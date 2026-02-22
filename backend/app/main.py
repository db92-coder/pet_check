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
        "http://localhost:5174",
        "http://127.0.0.1:5174",
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
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS address VARCHAR;
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
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS phone VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS email VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS address VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS suburb VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS state VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS postcode VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS latitude VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            ALTER TABLE organisations ADD COLUMN IF NOT EXISTS longitude VARCHAR;
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS vet_cost_guidelines (
                guideline_id UUID PRIMARY KEY,
                species VARCHAR NOT NULL,
                size_class VARCHAR NOT NULL,
                annual_food_wet NUMERIC(10,2) NOT NULL,
                annual_food_dry NUMERIC(10,2) NOT NULL,
                annual_checkups NUMERIC(10,2) NOT NULL,
                annual_unscheduled NUMERIC(10,2) NOT NULL,
                annual_insurance NUMERIC(10,2) NOT NULL,
                avg_lifespan_years INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS owner_gov_profiles (
                profile_id UUID PRIMARY KEY,
                owner_id UUID NOT NULL UNIQUE REFERENCES owners(owner_id) ON DELETE CASCADE,
                tax_file_number VARCHAR NOT NULL,
                ato_reference_number VARCHAR NOT NULL,
                taxable_income NUMERIC(12,2) NOT NULL,
                assessed_tax_payable NUMERIC(12,2) NOT NULL,
                receiving_centrelink_unemployment BOOLEAN NOT NULL DEFAULT FALSE,
                receiving_aged_pension BOOLEAN NOT NULL DEFAULT FALSE,
                receiving_dva_pension BOOLEAN NOT NULL DEFAULT FALSE,
                government_housing BOOLEAN NOT NULL DEFAULT FALSE,
                housing_status VARCHAR NOT NULL DEFAULT 'rent',
                property_size_sqm INTEGER NOT NULL DEFAULT 80,
                household_income NUMERIC(12,2) NOT NULL,
                credit_score INTEGER NOT NULL,
                basic_living_expenses NUMERIC(12,2) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS staff_leaves (
                leave_id UUID PRIMARY KEY,
                organisation_id UUID NOT NULL REFERENCES organisations(organisation_id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                reason VARCHAR,
                status VARCHAR NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )
    )
