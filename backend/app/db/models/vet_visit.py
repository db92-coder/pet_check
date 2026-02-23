"""Module: vet_visit."""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Clinical visit/appointment records for pets with optional clinic and vet context.
class VetVisit(Base):
    __tablename__ = "vet_visits"

    visit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pets.pet_id", ondelete="CASCADE"),
        nullable=False
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.organisation_id", ondelete="SET NULL"),
        nullable=True
    )
    vet_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )

    visit_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=True)
    notes_visible_to_owner: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

