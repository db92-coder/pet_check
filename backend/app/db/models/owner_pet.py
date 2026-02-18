import uuid
from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class OwnerPet(Base):
    __tablename__ = "owner_pets"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("owners.owner_id", ondelete="CASCADE"),
        primary_key=True
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pets.pet_id", ondelete="CASCADE"),
        primary_key=True
    )
    start_date: Mapped[Date] = mapped_column(Date, primary_key=True)
    end_date: Mapped[Date] = mapped_column(Date, nullable=True)
    relationship_type: Mapped[str] = mapped_column(String, nullable=False, default="primary_owner")
