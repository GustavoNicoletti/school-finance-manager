import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_local_settings_parse_comma_separated_cors_origins():
    settings = Settings(CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173")

    assert settings.cors_origins == ["http://127.0.0.1:5173", "http://localhost:5173"]


def test_production_settings_reject_default_secret_key():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="change-me-in-production",
            CORS_ORIGINS=["https://sistema.escola.example"],
        )


def test_production_settings_reject_short_secret_key():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="curta-demais",
            CORS_ORIGINS=["https://sistema.escola.example"],
        )


def test_production_settings_reject_wildcard_cors():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="x" * 48,
            CORS_ORIGINS=["*"],
        )


def test_production_settings_accept_strong_secret_and_explicit_cors():
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 48,
        CORS_ORIGINS=["https://sistema.escola.example"],
    )

    assert settings.environment == "production"
    assert settings.cors_origins == ["https://sistema.escola.example"]
    assert settings.api_docs_enabled is False
    assert settings.resolved_access_token_cookie_secure is True


def test_local_settings_keep_docs_enabled_by_default():
    settings = Settings()

    assert settings.api_docs_enabled is True
