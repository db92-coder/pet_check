from fastapi import FastAPI
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.integrations import router as integrations_router
from fastapi import FastAPI
from app.api.v1.api import api_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Pet Check API", version="0.1.0")
app = FastAPI()

app.include_router(health_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")



from app.db.base import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)
