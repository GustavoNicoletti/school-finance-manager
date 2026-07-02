from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


settings = get_settings()


@dataclass
class LoginAttemptBucket:
    failed_attempts: deque[datetime] = field(default_factory=deque)
    blocked_until: datetime | None = None


_attempts: dict[str, LoginAttemptBucket] = {}
_attempts_lock = Lock()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _window_delta() -> timedelta:
    return timedelta(minutes=settings.login_rate_limit_window_minutes)


def _lockout_delta() -> timedelta:
    return timedelta(minutes=settings.login_rate_limit_lockout_minutes)


def _prune_bucket(bucket: LoginAttemptBucket, now: datetime) -> None:
    window_start = now - _window_delta()
    while bucket.failed_attempts and bucket.failed_attempts[0] < window_start:
        bucket.failed_attempts.popleft()

    if bucket.blocked_until and bucket.blocked_until <= now:
        bucket.blocked_until = None


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for.strip():
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def build_login_rate_limit_key(request: Request, email: str) -> str:
    return f"{get_client_ip(request)}::{email.strip().lower()}"


def ensure_login_allowed(key: str) -> None:
    now = _utc_now()
    with _attempts_lock:
        bucket = _attempts.get(key)
        if not bucket:
            return

        _prune_bucket(bucket, now)
        if bucket.blocked_until and bucket.blocked_until > now:
            retry_after = max(1, int((bucket.blocked_until - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas de login. Aguarde alguns minutos antes de tentar novamente.",
                headers={"Retry-After": str(retry_after)},
            )

        if not bucket.failed_attempts and bucket.blocked_until is None:
            _attempts.pop(key, None)


def register_failed_login(key: str) -> None:
    now = _utc_now()
    with _attempts_lock:
        bucket = _attempts.setdefault(key, LoginAttemptBucket())
        _prune_bucket(bucket, now)
        bucket.failed_attempts.append(now)
        if len(bucket.failed_attempts) >= settings.login_rate_limit_max_attempts:
            bucket.blocked_until = now + _lockout_delta()


def register_successful_login(key: str) -> None:
    with _attempts_lock:
        _attempts.pop(key, None)


def reset_login_rate_limit_state() -> None:
    with _attempts_lock:
        _attempts.clear()
