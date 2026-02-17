from app.db.session import engine
from app.db.base import Base

# IMPORTANT: import models so they register with Base.metadata
from app.db.models.user import User  # noqa: F401
from app.db.models.pet import Pet    # noqa: F401

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
