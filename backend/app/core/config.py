import json
from functools import lru_cache
from typing import Any

from pydantic import EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "School Finance Manager API"
    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    api_prefix: str = Field(default="/api", validation_alias="API_PREFIX")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:change-me@127.0.0.1:5432/school_finance_demo",
        validation_alias="DATABASE_URL",
    )
    secret_key: str = Field(default="change-me-in-production", validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60 * 8, ge=5, le=24 * 60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    access_token_cookie_name: str = Field(default="gestao_escolar_access_token", validation_alias="ACCESS_TOKEN_COOKIE_NAME")
    access_token_cookie_domain: str | None = Field(default=None, validation_alias="ACCESS_TOKEN_COOKIE_DOMAIN")
    access_token_cookie_samesite: str = Field(default="lax", validation_alias="ACCESS_TOKEN_COOKIE_SAMESITE")
    access_token_cookie_secure: bool | None = Field(default=None, validation_alias="ACCESS_TOKEN_COOKIE_SECURE")
    enable_api_docs: bool | None = Field(default=None, validation_alias="ENABLE_API_DOCS")
    login_rate_limit_max_attempts: int = Field(default=5, ge=3, le=20, validation_alias="LOGIN_RATE_LIMIT_MAX_ATTEMPTS")
    login_rate_limit_window_minutes: int = Field(default=15, ge=1, le=60, validation_alias="LOGIN_RATE_LIMIT_WINDOW_MINUTES")
    login_rate_limit_lockout_minutes: int = Field(default=15, ge=1, le=120, validation_alias="LOGIN_RATE_LIMIT_LOCKOUT_MINUTES")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"],
        validation_alias="CORS_ORIGINS",
    )
    first_superuser_email: EmailStr = Field(default="admin@example.com", validation_alias="FIRST_SUPERUSER_EMAIL")
    first_superuser_password: str = Field(default="ChangeMe@123456", validation_alias="FIRST_SUPERUSER_PASSWORD")
    first_superuser_name: str = Field(default="Demo Administrator", validation_alias="FIRST_SUPERUSER_NAME")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped_value = value.strip()
            if not stripped_value:
                return []
            if stripped_value.startswith("["):
                return json.loads(stripped_value)
            return [origin.strip() for origin in stripped_value.split(",") if origin.strip()]
        return value

    @field_validator("access_token_cookie_samesite", mode="before")
    @classmethod
    def normalize_cookie_samesite(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("ACCESS_TOKEN_COOKIE_SAMESITE must be a string.")

        normalized = value.strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("ACCESS_TOKEN_COOKIE_SAMESITE must be one of: lax, strict, none.")
        return normalized

    @field_validator("access_token_cookie_domain", mode="before")
    @classmethod
    def normalize_cookie_domain(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @property
    def is_production_like(self) -> bool:
        return self.environment.lower() in {"prod", "production", "staging"}

    @property
    def api_docs_enabled(self) -> bool:
        if self.enable_api_docs is not None:
            return self.enable_api_docs
        return not self.is_production_like

    @property
    def local_cors_origin_regex(self) -> str | None:
        if self.is_production_like:
            return None
        return r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @property
    def resolved_access_token_cookie_secure(self) -> bool:
        if self.access_token_cookie_secure is not None:
            return self.access_token_cookie_secure
        return self.is_production_like

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.is_production_like:
            return self

        if self.secret_key == "change-me-in-production" or len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be changed and have at least 32 characters outside local environment.")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS cannot contain '*' outside local environment.")
        if not self.resolved_access_token_cookie_secure:
            raise ValueError("ACCESS_TOKEN_COOKIE_SECURE must remain enabled outside local environment.")
        if self.access_token_cookie_samesite == "none" and not self.resolved_access_token_cookie_secure:
            raise ValueError("SameSite=None cookies must use Secure outside local environment.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
