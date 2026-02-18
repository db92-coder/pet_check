from app.db.session import engine
from app.db.base import Base

# Import models so they register with Base.metadata
from app.db.models.user import User  # noqa: F401
from app.db.models.pet import Pet    # noqa: F401
from app.db.models.owner import Owner  # noqa: F401
from app.db.models.owner_pet import OwnerPet  # noqa: F401

from app.db.models.organisation import Organisation  # noqa: F401
from app.db.models.organisation_member import OrganisationMember  # noqa: F401
from app.db.models.vet_visit import VetVisit  # noqa: F401
from app.db.models.weight import Weight  # noqa: F401
from app.db.models.vaccination import Vaccination  # noqa: F401

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
