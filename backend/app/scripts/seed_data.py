"""Module: seed_data."""

from faker import Faker
import random
import string
import csv
import uuid
from pathlib import Path
from datetime import datetime, UTC, timedelta
from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.core.security import hash_password

from app.db.models.user import User
from app.db.models.owner import Owner
from app.db.models.pet import Pet
from app.db.models.owner_pet import OwnerPet

from app.db.models.organisation import Organisation
from app.db.models.organisation_member import OrganisationMember
from app.db.models.vet_visit import VetVisit
from app.db.models.weight import Weight
from app.db.models.vaccination import Vaccination
from app.db.models.medication import Medication
from app.db.models.vet_cost_guideline import VetCostGuideline
from app.db.models.owner_gov_profile import OwnerGovProfile
from app.db.models.staff_leave import StaffLeave
from app.db.models.vet_practice import VetPractice
from app.db.models.practice_staff import PracticeStaff
from app.db.models.practice_staff_source import PracticeStaffSource

fake = Faker()
random.seed(42)
fake.seed_instance(42)

DOG_VAX = ["C5", "C3", "Rabies"]
CAT_VAX = ["F3", "FIV", "Rabies"]
FIXED_ACCOUNT_PASSWORD = "Had6$sq78"
FIXED_ACCOUNTS = [
    {
        "email": "admin@petprotect.local",
        "role": "ADMIN",
        "full_name": "Pet Protect Admin",
        "suburb": "Hobart",
        "postcode": "7000",
    },
    {
        "email": "vet@petprotect.local",
        "role": "VET",
        "full_name": "Pet Protect Vet",
        "suburb": "Launceston",
        "postcode": "7250",
    },
    {
        "email": "owner@petprotect.local",
        "role": "OWNER",
        "full_name": "Pet Protect Owner",
        "suburb": "Sandy Bay",
        "postcode": "7005",
    },
]
POPULAR_EMAIL_PROVIDERS = [
    "gmail.com",
    "outlook.com",
    "hotmail.com.au",
    "yahoo.com.au",
    "icloud.com",
]
TAS_LOCALITIES = [
    ("Sandy Bay", "7005"),
    ("Hobart", "7000"),
    ("Lenah Valley", "7008"),
    ("Moonah", "7009"),
    ("Claremont", "7011"),
    ("Lindisfarne", "7015"),
    ("Bellerive", "7018"),
    ("Rosny Park", "7018"),
    ("Kingston", "7050"),
    ("Taroona", "7053"),
    ("Sorell", "7172"),
    ("Dodges Ferry", "7173"),
    ("Launceston", "7250"),
    ("Kings Meadows", "7249"),
    ("South Launceston", "7249"),
    ("Scottsdale", "7260"),
    ("Lilydale", "7268"),
    ("Exeter", "7275"),
    ("Longford", "7301"),
    ("Deloraine", "7304"),
    ("Sheffield", "7306"),
    ("Devonport", "7310"),
    ("Ulverstone", "7315"),
    ("Penguin", "7316"),
    ("Burnie", "7320"),
    ("Smithton", "7330"),
    ("St Helens", "7216"),
]
TAS_STREET_NAMES = [
    "Main St",
    "High St",
    "Church St",
    "King St",
    "George St",
    "Victoria St",
    "Bay Rd",
    "River Rd",
    "Channel Hwy",
    "Alexander Rd",
    "Wellington St",
    "Elizabeth St",
    "Charles St",
    "Crescent St",
]

# Shared helpers used by multiple seed builders.
def generate_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def generate_au_mobile() -> str:
    # Australian mobile format: 04 + 8 digits
    return "04" + "".join(random.choice(string.digits) for _ in range(8))


def _slugify_practice_domain(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-")
    return cleaned or "vet-practice"


def _unique_staff_email(first_name: str, last_name: str, clinic_domain: str, used: set[str]) -> str:
    base = f"{first_name.lower()}.{last_name.lower()}@{clinic_domain}.com.au"
    email = base
    n = 2
    while email in used:
        email = f"{first_name.lower()}.{last_name.lower()}{n}@{clinic_domain}.com.au"
        n += 1
    used.add(email)
    return email


def _split_name_parts(full_name: str) -> tuple[str, str]:
    parts = [p for p in (full_name or "").strip().split() if p]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    if len(parts) == 1:
        return parts[0], "owner"
    return "pet", "owner"


def _normalize_email_token(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalpha()) or "user"


def _generate_realistic_email(full_name: str, used: set[str]) -> str:
    first, last = _split_name_parts(full_name)
    first_norm = _normalize_email_token(first)
    last_norm = _normalize_email_token(last)
    domain = random.choice(POPULAR_EMAIL_PROVIDERS)
    pattern = random.choice(["first_last", "initial_last", "firstlast", "first_last_num", "initial_last_num"])
    if pattern == "first_last":
        local = f"{first_norm}.{last_norm}"
    elif pattern == "initial_last":
        local = f"{first_norm[0]}.{last_norm}"
    elif pattern == "firstlast":
        local = f"{first_norm}{last_norm}"
    elif pattern == "first_last_num":
        local = f"{first_norm}.{last_norm}{random.randint(1, 99)}"
    else:
        local = f"{first_norm[0]}.{last_norm}{random.randint(1, 99)}"

    email = f"{local}@{domain}"
    suffix = 2
    while email in used:
        email = f"{local}{suffix}@{domain}"
        suffix += 1
    used.add(email)
    return email


def _build_tas_address(suburb: str, postcode: str) -> str:
    number = random.randint(1, 250)
    street = random.choice(TAS_STREET_NAMES)
    return f"{number} {street}, {suburb} TAS {postcode}"


def _pick_tas_locality() -> tuple[str, str]:
    return random.choice(TAS_LOCALITIES)


def _postcode_bucket(postcode: str | None) -> str:
    if not postcode:
        return "UNKNOWN"
    pc = "".join(ch for ch in str(postcode) if ch.isdigit())
    if not pc:
        return "UNKNOWN"
    value = int(pc)
    if 7000 <= value <= 7199:
        return "SOUTH"
    if 7200 <= value <= 7299:
        return "NORTH_EAST"
    if 7300 <= value <= 7399:
        return "NORTH_WEST"
    return "UNKNOWN"


def _extract_postcode_from_address(address: str | None) -> str | None:
    if not address:
        return None
    tokens = [tok for tok in str(address).replace(",", " ").split() if tok.isdigit() and len(tok) == 4]
    return tokens[-1] if tokens else None


def ensure_user_auth_columns(session) -> None:
    # Ensure expected auth columns exist even on older DB schemas.
    session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password VARCHAR;"))
    session.execute(text("UPDATE users SET password = 'password123' WHERE password IS NULL;"))
    session.execute(text("ALTER TABLE users ALTER COLUMN password SET NOT NULL;"))
    session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR;"))
    session.execute(text("UPDATE users SET role = 'OWNER' WHERE role IS NULL;"))
    session.execute(text("ALTER TABLE users ALTER COLUMN role SET NOT NULL;"))
    session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS address VARCHAR;"))
    session.execute(text("UPDATE users SET address = 'Unknown address' WHERE address IS NULL;"))
    session.commit()


def ensure_pet_health_columns(session) -> None:
    # Backfill health-related columns/tables introduced after initial schema.
    session.execute(text("ALTER TABLE pets ADD COLUMN IF NOT EXISTS microchip_number VARCHAR;"))
    session.execute(text("CREATE TABLE IF NOT EXISTS medications ("
                         "medication_id UUID PRIMARY KEY,"
                         "pet_id UUID NOT NULL REFERENCES pets(pet_id) ON DELETE CASCADE,"
                         "name VARCHAR NOT NULL,"
                         "dosage VARCHAR,"
                         "instructions VARCHAR,"
                         "start_date DATE,"
                         "end_date DATE"
                         ");"))
    session.commit()


def ensure_clinic_profile_columns(session) -> None:
    # Backfill clinic profile and staff/vet snapshot tables for local dev startup.
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS phone VARCHAR;"))
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS email VARCHAR;"))
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS address VARCHAR;"))
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS suburb VARCHAR;"))
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS state VARCHAR;"))
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS postcode VARCHAR;"))
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS latitude VARCHAR;"))
    session.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS longitude VARCHAR;"))
    session.execute(
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
    session.execute(
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
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_vet_practices_suburb_postcode ON vet_practices (suburb, postcode);"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_vet_practices_rating ON vet_practices (rating);"))
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_vet_practices_service_types_gin ON vet_practices USING GIN (service_types);"))
    session.execute(
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
    session.execute(
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
    session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_practice_staff_identity
            ON practice_staff (practice_id, staff_name, role, source_url);
            """
        )
    )
    session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_practice_staff_sources_lookup
            ON practice_staff_sources (practice_id, source_url);
            """
        )
    )
    session.commit()


def ensure_risk_tables(session) -> None:
    # Government + vet cost scoring inputs for eligibility calculations.
    session.execute(
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
    session.execute(
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
    session.commit()


def ensure_care_coordination_tables(session) -> None:
    # Add owner clinical notes, concern flags, and dashboard calendar reminders.
    session.execute(
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
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_owner_notes_owner_created ON owner_notes (owner_id, created_at DESC);"))
    session.execute(
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
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_concern_flags_owner_status ON concern_flags (owner_id, status, created_at DESC);"))
    session.execute(
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
    session.execute(text("CREATE INDEX IF NOT EXISTS idx_dashboard_reminders_scope_due ON dashboard_reminders (role_scope, due_at);"))
    session.commit()


def export_credentials(users: list[User]) -> Path:
    out_path = Path(__file__).resolve().parent / "seeded_user_credentials.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "email", "password", "role"])
        for user in users:
            if user.email.endswith("@petprotect.local"):
                # Do not expose fixed account password/hash in exported CSV.
                writer.writerow([str(user.user_id), user.email, "<hidden>", user.role])
            else:
                writer.writerow([str(user.user_id), user.email, user.password, user.role])
    return out_path


def reset_db(session) -> None:
    # Keep reset order explicit so FK dependencies truncate cleanly.
    session.execute(text("""
        TRUNCATE TABLE
          dashboard_reminders,
          concern_flags,
          owner_notes,
          staff_leaves,
          practice_staff_sources,
          practice_staff,
          vet_practices,
          owner_gov_profiles,
          vet_cost_guidelines,
          medications,
          vaccinations,
          weights,
          vet_visits,
          organisation_members,
          organisations,
          owner_pets,
          owners,
          pets,
          users
        RESTART IDENTITY CASCADE;
    """))
    session.commit()


VET_GUIDELINE_ROWS = [
    # species, size, wet, dry, checkups, unscheduled, insurance, lifespan
    ("Dog", "Small", 520, 420, 340, 380, 680, 12),
    ("Dog", "Medium", 700, 560, 360, 460, 820, 12),
    ("Dog", "Large", 930, 760, 400, 620, 980, 12),
    ("Dog", "X-Large", 1220, 980, 440, 760, 1180, 12),
    ("Cat", "Small", 480, 260, 300, 260, 560, 16),
    ("Cat", "Medium", 640, 360, 320, 300, 640, 16),
    ("Cat", "Large", 780, 460, 340, 360, 720, 16),
    ("Cat", "X-Large", 930, 520, 360, 420, 780, 16),
    ("Horse", "X-Large", 2800, 2200, 800, 1600, 2200, 25),
    ("Bird", "Small", 220, 140, 180, 120, 220, 10),
]


def seed_vet_cost_guidelines(session) -> int:
    rows: list[VetCostGuideline] = []
    for species, size_class, wet, dry, checkups, unscheduled, insurance, lifespan in VET_GUIDELINE_ROWS:
        rows.append(
            VetCostGuideline(
                species=species,
                size_class=size_class,
                annual_food_wet=wet,
                annual_food_dry=dry,
                annual_checkups=checkups,
                annual_unscheduled=unscheduled,
                annual_insurance=insurance,
                avg_lifespan_years=lifespan,
            )
        )
    session.add_all(rows)
    session.commit()
    return len(rows)


def _fake_tfn() -> str:
    return "".join(random.choice(string.digits) for _ in range(9))


def _fake_ato_ref() -> str:
    return f"ATO-{random.randint(1000, 9999)}-{random.randint(100000, 999999)}"


def seed_owner_gov_profiles(session, owners: list[Owner]) -> int:
    # Generate financially varied profiles to exercise eligibility scoring ranges.
    rows: list[OwnerGovProfile] = []
    for owner in owners:
        taxable_income = random.randint(28000, 180000)
        assessed_tax = int(max(0, taxable_income * random.uniform(0.08, 0.29)))

        receiving_unemployment = random.random() < 0.12
        receiving_aged = random.random() < 0.10
        receiving_dva = random.random() < 0.04

        household_income = taxable_income + random.randint(0, 85000)
        living_expenses = random.randint(18000, 95000)
        housing_status = random.choices(["rent", "owner"], weights=[0.43, 0.57], k=1)[0]
        gov_housing = random.random() < (0.12 if housing_status == "rent" else 0.03)
        property_size_sqm = random.randint(45, 350)
        credit_score = random.randint(380, 900)

        rows.append(
            OwnerGovProfile(
                owner_id=owner.owner_id,
                tax_file_number=_fake_tfn(),
                ato_reference_number=_fake_ato_ref(),
                taxable_income=taxable_income,
                assessed_tax_payable=assessed_tax,
                receiving_centrelink_unemployment=receiving_unemployment,
                receiving_aged_pension=receiving_aged,
                receiving_dva_pension=receiving_dva,
                government_housing=gov_housing,
                housing_status=housing_status,
                property_size_sqm=property_size_sqm,
                household_income=household_income,
                credit_score=credit_score,
                basic_living_expenses=living_expenses,
            )
        )

    session.add_all(rows)
    session.commit()
    return len(rows)


def seed_users(session, n: int = 800) -> list[User]:
    # Base user population across OWNER/VET/ADMIN roles.
    users: list[User] = []
    used_emails = {e for e in session.execute(select(User.email)).scalars().all() if e}

    # Seed permanent deterministic accounts that are recreated on every reseed.
    for row in FIXED_ACCOUNTS:
        users.append(
            User(
                email=row["email"],
                password=hash_password(FIXED_ACCOUNT_PASSWORD),
                role=row["role"],
                full_name=row["full_name"],
                phone=generate_au_mobile(),
                address=_build_tas_address(row["suburb"], row["postcode"]),
            )
        )
        used_emails.add(row["email"])

    random_n = max(0, n - len(FIXED_ACCOUNTS))
    for _ in range(random_n):
        role = random.choices(
            population=["OWNER", "VET", "ADMIN"],
            weights=[0.6, 0.25, 0.15],
            k=1,
        )[0]
        full_name = fake.name()
        suburb, postcode = _pick_tas_locality()
        users.append(User(
            email=_generate_realistic_email(full_name, used_emails),
            password=generate_password(),
            role=role,
            full_name=full_name,
            phone=generate_au_mobile(),
            address=_build_tas_address(suburb, postcode),
        ))
    session.add_all(users)
    session.commit()
    return users


def seed_owners(session, users: list[User]) -> list[Owner]:
    # OWNER records are derived from users rather than generated independently.
    owners: list[Owner] = []
    for u in users:
        if (u.role or "").upper() != "OWNER":
            continue
        owners.append(Owner(
            user_id=u.user_id,
            verified_identity_level=random.choice([0, 1, 2])
        ))
    session.add_all(owners)
    session.commit()
    return owners


DOG_BREEDS = [
    "Labrador Retriever",
    "German Shepherd",
    "Golden Retriever",
    "French Bulldog",
    "Poodle",
    "Rottweiler",
    "Beagle",
    "Dachshund",
    "Border Collie",
    "Staffordshire Bull Terrier",
    "Cavalier King Charles Spaniel",
    "Australian Shepherd",
    "Siberian Husky",
    "Boxer",
    "Chihuahua",
]

CAT_BREEDS = [
    "Domestic Shorthair",
    "Domestic Longhair",
    "Maine Coon",
    "Ragdoll",
    "Persian",
    "Siamese",
    "Bengal",
    "British Shorthair",
    "Sphynx",
    "Scottish Fold",
    "Abyssinian",
    "Russian Blue",
    "Norwegian Forest Cat",
]

MEDICATION_POOL = [
    ("Carprofen", "25mg twice daily", "Give with food"),
    ("Prednisone", "5mg once daily", "Morning dose preferred"),
    ("Amoxicillin", "250mg twice daily", "Complete full course"),
    ("Gabapentin", "100mg at night", "For pain management"),
    ("Apoquel", "16mg once daily", "For itch control"),
]


def seed_pets(session, n: int = 1600) -> list[Pet]:
    # Build a mixed dog/cat population with realistic breed distribution.
    pets: list[Pet] = []

    for _ in range(n):
        species = random.choice(["Dog", "Cat"])
        breed = random.choice(DOG_BREEDS if species == "Dog" else CAT_BREEDS)

        pets.append(Pet(
            name=fake.first_name(),
            species=species,
            breed=breed,
            sex=random.choice(["Male", "Female"]),
            microchip_number="".join(random.choice(string.digits) for _ in range(15)),
            date_of_birth=fake.date_between(start_date="-10y", end_date="today")
        ))

    session.add_all(pets)
    session.commit()
    return pets


def seed_owner_pets(session, owners: list[Owner], pets: list[Pet]) -> int:
    # Current model assigns one primary owner per pet for deterministic joins.
    links: list[OwnerPet] = []
    for p in pets:
        o = random.choice(owners)
        links.append(OwnerPet(
            owner_id=o.owner_id,
            pet_id=p.pet_id,
            start_date=fake.date_between(start_date="-5y", end_date="today"),
            end_date=None,
            relationship_type="primary_owner"
        ))
    session.add_all(links)
    session.commit()
    return len(links)


def _vet_gateway_csv_path() -> Path:
    return Path(__file__).resolve().parents[1] / "services" / "vet_gateway" / "tas_vet_practices_enriched_partial.csv"


def _vet_staff_snapshot_csv_path() -> Path:
    return Path(__file__).resolve().parents[1] / "services" / "vet_gateway" / "tas_practice_staff_snapshot.csv"


def _parse_optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    v = str(value).strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    v = str(value).strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    v = str(value).strip()
    return v or None


def _normalize_whitespace(value: str | None) -> str | None:
    text_value = _normalize_optional_text(value)
    if not text_value:
        return None
    return " ".join(text_value.split())


def _normalize_role(value: str | None) -> tuple[str | None, str | None]:
    role_raw = _normalize_whitespace(value)
    if not role_raw:
        return None, None
    normalized = role_raw.lower()
    if any(token in normalized for token in ["veterinarian", "vet ", "veterinary surgeon"]):
        return "Veterinarian", role_raw
    if "nurse" in normalized:
        return "Vet Nurse", role_raw
    if "manager" in normalized:
        return "Practice Manager", role_raw
    if any(token in normalized for token in ["reception", "client care"]):
        return "Reception/Client Care", role_raw
    return role_raw.title(), role_raw


def _parse_optional_bool(value: str | None) -> bool | None:
    raw = _normalize_optional_text(value)
    if raw is None:
        return None
    normalized = raw.lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return None


def _parse_after_hours(value: str | None) -> tuple[bool | None, str | None]:
    raw = _normalize_optional_text(value)
    if not raw:
        return None, None
    val = raw.lower()
    if val.startswith("yes"):
        return True, raw
    if val.startswith("no"):
        return False, raw
    return None, raw


def _infer_practice_type(service_types: list[str], emergency_text: str | None) -> str:
    svc = " ".join(service_types).lower()
    em = (emergency_text or "").lower()
    if "emergency" in svc or "emergency" in em:
        return "emergency"
    if "mobile" in svc:
        return "mobile"
    if "special" in svc:
        return "specialist"
    if "hospital" in svc:
        return "hospital"
    return "clinic"


def _staff_guardrail_check(
    source_url: str | None,
    source_type: str | None,
    is_publicly_listed: bool | None,
) -> tuple[bool, str | None]:
    if not source_url:
        return False, "missing source_url"
    url_lower = source_url.lower()
    if "linkedin.com" in url_lower:
        return False, "linkedin sources are blocked"
    if source_type and source_type.lower() not in {"practice_website", "official_website"}:
        return False, "source_type is not a practice website"
    if is_publicly_listed is False:
        return False, "row not marked as publicly listed"
    return True, None


def seed_vet_practices_and_clinics_from_tas_data(session) -> tuple[list[Organisation], list[VetPractice], int]:
    # Ingest Tasmania real-world snapshot and keep both vet_practices + organisations in sync.
    csv_path = _vet_gateway_csv_path()
    if not csv_path.exists():
        print(f"TAS vet dataset not found at {csv_path}, falling back to synthetic clinics.")
        fallback_clinics = seed_clinics(session, 5)
        return fallback_clinics, [], 0

    practices: list[VetPractice] = []
    clinics: list[Organisation] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = _normalize_optional_text(row.get("name"))
            if not name:
                continue
            address = _normalize_optional_text(row.get("address"))
            suburb = _normalize_optional_text(row.get("suburb"))
            state = _normalize_optional_text(row.get("state")) or "TAS"
            postcode = _normalize_optional_text(row.get("postcode"))
            phone = _normalize_optional_text(row.get("phone"))
            website = _normalize_optional_text(row.get("website"))
            email = _normalize_optional_text(row.get("email"))
            facebook = _normalize_optional_text(row.get("facebook"))
            instagram = _normalize_optional_text(row.get("instagram"))
            emergency = _normalize_optional_text(row.get("emergency"))
            opening_hours = _normalize_optional_text(row.get("opening_hours"))
            service_types = [s.strip() for s in (row.get("service_types") or "").split(";") if s.strip()]
            after_hours_available, after_hours_notes = _parse_after_hours(row.get("after_hours"))
            source = _normalize_optional_text(row.get("source"))

            lat = _parse_optional_float(row.get("latitude"))
            lng = _parse_optional_float(row.get("longitude"))
            rating = _parse_optional_float(row.get("rating"))
            review_count = _parse_optional_int(row.get("review_count"))

            scraped_raw = _normalize_optional_text(row.get("scraped_at")) or datetime.now(UTC).isoformat()
            try:
                scraped_at = datetime.fromisoformat(scraped_raw.replace("Z", "+00:00"))
            except Exception:
                scraped_at = datetime.now(UTC)

            source_key = "|".join([(name or "").lower(), (address or "").lower(), (postcode or "").lower(), (source or "").lower()])
            practice_type = _infer_practice_type(service_types, emergency)

            practices.append(
                VetPractice(
                    source_key=source_key,
                    source=source,
                    name=name,
                    abn=None,
                    practice_type=practice_type,
                    phone=phone,
                    email=email,
                    website=website,
                    facebook_url=facebook,
                    instagram_url=instagram,
                    street_address=address,
                    suburb=suburb,
                    state=state,
                    postcode=postcode,
                    latitude=lat,
                    longitude=lng,
                    service_types=service_types or None,
                    opening_hours_text=opening_hours,
                    opening_hours_json=None,
                    after_hours_available=after_hours_available,
                    after_hours_notes=after_hours_notes,
                    emergency_referral=emergency,
                    rating=rating,
                    review_count=review_count,
                    scraped_at=scraped_at,
                )
            )

            clinics.append(
                Organisation(
                    name=name,
                    org_type="vet_clinic",
                    phone=phone,
                    email=email,
                    address=address,
                    suburb=suburb,
                    state=state,
                    postcode=postcode,
                    latitude=str(lat) if lat is not None else None,
                    longitude=str(lng) if lng is not None else None,
                )
            )

    session.add_all(practices)
    session.add_all(clinics)
    session.commit()
    return clinics, practices, len(practices)


def seed_practice_staff_from_snapshot(session, practices: list[VetPractice]) -> tuple[int, int]:
    """
    Load staff snapshots from vetted practice website sources only.

    Expected CSV columns:
      - practice_name, practice_address, practice_postcode
      - staff_name, role, bio, profile_image_url
      - source_url, source_type, is_publicly_listed
      - scraped_at, http_status
    """
    csv_path = _vet_staff_snapshot_csv_path()
    if not csv_path.exists():
        return 0, 0

    practice_index: dict[str, VetPractice] = {}
    for practice in practices:
        key = "|".join(
            [
                (practice.name or "").strip().lower(),
                (practice.street_address or "").strip().lower(),
                (practice.postcode or "").strip().lower(),
            ]
        )
        practice_index[key] = practice

    staff_rows: list[PracticeStaff] = []
    source_rows: list[PracticeStaffSource] = []
    seen_staff_keys: set[tuple[str, str, str, str]] = set()
    seen_source_keys: set[tuple[str, str]] = set()

    # Guardrails are enforced per-row before staff records are admitted.
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            practice_name = _normalize_whitespace(row.get("practice_name") or row.get("name"))
            practice_address = _normalize_whitespace(row.get("practice_address") or row.get("address")) or ""
            practice_postcode = _normalize_whitespace(row.get("practice_postcode") or row.get("postcode")) or ""
            if not practice_name:
                continue

            practice_key = "|".join([practice_name.lower(), practice_address.lower(), practice_postcode.lower()])
            practice = practice_index.get(practice_key)
            if not practice:
                continue

            source_url = _normalize_optional_text(row.get("source_url"))
            source_type = _normalize_optional_text(row.get("source_type"))
            is_publicly_listed = _parse_optional_bool(row.get("is_publicly_listed"))
            allowed, note = _staff_guardrail_check(source_url, source_type, is_publicly_listed)

            scraped_raw = _normalize_optional_text(row.get("scraped_at")) or datetime.now(UTC).isoformat()
            try:
                scraped_at = datetime.fromisoformat(scraped_raw.replace("Z", "+00:00"))
            except Exception:
                scraped_at = datetime.now(UTC)

            source_key = (str(practice.id), source_url or "")
            if source_key not in seen_source_keys:
                source_rows.append(
                    PracticeStaffSource(
                        practice_id=practice.id,
                        source_url=source_url or "missing",
                        http_status=_parse_optional_int(row.get("http_status")),
                        last_scraped_at=scraped_at,
                        parse_success=bool(allowed),
                        notes=note,
                    )
                )
                seen_source_keys.add(source_key)

            if not allowed:
                continue

            staff_name = _normalize_whitespace(row.get("staff_name"))
            role, role_raw = _normalize_role(row.get("role"))
            if not staff_name or not role or not source_url:
                continue

            staff_key = (str(practice.id), staff_name.lower(), role.lower(), source_url.lower())
            if staff_key in seen_staff_keys:
                continue

            staff_rows.append(
                PracticeStaff(
                    practice_id=practice.id,
                    staff_name=staff_name,
                    role=role,
                    role_raw=role_raw,
                    bio=_normalize_optional_text(row.get("bio")),
                    profile_image_url=_normalize_optional_text(row.get("profile_image_url")),
                    source_url=source_url,
                    scraped_at=scraped_at,
                    is_active=True,
                )
            )
            seen_staff_keys.add(staff_key)

    if source_rows:
        session.add_all(source_rows)
    if staff_rows:
        session.add_all(staff_rows)
    session.commit()
    return len(staff_rows), len(source_rows)


def seed_clinics(session, n: int = 5) -> list[Organisation]:
    clinics: list[Organisation] = []
    au_states = ["NSW", "VIC", "QLD", "WA", "SA", "ACT", "TAS", "NT"]
    for _ in range(n):
        suburb = fake.city()
        state = random.choice(au_states)
        postcode = f"{random.randint(2000, 7999)}"
        lat = round(random.uniform(-38.0, -12.0), 6)
        lng = round(random.uniform(113.0, 153.0), 6)
        clinics.append(Organisation(
            name=f"{fake.last_name()} Veterinary Clinic",
            org_type="vet_clinic",
            phone=generate_au_mobile(),
            email=f"contact@{fake.domain_word()}clinic.au",
            address=f"{fake.building_number()} {fake.street_name()}",
            suburb=suburb,
            state=state,
            postcode=postcode,
            latitude=str(lat),
            longitude=str(lng),
        ))
    session.add_all(clinics)
    session.commit()
    return clinics


def seed_vet_staff(session, clinics: list[Organisation]) -> list[User]:
    """
    Generate clinic staff per clinic with realistic role mix and contact details.

    Staff counts by clinic size bucket:
      - small: 8-12
      - medium: 12-18
      - large: 18-24
    """
    created_users: list[User] = []
    members: list[OrganisationMember] = []
    vet_users_for_visits: list[User] = []

    existing_emails = {
        e
        for e in session.execute(select(User.email)).scalars().all()
        if e
    }

    for clinic in clinics:
        # Size buckets emulate realistic staffing scales per clinic.
        size_bucket = random.choices(["small", "medium", "large"], weights=[0.5, 0.35, 0.15], k=1)[0]
        if size_bucket == "small":
            staff_total = random.randint(8, 12)
        elif size_bucket == "medium":
            staff_total = random.randint(12, 18)
        else:
            staff_total = random.randint(18, 24)

        admin_count = random.randint(1, min(4, max(1, staff_total // 4)))
        senior_vet_count = random.randint(1, 3 if size_bucket != "small" else 2)
        remaining = max(0, staff_total - admin_count - senior_vet_count)
        vet_tech_count = random.randint(1, min(4, remaining)) if remaining > 0 else 0
        veterinarian_count = max(1, staff_total - admin_count - senior_vet_count - vet_tech_count)

        role_plan = (
            [("admin_staff", "ADMIN")] * admin_count
            + [("senior_veterinarian", "VET")] * senior_vet_count
            + [("veterinarian", "VET")] * veterinarian_count
            + [("vet_tech", "VET")] * vet_tech_count
        )
        random.shuffle(role_plan)

        for member_role, app_role in role_plan:
            # Staff emails follow realistic person-style formats.
            first = fake.first_name()
            last = fake.last_name()
            full_name = f"{first} {last}"
            email = _generate_realistic_email(full_name, existing_emails)
            suburb = clinic.suburb or _pick_tas_locality()[0]
            postcode = clinic.postcode or _pick_tas_locality()[1]
            user = User(
                email=email,
                password=generate_password(),
                role=app_role,
                full_name=full_name,
                phone=generate_au_mobile(),
                address=_build_tas_address(suburb, postcode),
            )
            created_users.append(user)
            session.add(user)
            session.flush()

            members.append(
                OrganisationMember(
                    organisation_id=clinic.organisation_id,
                    user_id=user.user_id,
                    member_role=member_role,
                )
            )
            if member_role in {"veterinarian", "senior_veterinarian"}:
                vet_users_for_visits.append(user)

    session.add_all(members)
    session.commit()
    return vet_users_for_visits


def seed_visits_weights_vax(session, pets: list[Pet], clinics: list[Organisation], vet_users: list[User]) -> tuple[int, int, int]:
    # Visits drive downstream synthetic weights/vaccinations to keep dashboards populated.
    visits: list[VetVisit] = []
    weights: list[Weight] = []
    vax: list[Vaccination] = []

    routine_reasons = [
        "Annual check-up",
        "Vaccination",
        "Skin irritation",
        "Limping",
        "Dental",
        "Worming advice",
        "Weight check",
    ]
    cancellation_reasons = [
        "Cancelled: owner unavailable",
        "Cancelled: clinic reschedule",
        "No show: owner did not attend",
        "Did not attend",
    ]

    clinic_by_bucket: dict[str, list[Organisation]] = {"SOUTH": [], "NORTH_EAST": [], "NORTH_WEST": [], "UNKNOWN": []}
    for clinic in clinics:
        clinic_by_bucket[_postcode_bucket(clinic.postcode)].append(clinic)

    owner_postcode_by_pet: dict[uuid.UUID, str] = {}
    pet_owner_rows = session.execute(
        text(
            """
            SELECT op.pet_id::text AS pet_id, u.address AS owner_address
            FROM owner_pets op
            JOIN owners o ON o.owner_id = op.owner_id
            JOIN users u ON u.user_id = o.user_id
            WHERE op.end_date IS NULL
            """
        )
    ).mappings().all()
    for row in pet_owner_rows:
        owner_postcode_by_pet[uuid.UUID(row["pet_id"])] = _extract_postcode_from_address(row.get("owner_address")) or ""

    clinic_vet_user_ids: dict[uuid.UUID, list[uuid.UUID]] = {}
    clinic_vet_rows = session.execute(
        text(
            """
            SELECT om.organisation_id::text AS organisation_id, om.user_id::text AS user_id
            FROM organisation_members om
            JOIN users u ON u.user_id = om.user_id
            WHERE UPPER(COALESCE(u.role, '')) = 'VET'
            """
        )
    ).mappings().all()
    for row in clinic_vet_rows:
        cid = uuid.UUID(row["organisation_id"])
        uid = uuid.UUID(row["user_id"])
        clinic_vet_user_ids.setdefault(cid, []).append(uid)

    vet_lookup = {u.user_id: u for u in vet_users}

    now = datetime.now(UTC)
    for p in pets:
        num_visits = random.randint(1, 3)
        for _ in range(num_visits):
            visit_dt = now - timedelta(days=random.randint(0, 365 * 3))
            owner_postcode = owner_postcode_by_pet.get(p.pet_id)
            owner_bucket = _postcode_bucket(owner_postcode)
            candidate_clinics = clinic_by_bucket.get(owner_bucket) or clinics
            clinic = random.choice(candidate_clinics) if candidate_clinics else random.choice(clinics)

            clinic_vets = clinic_vet_user_ids.get(clinic.organisation_id, [])
            if clinic_vets:
                vet_user_id = random.choice(clinic_vets)
                vet = vet_lookup.get(vet_user_id)
            else:
                vet = random.choice(vet_users) if vet_users else None

            # Seed a meaningful cancellation/no-show rate for analytics/testing.
            if random.random() < 0.18:
                reason = random.choice(cancellation_reasons)
            else:
                reason = random.choice(routine_reasons)

            visit = VetVisit(
                pet_id=p.pet_id,
                organisation_id=clinic.organisation_id,
                vet_user_id=vet.user_id if vet else None,
                visit_datetime=visit_dt,
                reason=reason,
                notes_visible_to_owner=fake.sentence(nb_words=10)
            )
            visits.append(visit)

    session.add_all(visits)
    session.commit()

    for v in visits:
        # Cancelled/no-show visits should not produce measured clinical outcomes.
        reason_text = (v.reason or "").lower()
        is_cancelled = ("cancel" in reason_text) or ("no show" in reason_text) or ("did not attend" in reason_text)
        if is_cancelled:
            continue

        base = 10.0 if random.random() < 0.5 else 4.5
        weight_val = max(1.5, random.gauss(mu=base, sigma=2.0))
        weights.append(Weight(
            pet_id=v.pet_id,
            visit_id=v.visit_id,
            measured_at=v.visit_datetime,
            weight_kg=round(weight_val, 2),
            measured_by=v.vet_user_id
        ))

        prob = 0.6 if (v.reason and "Vaccin" in v.reason) else 0.15
        if random.random() < prob:
            vaccine_type = random.choice(DOG_VAX + CAT_VAX)
            vax.append(Vaccination(
                pet_id=v.pet_id,
                visit_id=v.visit_id,
                vaccine_type=vaccine_type,
                batch_number=fake.bothify(text="??####"),
                administered_at=v.visit_datetime,
                due_at=v.visit_datetime + timedelta(days=365)
            ))

    session.add_all(weights)
    session.add_all(vax)
    session.commit()

    return (len(visits), len(weights), len(vax))


VET_NOTE_TEMPLATES = [
    "TPR WNL. BCS {bcs}/9. Appetite stable, no vomiting/diarrhoea reported.",
    "Auscultation NAD. Mild gingivitis present. Recommend dental prophylaxis within {days} days.",
    "Recheck completed: otitis externa improving. Continue topical therapy and reassess in {days} days.",
    "Dermatology review: pruritus reduced on current management plan. Continue diet trial for {days} days.",
    "Orthopaedic exam: intermittent lameness, grade 1/5. Restrict high-impact activity and review in {days} days.",
    "Weight-management consult: target weight trajectory discussed. Daily ration adjusted; reweigh in {days} days.",
    "Post-vaccination check: no adverse effects noted. Preventative plan reviewed with owner.",
]

CONCERN_DESCRIPTIONS = [
    "Multiple missed appointments in the last 8 weeks; welfare follow-up call required.",
    "Owner-reported weight differs materially from clinic measure; verify home tracking method.",
    "Medication adherence uncertain based on refill gap; schedule compliance review.",
    "Chronic dermatitis not improving as expected; recommend escalation to senior vet.",
    "Behavioural decline reported with reduced enrichment; welfare check requested.",
]


def seed_owner_notes_flags_and_reminders(
    session,
    owners: list[Owner],
    pets: list[Pet],
    clinics: list[Organisation],
    vet_users: list[User],
) -> tuple[int, int, int]:
    # Build owner/pet mapping for realistic, linked clinical records.
    owner_pet_rows = session.execute(
        text(
            """
            SELECT op.owner_id::text AS owner_id, op.pet_id::text AS pet_id
            FROM owner_pets op
            WHERE op.end_date IS NULL
            """
        )
    ).mappings().all()
    pets_by_owner: dict[uuid.UUID, list[uuid.UUID]] = {}
    for row in owner_pet_rows:
        oid = uuid.UUID(row["owner_id"])
        pid = uuid.UUID(row["pet_id"])
        pets_by_owner.setdefault(oid, []).append(pid)

    # Map pets to likely clinics from prior visits to keep reminders logical.
    clinic_by_pet: dict[uuid.UUID, uuid.UUID] = {}
    visit_rows = session.execute(
        text(
            """
            SELECT DISTINCT ON (vv.pet_id)
              vv.pet_id::text AS pet_id,
              vv.organisation_id::text AS organisation_id
            FROM vet_visits vv
            WHERE vv.organisation_id IS NOT NULL
            ORDER BY vv.pet_id, vv.visit_datetime DESC
            """
        )
    ).mappings().all()
    for row in visit_rows:
        clinic_by_pet[uuid.UUID(row["pet_id"])] = uuid.UUID(row["organisation_id"])

    notes_rows: list[dict] = []
    concern_rows: list[dict] = []
    reminder_rows: list[dict] = []
    now = datetime.now(UTC)
    vet_ids = [u.user_id for u in vet_users] if vet_users else []

    for owner in owners:
        owner_pet_ids = pets_by_owner.get(owner.owner_id, [])
        if not owner_pet_ids:
            continue

        note_count = random.randint(1, 4)
        for _ in range(note_count):
            pet_id = random.choice(owner_pet_ids)
            template = random.choice(VET_NOTE_TEMPLATES)
            notes_rows.append(
                {
                    "note_id": uuid.uuid4(),
                    "owner_id": owner.owner_id,
                    "pet_id": pet_id,
                    "author_user_id": random.choice(vet_ids) if vet_ids else None,
                    "note_text": template.format(bcs=random.randint(4, 7), days=random.choice([7, 10, 14, 21, 28])),
                    "note_type": random.choice(["CHECKUP", "FOLLOWUP", "MEDICATION", "WELFARE"]),
                    "created_at": now - timedelta(days=random.randint(0, 120)),
                }
            )

            # Seed owner reminders suitable for dashboard calendar and follow-up workflows.
            reminder_rows.append(
                {
                    "reminder_id": uuid.uuid4(),
                    "role_scope": "OWNER",
                    "user_id": None,
                    "organisation_id": clinic_by_pet.get(pet_id),
                    "owner_id": owner.owner_id,
                    "pet_id": pet_id,
                    "title": random.choice(["Medication review", "Weight recheck", "Follow-up appointment"]),
                    "details": "Auto-generated follow-up reminder from latest care plan.",
                    "reminder_type": random.choice(["FOLLOWUP", "REMINDER"]),
                    "due_at": now + timedelta(days=random.randint(-20, 45)),
                    "status": random.choice(["OPEN", "OPEN", "DONE"]),
                    "created_by_user_id": random.choice(vet_ids) if vet_ids else None,
                    "created_at": now - timedelta(days=random.randint(0, 30)),
                }
            )

        if random.random() < 0.28:
            concern_pet = random.choice(owner_pet_ids)
            concern_rows.append(
                {
                    "flag_id": uuid.uuid4(),
                    "owner_id": owner.owner_id,
                    "pet_id": concern_pet,
                    "raised_by_user_id": random.choice(vet_ids) if vet_ids else None,
                    "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "status": random.choice(["OPEN", "OPEN", "UNDER_REVIEW"]),
                    "category": random.choice(["WELFARE", "COMPLIANCE", "MEDICATION", "FOLLOW_UP"]),
                    "description": random.choice(CONCERN_DESCRIPTIONS),
                    "created_at": now - timedelta(days=random.randint(0, 90)),
                }
            )

    # Seed clinic-level operational reminders for admin and vet dashboards.
    clinic_ids = [c.organisation_id for c in clinics]
    for clinic_id in clinic_ids:
        for _ in range(random.randint(4, 8)):
            reminder_rows.append(
                {
                    "reminder_id": uuid.uuid4(),
                    "role_scope": "VET",
                    "user_id": None,
                    "organisation_id": clinic_id,
                    "owner_id": None,
                    "pet_id": None,
                    "title": random.choice(["Call owner follow-up", "Review cancelled appointments", "Medication stock check"]),
                    "details": "Clinic operations task generated for monthly workflow tracking.",
                    "reminder_type": random.choice(["FOLLOWUP", "CONCERN", "REMINDER"]),
                    "due_at": now + timedelta(days=random.randint(-15, 30)),
                    "status": random.choice(["OPEN", "OPEN", "DONE"]),
                    "created_by_user_id": random.choice(vet_ids) if vet_ids else None,
                    "created_at": now - timedelta(days=random.randint(0, 40)),
                }
            )
        for _ in range(random.randint(3, 6)):
            reminder_rows.append(
                {
                    "reminder_id": uuid.uuid4(),
                    "role_scope": "ADMIN",
                    "user_id": None,
                    "organisation_id": clinic_id,
                    "owner_id": None,
                    "pet_id": None,
                    "title": random.choice(["Audit unresolved concerns", "KPI review meeting", "Investigate missed appointments"]),
                    "details": "Admin-level calendar item linked to clinic performance monitoring.",
                    "reminder_type": random.choice(["CONCERN", "REMINDER"]),
                    "due_at": now + timedelta(days=random.randint(-10, 35)),
                    "status": random.choice(["OPEN", "OPEN", "DONE"]),
                    "created_by_user_id": random.choice(vet_ids) if vet_ids else None,
                    "created_at": now - timedelta(days=random.randint(0, 45)),
                }
            )

    for row in notes_rows:
        session.execute(
            text(
                """
                INSERT INTO owner_notes (note_id, owner_id, pet_id, author_user_id, note_text, note_type, created_at)
                VALUES (:note_id, :owner_id, :pet_id, :author_user_id, :note_text, :note_type, :created_at)
                """
            ),
            row,
        )
    for row in concern_rows:
        session.execute(
            text(
                """
                INSERT INTO concern_flags (flag_id, owner_id, pet_id, raised_by_user_id, severity, status, category, description, created_at)
                VALUES (:flag_id, :owner_id, :pet_id, :raised_by_user_id, :severity, :status, :category, :description, :created_at)
                """
            ),
            row,
        )
    for row in reminder_rows:
        session.execute(
            text(
                """
                INSERT INTO dashboard_reminders (
                  reminder_id, role_scope, user_id, organisation_id, owner_id, pet_id, title, details,
                  reminder_type, due_at, status, created_by_user_id, created_at
                )
                VALUES (
                  :reminder_id, :role_scope, :user_id, :organisation_id, :owner_id, :pet_id, :title, :details,
                  :reminder_type, :due_at, :status, :created_by_user_id, :created_at
                )
                """
            ),
            row,
        )
    session.commit()
    return len(notes_rows), len(concern_rows), len(reminder_rows)


def seed_medications(session, pets: list[Pet]) -> int:
    meds: list[Medication] = []
    for pet in pets:
        if random.random() < 0.35:
            name, dosage, instructions = random.choice(MEDICATION_POOL)
            meds.append(
                Medication(
                    pet_id=pet.pet_id,
                    name=name,
                    dosage=dosage,
                    instructions=instructions,
                    start_date=fake.date_between(start_date="-6m", end_date="today"),
                    end_date=fake.date_between(start_date="today", end_date="+6m") if random.random() < 0.7 else None,
                )
            )
    session.add_all(meds)
    session.commit()
    return len(meds)


def seed_staff_leave(session, clinics: list[Organisation], vet_users: list[User]) -> int:
    member_rows = session.execute(
        text(
            """
            SELECT organisation_id::text AS organisation_id, user_id::text AS user_id, member_role
            FROM organisation_members
            """
        )
    ).mappings().all()
    if not member_rows:
        return 0

    now = datetime.now(UTC).date()
    leaves: list[StaffLeave] = []
    sample_size = min(max(30, len(member_rows) // 3), len(member_rows))
    for row in random.sample(member_rows, k=sample_size):
        # Ensure we generate a mix of historical, current, and future leave states.
        pattern = random.choices(
            ["past", "current", "upcoming_approved", "upcoming_pending"],
            weights=[0.35, 0.2, 0.25, 0.2],
            k=1,
        )[0]
        duration = random.randint(1, 10)
        if pattern == "past":
            end_date = now - timedelta(days=random.randint(5, 120))
            start_date = end_date - timedelta(days=duration)
            status = "APPROVED"
        elif pattern == "current":
            start_date = now - timedelta(days=random.randint(0, 4))
            end_date = now + timedelta(days=random.randint(1, 8))
            status = "APPROVED"
        elif pattern == "upcoming_approved":
            start_date = now + timedelta(days=random.randint(2, 45))
            end_date = start_date + timedelta(days=duration)
            status = "APPROVED"
        else:
            start_date = now + timedelta(days=random.randint(3, 60))
            end_date = start_date + timedelta(days=duration)
            status = "PENDING"

        leaves.append(
            StaffLeave(
                organisation_id=uuid.UUID(row["organisation_id"]),
                user_id=uuid.UUID(row["user_id"]),
                start_date=start_date,
                end_date=end_date,
                reason=random.choice(["Annual leave", "Study leave", "Personal leave", "Conference"]),
                status=status,
            )
        )
    session.add_all(leaves)
    session.commit()
    return len(leaves)


if __name__ == "__main__":
    # Full reseed pipeline used by docker exec -it petcheck_backend python -m app.scripts.seed_data
    session = SessionLocal()
    try:
        print("Ensuring users auth columns...")
        ensure_user_auth_columns(session)
        print("Ensuring pet health columns...")
        ensure_pet_health_columns(session)
        print("Ensuring clinic profile columns...")
        ensure_clinic_profile_columns(session)
        print("Ensuring risk/eligibility tables...")
        ensure_risk_tables(session)
        print("Ensuring care coordination tables...")
        ensure_care_coordination_tables(session)

        print("Resetting tables...")
        reset_db(session)

        print("Seeding users (800)...")
        users = seed_users(session, 800)

        print("Seeding owners (200)...")
        owners = seed_owners(session, users)

        print("Seeding vet cost guidelines...")
        guideline_n = seed_vet_cost_guidelines(session)

        print("Seeding owner government profiles...")
        gov_profile_n = seed_owner_gov_profiles(session, owners)

        print("Seeding pets (1600)...")
        pets = seed_pets(session, 1600)

        print("Linking owner_pets (1600)...")
        seed_owner_pets(session, owners, pets)

        print("Seeding clinics (5)...")
        clinics, practices, practice_n = seed_vet_practices_and_clinics_from_tas_data(session)

        print("Seeding practice staff snapshot (if available)...")
        practice_staff_n, practice_staff_source_n = seed_practice_staff_from_snapshot(session, practices)

        print("Seeding vet staff (size-based by clinic)...")
        vet_users = seed_vet_staff(session, clinics)

        print("Seeding visits + weights + vaccinations...")
        visit_n, weight_n, vax_n = seed_visits_weights_vax(session, pets, clinics, vet_users)
        med_n = seed_medications(session, pets)
        leave_n = seed_staff_leave(session, clinics, vet_users)
        note_n, concern_n, reminder_n = seed_owner_notes_flags_and_reminders(session, owners, pets, clinics, vet_users)

        all_users = session.execute(select(User)).scalars().all()
        creds_path = export_credentials(all_users)

        print(
            f"Done. visits={visit_n}, weights={weight_n}, vaccinations={vax_n}, medications={med_n}, "
            f"staff_leave={leave_n}, vet_practices={practice_n}, practice_staff={practice_staff_n}, "
            f"practice_staff_sources={practice_staff_source_n}, vet_guidelines={guideline_n}, "
            f"owner_gov_profiles={gov_profile_n}, owner_notes={note_n}, concern_flags={concern_n}, reminders={reminder_n}"
        )
        print(f"Fixed account password: {FIXED_ACCOUNT_PASSWORD}")
        print("Fixed accounts: admin@petprotect.local, vet@petprotect.local, owner@petprotect.local")
        print("All other seeded users keep randomly generated passwords.")
        print(f"Credentials export: {creds_path}")
    finally:
        session.close()

