from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, Response
from jose import jwt
from starlette.requests import Request

from app.core.config import get_settings
from app.core.security import (
    clear_access_token_cookie,
    create_access_token,
    decode_access_token,
    get_password_hash,
    get_request_access_token,
    set_access_token_cookie,
    verify_password,
)
from app.services.login_rate_limit_service import (
    build_login_rate_limit_key,
    ensure_login_allowed,
    get_client_ip,
    register_failed_login,
    register_successful_login,
)


def make_request(*, forwarded_for: str | None = None, cookie_token: str | None = None, client_host: str = "127.0.0.1") -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for:
        headers.append((b"x-forwarded-for", forwarded_for.encode("utf-8")))
    if cookie_token:
        settings = get_settings()
        headers.append((b"cookie", f"{settings.access_token_cookie_name}={cookie_token}".encode("utf-8")))

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": (client_host, 50000),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


def test_password_hash_roundtrip_and_plaintext_not_stored() -> None:
    password = "ChangeMe@123456"

    hashed_password = get_password_hash(password)

    assert hashed_password != password
    assert hashed_password.startswith("$2")
    assert verify_password(password, hashed_password) is True
    assert verify_password("SenhaErrada@1", hashed_password) is False


def test_verify_password_returns_false_for_invalid_hash() -> None:
    assert verify_password("ChangeMe@123456", "hash-invalido") is False


def test_decode_access_token_accepts_valid_access_token() -> None:
    token = create_access_token("42", expires_delta=timedelta(minutes=5))

    assert decode_access_token(token) == "42"


def test_decode_access_token_rejects_refresh_like_token() -> None:
    settings = get_settings()
    refresh_like_token = jwt.encode(
        {
            "sub": "42",
            "type": "refresh",
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(refresh_like_token)

    assert exc_info.value.status_code == 401


def test_get_request_access_token_prefers_bearer_over_cookie() -> None:
    request = make_request(cookie_token="cookie-token")

    assert get_request_access_token(request, "bearer-token") == "bearer-token"
    assert get_request_access_token(request, None) == "cookie-token"


def test_access_token_cookie_helpers_apply_security_flags() -> None:
    settings = get_settings()
    response = Response()

    set_access_token_cookie(response, "token-seguro")

    cookie_header = response.headers["set-cookie"]
    assert f"{settings.access_token_cookie_name}=token-seguro" in cookie_header
    assert "HttpOnly" in cookie_header
    assert f"SameSite={settings.access_token_cookie_samesite}" in cookie_header

    clear_access_token_cookie(response)

    cleared_cookie_header = response.headers.getlist("set-cookie")[-1]
    assert f"{settings.access_token_cookie_name}=" in cleared_cookie_header
    assert "Max-Age=0" in cleared_cookie_header


def test_login_rate_limit_uses_forwarded_ip_and_normalizes_email() -> None:
    request = make_request(forwarded_for="203.0.113.10, 198.51.100.5")

    assert get_client_ip(request) == "203.0.113.10"
    assert build_login_rate_limit_key(request, "  User@Example.Com  ") == "203.0.113.10::user@example.com"


def test_login_rate_limit_blocks_after_threshold_and_can_reset() -> None:
    settings = get_settings()
    key = "198.51.100.10::admin@example.com"

    for _ in range(settings.login_rate_limit_max_attempts):
        register_failed_login(key)

    with pytest.raises(HTTPException) as exc_info:
        ensure_login_allowed(key)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"].isdigit()

    register_successful_login(key)
    ensure_login_allowed(key)

