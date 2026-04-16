from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey, IdempotencyStatus
from app.repositories.idempotency_repository import (
    create_key,
    get_with_lock,
    update_to_completed,
    update_to_failed,
    update_locked_at,
    update_to_pending,
)

logger = logging.getLogger(__name__)


class IdempotencyBadRequestError(ValueError):
    pass


class IdempotencyConflictError(Exception):
    pass


@dataclass(frozen=True)
class IdempotencyExecutionResult:
    response_status: int
    response_json: dict[str, Any]
    resource_id: UUID | None
    replayed: bool
    status: IdempotencyStatus


@dataclass(frozen=True)
class LockedIdempotencyRecord:
    record: IdempotencyKey
    created: bool


@dataclass(frozen=True)
class IdempotentOperationResult:
    response_status: int
    response_json: dict[str, Any]
    resource_id: UUID | None = None


def compute_request_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(serialized).hexdigest()


def _log_idempotency_event(
    event: str,
    *,
    user_id: UUID,
    idempotency_key: str,
    status: str,
    decision: str,
    created: bool,
) -> None:
    logger.info(
        json.dumps(
            {
                "event": event,
                "user_id": str(user_id),
                "idempotency_key": idempotency_key,
                "status": status,
                "decision": decision,
                "created": created,
                "service": "backend",
                "layer": "service",
            }
        )
    )


def _build_failed_error_json(exc: Exception) -> dict[str, Any]:
    return {
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }


async def _get_or_create_locked_record(
    session: AsyncSession,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
) -> LockedIdempotencyRecord:
    now = datetime.now(UTC)
    record = await get_with_lock(
        session,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if record is not None:
        return LockedIdempotencyRecord(record=record, created=False)

    created_record = await create_key(
        session,
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        locked_at=now,
    )
    if created_record is not None:
        return LockedIdempotencyRecord(record=created_record, created=True)

    refetched_record = await get_with_lock(
        session,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if refetched_record is None:
        raise IdempotencyConflictError("Unable to acquire idempotency record.")
    if refetched_record.status == IdempotencyStatus.PENDING:
        await update_locked_at(
            session,
            idempotency_key_id=refetched_record.id,
            locked_at=now,
        )
        refetched_record.locked_at = now
    return LockedIdempotencyRecord(record=refetched_record, created=False)


async def execute_with_idempotency(
    session: AsyncSession,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_payload: dict[str, Any],
    operation: Callable[[], Awaitable[IdempotentOperationResult]],
) -> IdempotencyExecutionResult:
    request_hash = compute_request_hash(request_payload)
    locked_record = await _get_or_create_locked_record(
        session,
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    record = locked_record.record

    if record.request_hash != request_hash:
        _log_idempotency_event(
            "IDEMPOTENCY_HASH_MISMATCH",
            user_id=user_id,
            idempotency_key=idempotency_key,
            status=record.status.value,
            decision="reject",
            created=locked_record.created,
        )
        raise IdempotencyBadRequestError(
            "Idempotency-Key has already been used with a different request payload."
        )

    if record.status == IdempotencyStatus.COMPLETED:
        _log_idempotency_event(
            "IDEMPOTENCY_HIT_COMPLETED",
            user_id=user_id,
            idempotency_key=idempotency_key,
            status=record.status.value,
            decision="replay",
            created=locked_record.created,
        )
        return IdempotencyExecutionResult(
            response_status=record.response_status,
            response_json=record.response_json or {},
            resource_id=record.resource_id,
            replayed=True,
            status=record.status,
        )

    now = datetime.now(UTC)

    if record.status in {IdempotencyStatus.PENDING, IdempotencyStatus.FAILED}:
        _log_idempotency_event(
            "IDEMPOTENCY_RETRY_FAILED"
            if record.status == IdempotencyStatus.FAILED
            else "IDEMPOTENCY_IN_PROGRESS",
            user_id=user_id,
            idempotency_key=idempotency_key,
            status=record.status.value,
            decision="execute",
            created=locked_record.created,
        )
        await update_to_pending(
            session,
            idempotency_key_id=record.id,
            locked_at=now,
        )
        record.status = IdempotencyStatus.PENDING
        record.locked_at = now

    if record.status != IdempotencyStatus.PENDING:
        raise IdempotencyConflictError(
            "Idempotency-Key is not in an executable state."
        )

    await session.flush()

    try:
        operation_result = await operation()
    except Exception as exc:
        await update_to_failed(
            session,
            idempotency_key_id=record.id,
            error_json=_build_failed_error_json(exc),
        )
        raise

    await update_to_completed(
        session,
        idempotency_key_id=record.id,
        response_status=operation_result.response_status,
        response_json=operation_result.response_json,
        resource_id=operation_result.resource_id,
    )
    return IdempotencyExecutionResult(
        response_status=operation_result.response_status,
        response_json=operation_result.response_json,
        resource_id=operation_result.resource_id,
        replayed=False,
        status=IdempotencyStatus.COMPLETED,
    )
