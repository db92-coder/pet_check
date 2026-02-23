"""Module: weight."""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Weight measurements captured for pets over time for health trend analysis.
class Weight(Base):
    __tablename__ = "weights"

    weight_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

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
    measured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    measured_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

