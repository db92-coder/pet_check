"""Module: deps."""

from typing import Generator
from sqlalchemy.orm import Session

# CHANGE THIS import to wherever SessionLocal lives in your repo
from app.db.session import SessionLocal

# Dependency provider: one DB session per request lifecycle.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

