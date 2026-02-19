from faker import Faker
import random
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

fake = Faker()

DOG_VAX = ["C5", "C3", "Rabies"]
CAT_VAX = ["F3", "FIV", "Rabies"]

def reset_db(session) -> None:
    # Drop in FK-safe order (truncate with cascade helps, but order keeps it tidy)
    session.execute(text("""
        TRUNCATE TABLE
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

def seed_users(session, n: int = 200) -> list[User]:
    users: list[User] = []
    for _ in range(n):
        users.append(User(
            email=fake.unique.email(),
            full_name=fake.name(),
            phone=fake.phone_number()
        ))
    session.add_all(users)
    session.commit()
    return users

def seed_owners(session, users: list[User]) -> list[Owner]:
    owners: list[Owner] = []
    for u in users:
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


def seed_pets(session, n: int = 400) -> list[Pet]:
    pets: list[Pet] = []

    for _ in range(n):
        species = random.choice(["Dog", "Cat"])

        if species == "Dog":
            breed = random.choice(DOG_BREEDS)
        else:
            breed = random.choice(CAT_BREEDS)

        pets.append(Pet(
            name=fake.first_name(),
            species=species,
            breed=breed,
            sex=random.choice(["Male", "Female"]),
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
    for i in range(n):
        clinics.append(Organisation(
            name=f"{fake.last_name()} Veterinary Clinic",
            org_type="vet_clinic"
        ))
    session.add_all(clinics)
    session.commit()
    return clinics

def seed_vet_staff(session, users: list[User], clinics: list[Organisation], n_vets: int = 25) -> list[User]:
    vet_users = random.sample(users, k=min(n_vets, len(users)))
    members: list[OrganisationMember] = []

    for u in vet_users:
        clinic = random.choice(clinics)
        members.append(OrganisationMember(
            organisation_id=clinic.organisation_id,
            user_id=u.user_id,
            member_role=random.choice(["vet", "nurse"])
        ))

    session.add_all(members)
    session.commit()
    return vet_users

def seed_visits_weights_vax(session, pets: list[Pet], clinics: list[Organisation], vet_users: list[User]) -> tuple[int,int,int]:
    visits: list[VetVisit] = []
    weights: list[Weight] = []
    vax: list[Vaccination] = []

    reasons = ["Annual check-up", "Vaccination", "Skin irritation", "Limping", "Dental", "Worming advice", "Weight check"]

    now = datetime.now(UTC)
    for p in pets:
        # 1–3 visits per pet
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

    # Build weights + some vaccinations per visit
    for v in visits:
        # 1 weight per visit
        base = 10.0 if random.random() < 0.5 else 4.5  # rough dog vs cat bias
        weight_val = max(1.5, random.gauss(mu=base, sigma=2.0))
        weights.append(Weight(
            pet_id=v.pet_id,
            visit_id=v.visit_id,
            measured_at=v.visit_datetime,
            weight_kg=round(weight_val, 2),
            measured_by=v.vet_user_id
        ))

        # ~60% of visits include a vaccination if the reason suggests it, else ~15%
        prob = 0.6 if (v.reason and "Vaccin" in v.reason) else 0.15
        if random.random() < prob:
            # Pick vaccine based on species (we need species; quick lookup in memory)
            # We'll infer with a bias; later we’ll do proper joins/relationships.
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

if __name__ == "__main__":

    session = SessionLocal()
    try:
        print("Resetting tables...")
        reset_db(session)

        print("Seeding users (200)...")
        users = seed_users(session, 200)

        print("Seeding owners (200)...")
        owners = seed_owners(session, users)

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

        print(f"Done. visits={visit_n}, weights={weight_n}, vaccinations={vax_n}")
    finally:
        session.close()