"""Module: practice_staff_source."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Captures provenance/parse status for each clinic staff source URL scrape.
class PracticeStaffSource(Base):
    __tablename__ = "practice_staff_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vet_practices.id", ondelete="CASCADE"), nullable=False
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=True)
    last_scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parse_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

