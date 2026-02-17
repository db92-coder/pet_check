from faker import Faker
import random

from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.db.models.user import User
from app.db.models.pet import Pet

fake = Faker()

def seed_users(session, n=100):
    users = []
    for _ in range(n):
        users.append(
            User(
                email=fake.unique.email(),
                full_name=fake.name(),
                phone=fake.phone_number()
            )
        )
    session.add_all(users)
    session.commit()
    return users

def seed_pets(session, n=200):
    pets = []
    for _ in range(n):
        pets.append(
            Pet(
                name=fake.first_name(),
                species=random.choice(["Dog", "Cat"]),
                breed=fake.word(),
                sex=random.choice(["Male", "Female"]),
                date_of_birth=fake.date_between(start_date="-10y", end_date="today")
            )
        )
    session.add_all(pets)
    session.commit()
    return pets

if __name__ == "__main__":
    init_db()

    session = SessionLocal()
    try:
        print("Seeding users...")
        seed_users(session, 100)

        print("Seeding pets...")
        seed_pets(session, 200)

        print("Done.")
    finally:
        session.close()
