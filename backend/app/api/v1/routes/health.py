"""Module: health."""

from fastapi import APIRouter

router = APIRouter()

# Endpoint: lightweight health probe for service liveness.
@router.get("/health")
def health():
    return {"status": "ok"}

