"""Module: main."""

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
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS vet_practices (
                id UUID PRIMARY KEY,
                source_key VARCHAR NOT NULL UNIQUE,
                source VARCHAR,
                name VARCHAR NOT NULL,
                abn VARCHAR,
                practice_type VARCHAR,
                phone VARCHAR,
                email VARCHAR,
                website VARCHAR,
                facebook_url VARCHAR,
                instagram_url VARCHAR,
                street_address VARCHAR,
                suburb VARCHAR,
                state VARCHAR,
                postcode VARCHAR,
                latitude NUMERIC(9,6),
                longitude NUMERIC(9,6),
                service_types TEXT[],
                opening_hours_text VARCHAR,
                opening_hours_json VARCHAR,
                after_hours_available BOOLEAN,
                after_hours_notes VARCHAR,
                emergency_referral VARCHAR,
                rating NUMERIC(3,2),
                review_count INTEGER,
                scraped_at TIMESTAMPTZ NOT NULL
            );
            """
        )
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vet_practices_suburb_postcode ON vet_practices (suburb, postcode);"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vet_practices_rating ON vet_practices (rating);"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vet_practices_service_types_gin ON vet_practices USING GIN (service_types);"))
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS practice_staff (
                id UUID PRIMARY KEY,
                practice_id UUID NOT NULL REFERENCES vet_practices(id) ON DELETE CASCADE,
                staff_name TEXT NOT NULL,
                role TEXT NOT NULL,
                role_raw TEXT,
                bio TEXT,
                profile_image_url TEXT,
                source_url TEXT NOT NULL,
                scraped_at TIMESTAMPTZ NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            );
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS practice_staff_sources (
                id UUID PRIMARY KEY,
                practice_id UUID NOT NULL REFERENCES vet_practices(id) ON DELETE CASCADE,
                source_url TEXT NOT NULL,
                http_status INTEGER,
                last_scraped_at TIMESTAMPTZ NOT NULL,
                parse_success BOOLEAN NOT NULL DEFAULT FALSE,
                notes TEXT
            );
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS owner_notes (
                note_id UUID PRIMARY KEY,
                owner_id UUID NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
                pet_id UUID REFERENCES pets(pet_id) ON DELETE SET NULL,
                author_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
                note_text TEXT NOT NULL,
                note_type VARCHAR NOT NULL DEFAULT 'GENERAL',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                deleted_at TIMESTAMP
            );
            """
        )
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_owner_notes_owner_created ON owner_notes (owner_id, created_at DESC);"))
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS concern_flags (
                flag_id UUID PRIMARY KEY,
                owner_id UUID NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
                pet_id UUID REFERENCES pets(pet_id) ON DELETE SET NULL,
                raised_by_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
                severity VARCHAR NOT NULL DEFAULT 'MEDIUM',
                status VARCHAR NOT NULL DEFAULT 'OPEN',
                category VARCHAR NOT NULL DEFAULT 'WELFARE',
                description TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                resolved_at TIMESTAMP,
                resolved_by_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
                resolution_notes TEXT
            );
            """
        )
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_concern_flags_owner_status ON concern_flags (owner_id, status, created_at DESC);"))
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS dashboard_reminders (
                reminder_id UUID PRIMARY KEY,
                role_scope VARCHAR NOT NULL,
                user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
                organisation_id UUID REFERENCES organisations(organisation_id) ON DELETE SET NULL,
                owner_id UUID REFERENCES owners(owner_id) ON DELETE SET NULL,
                pet_id UUID REFERENCES pets(pet_id) ON DELETE SET NULL,
                title VARCHAR NOT NULL,
                details TEXT,
                reminder_type VARCHAR NOT NULL DEFAULT 'REMINDER',
                due_at TIMESTAMP NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'OPEN',
                created_by_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                deleted_at TIMESTAMP
            );
            """
        )
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_dashboard_reminders_scope_due ON dashboard_reminders (role_scope, due_at);"))
    conn.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_practice_staff_identity
            ON practice_staff (practice_id, staff_name, role, source_url);
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_practice_staff_sources_lookup
            ON practice_staff_sources (practice_id, source_url);
            """
        )
    )
    conn.execute(
        text(
            """
            DO $$
            BEGIN
              BEGIN
                CREATE EXTENSION IF NOT EXISTS postgis;
              EXCEPTION
                WHEN OTHERS THEN
                  NULL;
              END;
            END $$;
            """
        )
    )

