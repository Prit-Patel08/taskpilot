from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import re
from typing import Any

from app.errors.domain_errors import DomainError
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

try:
    from asyncpg import exceptions as asyncpg_exceptions
except ImportError:  # pragma: no cover
    asyncpg_exceptions = None


RETRYABLE_POSTGRES_SQLSTATES = {
    "40001",  # serialization_failure
    "40P01",  # deadlock_detected
    "53300",  # too_many_connections
    "57P03",  # cannot_connect_now
}

RETRYABLE_MESSAGE_PATTERNS = (
    "connection refused",
    "connection reset",
    "connection aborted",
    "connection timed out",
    "temporary failure",
    "temporarily unavailable",
    "network",
    "service unavailable",
    "too many connections",
    "cannot connect now",
    "deadlock detected",
    "serialization failure",
)

NON_RETRYABLE_MESSAGE_PATTERNS = (
    "validation",
    "not found",
    "missing",
    "invalid state",
    "unexpected status",
)
MAX_ERROR_MESSAGE_SHORT_LENGTH = 100


@dataclass(frozen=True)
class RetryClassification:
    retryable: bool
    classification: str
    reason: str
    error_code: str
    error_type: str
    error_message_short: str
    error_fingerprint: str


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def sanitize_retry_count(value: Any, *, max_retries: int) -> tuple[int, bool]:
    if value is None:
        return 0, False

    parsed = _coerce_int(value)
    if parsed is None or parsed < 0:
        return max_retries, True
    if parsed > max_retries:
        return max_retries, True
    return parsed, False


def _retryable_sqlstate(exc: DBAPIError) -> str | None:
    original = getattr(exc, "orig", None)
    for attribute in ("sqlstate", "pgcode"):
        value = getattr(original, attribute, None)
        if isinstance(value, str) and value:
            return value
    return None


def _build_error_message_short(exc: Exception) -> str:
    normalized = re.sub(r"\s+", " ", str(exc)).strip()
    if not normalized:
        normalized = exc.__class__.__name__
    if len(normalized) <= MAX_ERROR_MESSAGE_SHORT_LENGTH:
        return normalized
    return normalized[: MAX_ERROR_MESSAGE_SHORT_LENGTH - 3] + "..."


def _build_error_fingerprint(error_code: str, error_message_short: str) -> str:
    fingerprint_source = f"{error_code}:{error_message_short}".encode("utf-8")
    return hashlib.sha256(fingerprint_source).hexdigest()[:16]


def _camel_to_upper_snake(value: str) -> str:
    with_boundaries = re.sub(r"(?<!^)(?=[A-Z])", "_", value)
    return with_boundaries.upper()


def _build_retry_classification(
    *,
    retryable: bool,
    classification: str,
    reason: str,
    error_code: str,
    error_type: str,
    exc: Exception,
) -> RetryClassification:
    error_message_short = _build_error_message_short(exc)
    return RetryClassification(
        retryable=retryable,
        classification=classification,
        reason=reason,
        error_code=error_code,
        error_type=error_type,
        error_message_short=error_message_short,
        error_fingerprint=_build_error_fingerprint(
            error_code=error_code,
            error_message_short=error_message_short,
        ),
    )


def classify_exception(exc: Exception) -> RetryClassification:
    if isinstance(exc, DomainError):
        return _build_retry_classification(
            retryable=exc.retryable,
            classification="domain",
            reason=exc.error_code,
            error_code=exc.error_code,
            error_type="domain",
            exc=exc,
        )

    if isinstance(exc, (ValidationError, ValueError, LookupError, IntegrityError)):
        return _build_retry_classification(
            retryable=False,
            classification="system",
            reason=exc.__class__.__name__,
            error_code=_camel_to_upper_snake(exc.__class__.__name__),
            error_type="system",
            exc=exc,
        )

    if isinstance(
        exc,
        (
            asyncio.TimeoutError,
            TimeoutError,
            ConnectionError,
            OperationalError,
            InterfaceError,
            SQLAlchemyTimeoutError,
        ),
    ):
        return _build_retry_classification(
            retryable=True,
            classification="system",
            reason=exc.__class__.__name__,
            error_code=_camel_to_upper_snake(exc.__class__.__name__),
            error_type="system",
            exc=exc,
        )

    if isinstance(exc, DBAPIError):
        if exc.connection_invalidated:
            return _build_retry_classification(
                retryable=True,
                classification="system",
                reason=exc.__class__.__name__,
                error_code="DB_CONNECTION_INVALIDATED",
                error_type="system",
                exc=exc,
            )

        sqlstate = _retryable_sqlstate(exc)
        if sqlstate is not None and (
            sqlstate.startswith("08") or sqlstate in RETRYABLE_POSTGRES_SQLSTATES
        ):
            return _build_retry_classification(
                retryable=True,
                classification="system",
                reason=exc.__class__.__name__,
                error_code=f"SQLSTATE_{sqlstate}",
                error_type="system",
                exc=exc,
            )

    if asyncpg_exceptions is not None:
        retryable_asyncpg_types = (
            getattr(asyncpg_exceptions, "PostgresConnectionError", tuple()),
            getattr(asyncpg_exceptions, "CannotConnectNowError", tuple()),
            getattr(asyncpg_exceptions, "ConnectionDoesNotExistError", tuple()),
            getattr(asyncpg_exceptions, "ConnectionFailureError", tuple()),
            getattr(asyncpg_exceptions, "TooManyConnectionsError", tuple()),
        )
        retryable_asyncpg_types = tuple(
            exc_type for exc_type in retryable_asyncpg_types if isinstance(exc_type, type)
        )
        if retryable_asyncpg_types and isinstance(exc, retryable_asyncpg_types):
            return _build_retry_classification(
                retryable=True,
                classification="system",
                reason=exc.__class__.__name__,
                error_code=_camel_to_upper_snake(exc.__class__.__name__),
                error_type="system",
                exc=exc,
            )

    message = str(exc).lower()
    if any(pattern in message for pattern in NON_RETRYABLE_MESSAGE_PATTERNS):
        return _build_retry_classification(
            retryable=False,
            classification="system",
            reason=exc.__class__.__name__,
            error_code=_camel_to_upper_snake(exc.__class__.__name__),
            error_type="system",
            exc=exc,
        )
    if any(pattern in message for pattern in RETRYABLE_MESSAGE_PATTERNS):
        return _build_retry_classification(
            retryable=True,
            classification="system",
            reason=exc.__class__.__name__,
            error_code=_camel_to_upper_snake(exc.__class__.__name__),
            error_type="system",
            exc=exc,
        )

    return _build_retry_classification(
        retryable=False,
        classification="system",
        reason=exc.__class__.__name__,
        error_code=_camel_to_upper_snake(exc.__class__.__name__),
        error_type="system",
        exc=exc,
    )


def is_retryable_exception(exc: Exception) -> bool:
    return classify_exception(exc).retryable
