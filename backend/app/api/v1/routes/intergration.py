"""Module: intergration."""

from fastapi import APIRouter
import httpx
from app.core.config import settings

router = APIRouter()

# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/integrations/gov/ping")
async def gov_ping():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{settings.mock_gov_base_url}/ping")
        r.raise_for_status()
        return {"upstream": "mock-gov", "response": r.json()}

# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/integrations/vet/ping")
async def vet_ping():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{settings.mock_vet_base_url}/ping")
        r.raise_for_status()
        return {"upstream": "mock-vet", "response": r.json()}

# Endpoint: handles HTTP request/response mapping for this route.
@router.post("/integrations/gov/check")
async def gov_check(payload: dict):
    """
    Simulated “government eligibility check”.
    payload example: {"owner_id":"...", "pet_id":"...", "context": {...}}
    """
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{settings.mock_gov_base_url}/eligibility/check", json=payload)
        r.raise_for_status()
        return r.json()

