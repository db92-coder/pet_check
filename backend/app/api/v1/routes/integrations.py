from fastapi import APIRouter
import httpx
import os

router = APIRouter()

MOCK_GOV_BASE_URL = os.getenv("MOCK_GOV_BASE_URL", "http://mock-gov:8001")
MOCK_VET_BASE_URL = os.getenv("MOCK_VET_BASE_URL", "http://mock-vet:8002")

@router.get("/gov/ping")
async def gov_ping():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{MOCK_GOV_BASE_URL}/ping")
        r.raise_for_status()
        return {"upstream": "mock-gov", "response": r.json()}

@router.get("/vet/ping")
async def vet_ping():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{MOCK_VET_BASE_URL}/ping")
        r.raise_for_status()
        return {"upstream": "mock-vet", "response": r.json()}

@router.post("/gov/check")
async def gov_check(payload: dict):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{MOCK_GOV_BASE_URL}/eligibility/check", json=payload)
        r.raise_for_status()
        return r.json()