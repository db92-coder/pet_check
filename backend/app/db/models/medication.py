"""Module: medication."""

import uuid
from datetime import date
from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Represents medications prescribed to a pet, including dosage and treatment window.
class Medication(Base):
    __tablename__ = "medications"

    medication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pets.pet_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    dosage: Mapped[str] = mapped_column(String, nullable=True)
    instructions: Mapped[str] = mapped_column(String, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)

