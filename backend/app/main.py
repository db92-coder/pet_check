from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.api import api_router
from app.db.base import Base
from app.db.session import engine

app = FastAPI(title="Pet Protect API", version="0.1.0")

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

Base.metadata.create_all(bind=engine)

with engine.begin() as conn:
    conn.execute(
        text(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS password VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE users
            SET password = 'password123'
            WHERE password IS NULL;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE users
            ALTER COLUMN password SET NOT NULL;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE users
            ALTER COLUMN password DROP DEFAULT;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS role VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE users
            SET role = 'OWNER'
            WHERE role IS NULL;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE users
            ALTER COLUMN role SET NOT NULL;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE users
            ALTER COLUMN role SET DEFAULT 'OWNER';
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE pets
            ADD COLUMN IF NOT EXISTS photo_url VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE pets
            ADD COLUMN IF NOT EXISTS microchip_number VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE pets
            ADD COLUMN IF NOT EXISTS photo_data BYTEA;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE pets
            ADD COLUMN IF NOT EXISTS photo_mime_type VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS medications (
                medication_id UUID PRIMARY KEY,
                pet_id UUID NOT NULL REFERENCES pets(pet_id) ON DELETE CASCADE,
                name VARCHAR NOT NULL,
                dosage VARCHAR,
                instructions VARCHAR,
                start_date DATE,
                end_date DATE
            );
            """
        )
    )
