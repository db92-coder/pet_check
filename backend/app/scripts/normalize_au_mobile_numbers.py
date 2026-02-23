"""Module: normalize_au_mobile_numbers."""

import random
import string
from app.db.session import SessionLocal
from app.db.models.user import User


# Utility generator for AU mobile format: 04XXXXXXXX.
def generate_au_mobile() -> str:
    return "04" + "".join(random.choice(string.digits) for _ in range(8))


if __name__ == "__main__":
    # One-off maintenance script to normalize all user phone numbers in-place.
    session = SessionLocal()
    try:
        users = session.query(User).all()
        for user in users:
            user.phone = generate_au_mobile()
        session.commit()
        print(f"Updated phone numbers for {len(users)} users to AU mobile format.")
    finally:
        session.close()

