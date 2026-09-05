"""Schema calibration API."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("/")
async def list_schemas():
    return {"schemas": []}


@router.post("/{schema_id}/approve")
async def approve_schema(schema_id: str):
    return {"schema_id": schema_id, "status": "approved"}
