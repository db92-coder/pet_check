"""Module: practice_staff."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Snapshot table for publicly listed clinic staff sourced from practice websites.
class PracticeStaff(Base):
    __tablename__ = "practice_staff"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vet_practices.id", ondelete="CASCADE"), nullable=False
    )
    staff_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    role_raw: Mapped[str] = mapped_column(Text, nullable=True)
    bio: Mapped[str] = mapped_column(Text, nullable=True)
    profile_image_url: Mapped[str] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

