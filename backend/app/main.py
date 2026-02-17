from fastapi import FastAPI
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.integrations import router as integrations_router

app = FastAPI(title="Pet Check API", version="0.1.0")

app.include_router(health_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")


from app.db.base import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)
