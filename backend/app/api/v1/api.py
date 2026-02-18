from fastapi import APIRouter

from app.api.v1.routes import pets, owners, visits, analytics

api_router = APIRouter()

api_router.include_router(pets.router, prefix="/pets", tags=["pets"])
api_router.include_router(owners.router, prefix="/owners", tags=["owners"])
api_router.include_router(visits.router, prefix="/visits", tags=["visits"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
