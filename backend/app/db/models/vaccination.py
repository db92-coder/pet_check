"""Module: vaccination."""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class Vaccination(Base):
    __tablename__ = "vaccinations"

    vaccination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pets.pet_id", ondelete="CASCADE"),
        nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vet_visits.visit_id", ondelete="SET NULL"),
        nullable=True
    )

    vaccine_type: Mapped[str] = mapped_column(String, nullable=False)
    batch_number: Mapped[str] = mapped_column(String, nullable=True)
    administered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

