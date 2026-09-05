"""API-key authentication dependency with an explicit development bypass."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from superapp.config import settings


def get_current_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if settings.auth_provider == "none":
        return "development"
    expected = settings.api_key
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return x_api_key


def get_api_key_auth_dependency():
    return get_current_api_key
