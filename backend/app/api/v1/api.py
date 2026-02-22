# backend/app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.integrations import router as integrations_router

from app.api.v1.routes.pets import router as pets_router
from app.api.v1.routes.owners import router as owners_router
from app.api.v1.routes.visits import router as visits_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.eligibility import router as eligibility_router
from app.api.v1.routes.dashboard import router as dashboard_router



api_router = APIRouter()

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])

api_router.include_router(pets_router, prefix="/pets", tags=["pets"])
api_router.include_router(owners_router, prefix="/owners", tags=["owners"])
api_router.include_router(visits_router, prefix="/visits", tags=["visits"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(eligibility_router, prefix="/eligibility", tags=["eligibility"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
