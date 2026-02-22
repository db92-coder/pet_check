from faker import Faker
import random
import string
import csv
import uuid
from pathlib import Path
from datetime import datetime, UTC, timedelta
from sqlalchemy import text

from app.db.session import SessionLocal

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

fake = Faker()

DOG_VAX = ["C5", "C3", "Rabies"]
CAT_VAX = ["F3", "FIV", "Rabies"]

def generate_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def generate_au_mobile() -> str:
    # Australian mobile format: 04 + 8 digits
    return "04" + "".join(random.choice(string.digits) for _ in range(8))


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
    session.commit()


def ensure_risk_tables(session) -> None:
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


def export_credentials(users: list[User]) -> Path:
    out_path = Path(__file__).resolve().parent / "seeded_user_credentials.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "email", "password", "role"])
        for user in users:
            writer.writerow([str(user.user_id), user.email, user.password, user.role])
    return out_path


def reset_db(session) -> None:
    session.execute(text("""
        TRUNCATE TABLE
          staff_leaves,
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


def seed_users(session, n: int = 200) -> list[User]:
    users: list[User] = []
    for _ in range(n):
        role = random.choices(
            population=["OWNER", "VET", "ADMIN"],
            weights=[0.6, 0.25, 0.15],
            k=1,
        )[0]
        users.append(User(
            email=fake.unique.email(),
            password=generate_password(),
            role=role,
            full_name=fake.name(),
            phone=generate_au_mobile(),
            address=fake.address().replace("\n", ", "),
        ))
    session.add_all(users)
    session.commit()
    return users


def seed_owners(session, users: list[User]) -> list[Owner]:
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


def seed_pets(session, n: int = 400) -> list[Pet]:
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


def seed_vet_staff(session, users: list[User], clinics: list[Organisation], n_vets: int = 25) -> list[User]:
    eligible = [u for u in users if (u.role or "").upper() == "VET"]
    if not eligible:
        return []

    vet_users = random.sample(eligible, k=min(n_vets, len(eligible)))
    members: list[OrganisationMember] = []

    clinic_has_manager: dict[str, bool] = {str(c.organisation_id): False for c in clinics}

    for u in vet_users:
        clinic = random.choice(clinics)
        cid = str(clinic.organisation_id)
        role = "manager" if not clinic_has_manager[cid] else random.choice(["vet", "nurse"])
        clinic_has_manager[cid] = True
        members.append(OrganisationMember(
            organisation_id=clinic.organisation_id,
            user_id=u.user_id,
            member_role=role
        ))

    session.add_all(members)
    session.commit()
    return vet_users


def seed_visits_weights_vax(session, pets: list[Pet], clinics: list[Organisation], vet_users: list[User]) -> tuple[int, int, int]:
    visits: list[VetVisit] = []
    weights: list[Weight] = []
    vax: list[Vaccination] = []

    reasons = ["Annual check-up", "Vaccination", "Skin irritation", "Limping", "Dental", "Worming advice", "Weight check"]

    now = datetime.now(UTC)
    for p in pets:
        num_visits = random.randint(1, 3)
        for _ in range(num_visits):
            visit_dt = now - timedelta(days=random.randint(0, 365 * 3))
            clinic = random.choice(clinics)
            vet = random.choice(vet_users) if vet_users else None

            visit = VetVisit(
                pet_id=p.pet_id,
                organisation_id=clinic.organisation_id,
                vet_user_id=vet.user_id if vet else None,
                visit_datetime=visit_dt,
                reason=random.choice(reasons),
                notes_visible_to_owner=fake.sentence(nb_words=10)
            )
            visits.append(visit)

    session.add_all(visits)
    session.commit()

    for v in visits:
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
    if not vet_users:
        return 0

    member_rows = session.execute(
        text(
            """
            SELECT organisation_id::text AS organisation_id, user_id::text AS user_id
            FROM organisation_members
            """
        )
    ).mappings().all()
    if not member_rows:
        return 0

    now = datetime.now(UTC).date()
    leaves: list[StaffLeave] = []
    for row in random.sample(member_rows, k=min(20, len(member_rows))):
        start_delta = random.randint(-15, 45)
        duration = random.randint(1, 10)
        start_date = now + timedelta(days=start_delta)
        end_date = start_date + timedelta(days=duration)
        status = "APPROVED" if start_delta <= 20 else "PENDING"
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

        print("Resetting tables...")
        reset_db(session)

        print("Seeding users (200)...")
        users = seed_users(session, 200)
        creds_path = export_credentials(users)

        print("Seeding owners (200)...")
        owners = seed_owners(session, users)

        print("Seeding vet cost guidelines...")
        guideline_n = seed_vet_cost_guidelines(session)

        print("Seeding owner government profiles...")
        gov_profile_n = seed_owner_gov_profiles(session, owners)

        print("Seeding pets (400)...")
        pets = seed_pets(session, 400)

        print("Linking owner_pets (400)...")
        seed_owner_pets(session, owners, pets)

        print("Seeding clinics (5)...")
        clinics = seed_clinics(session, 5)

        print("Seeding vet staff (25)...")
        vet_users = seed_vet_staff(session, users, clinics, 25)

        print("Seeding visits + weights + vaccinations...")
        visit_n, weight_n, vax_n = seed_visits_weights_vax(session, pets, clinics, vet_users)
        med_n = seed_medications(session, pets)
        leave_n = seed_staff_leave(session, clinics, vet_users)

        print(
            f"Done. visits={visit_n}, weights={weight_n}, vaccinations={vax_n}, medications={med_n}, "
            f"staff_leave={leave_n}, vet_guidelines={guideline_n}, owner_gov_profiles={gov_profile_n}"
        )
        print("Generated unique passwords for all users in users.password")
        print(f"Credentials export: {creds_path}")
    finally:
        session.close()
