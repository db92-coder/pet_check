from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal  # <-- adjust if your SessionLocal lives elsewhere

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
