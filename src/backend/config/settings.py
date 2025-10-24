from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field

try:
    import win32cred  # type: ignore
except ImportError:  # pragma: no cover - only triggered on non-Windows or missing package
    win32cred = None  # type: ignore[assignment]


class SecretNotFoundError(RuntimeError):
    """Raised when a required secret cannot be located in env vars or Credential Manager."""


def get_secret(key: str, credential_prefix: str = "USDT_") -> str:
    """
    Fetch a secret value.

    Order of precedence:
    1. Environment variable `<key>`
    2. Windows Credential Manager generic credential named `<credential_prefix><key>`

    Parameters
    ----------
    key:
        Environment variable name without prefix (e.g. ``DATABASE_URL``).
    credential_prefix:
        Prefix applied to credential names; defaults to ``USDT_``.

    Returns
    -------
    str
        Secret value.

    Raises
    ------
    SecretNotFoundError
        If the secret cannot be found anywhere.
    RuntimeError
        If Credential Manager support is not available and the environment variable
        is also missing.
    """

    value = os.getenv(key)
    if value:
        return value

    credential_name = f"{credential_prefix}{key}"
    if win32cred is None:
        raise SecretNotFoundError(
            f"{key} not found in environment and win32cred is unavailable. "
            "Store the secret as an environment variable or install pywin32."
        )

    try:
        cred = win32cred.CredRead(credential_name, win32cred.CRED_TYPE_GENERIC)  # type: ignore[attr-defined]
        blob: bytes = cred["CredentialBlob"]  # type: ignore[index]
        # CredentialBlob is UTF-16LE encoded for generic credentials
        return blob.decode("utf-16-le").rstrip("\x00")
    except Exception as exc:
        raise SecretNotFoundError(
            f"{key} not found in environment or Credential Manager entry {credential_name}"
        ) from exc


class Settings(BaseModel):
    """Application settings container."""

    api_version: str = Field(default="v1")
    log_level: str = Field(default="INFO")
    database_url: str = Field(...)
    rabbitmq_url: str = Field(...)
    telegram_bot_token: str = Field(...)
    healthcheck_timeout_seconds: int = Field(default=5)

    @classmethod
    def load(cls) -> "Settings":
        """
        Load settings using the secret resolution strategy.
        """

        return cls(
            database_url=get_secret("DATABASE_URL"),
            rabbitmq_url=get_secret("RABBITMQ_URL"),
            telegram_bot_token=get_secret("TELEGRAM_BOT_TOKEN"),
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Lazily load and cache settings for dependency injection.
    """

    return Settings.load()


__all__ = ["Settings", "get_settings", "get_secret", "SecretNotFoundError"]


