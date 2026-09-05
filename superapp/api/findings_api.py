"""Finding review API."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/findings", tags=["findings"])


@router.post("/{finding_id}/accept")
async def accept_finding(finding_id: str):
    return {"finding_id": finding_id, "status": "accepted"}


@router.post("/{finding_id}/dismiss")
async def dismiss_finding(finding_id: str):
    return {"finding_id": finding_id, "status": "dismissed"}
