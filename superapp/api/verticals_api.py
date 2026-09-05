"""Vertical management API."""

from __future__ import annotations

from fastapi import APIRouter

from superapp.verticals import list_verticals

router = APIRouter(prefix="/verticals", tags=["verticals"])


@router.get("/")
async def list_available_verticals():
    return {"verticals": [v.model_dump() for v in list_verticals()]}
