from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import logging
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, Request, status
from jose import ExpiredSignatureError, JWTError, jwt
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_db
from app.schemas.auth import CurrentUser, TokenClaims
from app.services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

UNAUTHORIZED_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication credentials were not provided or are invalid.",
    headers={"WWW-Authenticate": "Bearer"},
)


class AuthenticationError(Exception):
    def __init__(
        self,
        reason: str,
        *,
        auth_subject: str | None = None,
        log_level: int = logging.WARNING,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.auth_subject = auth_subject
        self.log_level = log_level


@dataclass(frozen=True)
class JWKSCacheEntry:
    keys: dict[str, Any]
    fetched_at: datetime
    expires_at: datetime


def _log_auth(
    event_name: str,
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    auth_subject: str | None = None,
    user_id: str | None = None,
    reason: str | None = None,
    log_level: int = logging.INFO,
) -> None:
    payload: dict[str, str | None] = {
        "event": event_name,
        "service": "backend",
        "layer": "auth",
        "request_id": request_id,
        "trace_id": trace_id,
    }
    if auth_subject is not None:
        payload["auth_subject"] = auth_subject
    if user_id is not None:
        payload["user_id"] = user_id
    if reason is not None:
        payload["reason"] = reason
    logger.log(log_level, json.dumps(payload))


def _unauthorized(
    reason: str,
    *,
    auth_subject: str | None = None,
    log_level: int = logging.WARNING,
) -> AuthenticationError:
    return AuthenticationError(reason, auth_subject=auth_subject, log_level=log_level)


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")


def _get_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return f"{span_context.trace_id:032x}"


class Auth0JWTVerifier:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._jwks_cache: JWKSCacheEntry | None = None
        self._jwks_lock = asyncio.Lock()
        self._jwks_ttl = timedelta(seconds=self._settings.auth0_jwks_cache_ttl_seconds)

    @property
    def issuer(self) -> str:
        return f"https://{self._settings.auth0_domain}/"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}.well-known/jwks.json"

    async def _fetch_jwks(self) -> dict[str, Any]:
        timeout = httpx.Timeout(
            self._settings.auth0_jwks_timeout_seconds,
            connect=min(2.0, self._settings.auth0_jwks_timeout_seconds),
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise _unauthorized("jwks_fetch_failed", log_level=logging.ERROR) from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
            raise _unauthorized("jwks_payload_invalid", log_level=logging.ERROR)
        return payload

    def _get_cached_jwks(self, now: datetime, *, force_refresh: bool = False) -> dict[str, Any] | None:
        if self._jwks_cache is None:
            return None
        if force_refresh:
            return None
        if now >= self._jwks_cache.expires_at:
            return None
        return self._jwks_cache.keys

    async def _get_jwks(self, *, force_refresh: bool = False) -> dict[str, Any]:
        now = datetime.now(UTC)
        cached_jwks = self._get_cached_jwks(now, force_refresh=force_refresh)
        if cached_jwks is not None:
            return cached_jwks

        async with self._jwks_lock:
            now = datetime.now(UTC)
            cached_jwks = self._get_cached_jwks(now, force_refresh=force_refresh)
            if cached_jwks is not None:
                return cached_jwks

            try:
                jwks = await self._fetch_jwks()
            except AuthenticationError:
                if self._jwks_cache is not None:
                    self._jwks_cache = JWKSCacheEntry(
                        keys=self._jwks_cache.keys,
                        fetched_at=self._jwks_cache.fetched_at,
                        expires_at=now + self._jwks_ttl,
                    )
                    return self._jwks_cache.keys
                raise

            cache_entry = JWKSCacheEntry(
                keys=jwks,
                fetched_at=now,
                expires_at=now + self._jwks_ttl,
            )
            self._jwks_cache = cache_entry
            return cache_entry.keys

    async def _get_signing_key(self, kid: str) -> dict[str, Any]:
        jwks = await self._get_jwks()
        for key in jwks["keys"]:
            if key.get("kid") == kid:
                return key

        jwks = await self._get_jwks(force_refresh=True)
        for key in jwks["keys"]:
            if key.get("kid") == kid:
                return key

        raise _unauthorized("signing_key_not_found", log_level=logging.ERROR)

    async def verify_token(self, token: str) -> TokenClaims:
        auth_subject: str | None = None
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise _unauthorized("invalid_token_header") from exc

        algorithm = header.get("alg")
        kid = header.get("kid")
        if (
            not isinstance(algorithm, str)
            or algorithm not in self._settings.auth0_algorithms
        ):
            raise _unauthorized("invalid_token_algorithm")
        if not isinstance(kid, str) or not kid:
            raise _unauthorized("missing_token_kid")

        signing_key = await self._get_signing_key(kid)

        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=list(self._settings.auth0_algorithms),
                audience=self._settings.auth0_audience,
                issuer=self.issuer,
            )
        except ExpiredSignatureError as exc:
            raise _unauthorized("token_expired") from exc
        except JWTError as exc:
            raise _unauthorized("token_verification_failed", log_level=logging.ERROR) from exc

        auth_subject = payload.get("sub")
        if not isinstance(auth_subject, str) or not auth_subject.strip():
            raise _unauthorized("missing_token_subject")

        email = payload.get("email")
        normalized_email = email.strip() if isinstance(email, str) and email.strip() else None
        return TokenClaims(
            auth_subject=auth_subject.strip(),
            email=normalized_email,
        )


auth0_verifier = Auth0JWTVerifier()


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise _unauthorized("missing_authorization_header")

    normalized = authorization.strip()
    if not normalized:
        raise _unauthorized("empty_authorization_header")

    parts = normalized.split()
    if len(parts) != 2:
        raise _unauthorized("malformed_authorization_header")
    if parts[0] != "Bearer":
        raise _unauthorized("invalid_authorization_scheme")
    if not parts[1].strip():
        raise _unauthorized("empty_bearer_token")
    return parts[1].strip()


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> CurrentUser:
    auth_subject: str | None = None
    request_id = _get_request_id(request)
    trace_id = _get_trace_id()
    settings = get_settings()

    if settings.dev_auth_bypass and authorization is None:
        user = await get_or_create_user(
            session,
            auth_subject=settings.dev_auth_subject,
            email=settings.dev_auth_email,
        )
        _log_auth(
            "auth_success",
            request_id=request_id,
            trace_id=trace_id,
            auth_subject=user.auth_subject,
            user_id=str(user.id),
        )
        return CurrentUser(
            id=user.id,
            auth_subject=user.auth_subject,
            email=user.email,
        )

    try:
        token = _extract_bearer_token(authorization)
        claims = await auth0_verifier.verify_token(token)
        auth_subject = claims.auth_subject
        user = await get_or_create_user(
            session,
            auth_subject=claims.auth_subject,
            email=claims.email,
        )
    except AuthenticationError as exc:
        _log_auth(
            "auth_failed",
            request_id=request_id,
            trace_id=trace_id,
            auth_subject=exc.auth_subject or auth_subject,
            reason=exc.reason,
            log_level=exc.log_level,
        )
        raise UNAUTHORIZED_EXCEPTION from exc
    except Exception:
        _log_auth(
            "auth_failed",
            request_id=request_id,
            trace_id=trace_id,
            auth_subject=auth_subject,
            reason="user_sync_failed",
            log_level=logging.ERROR,
        )
        raise

    _log_auth(
        "auth_success",
        request_id=request_id,
        trace_id=trace_id,
        auth_subject=user.auth_subject,
        user_id=str(user.id),
        log_level=logging.INFO,
    )
    return CurrentUser(
        id=user.id,
        auth_subject=user.auth_subject,
        email=user.email,
    )
