"""Module: vet_practice."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Real-world vet practice snapshot with contact, services, and rating metadata.
class VetPractice(Base):
    __tablename__ = "vet_practices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String, nullable=True)

    name: Mapped[str] = mapped_column(String, nullable=False)
    abn: Mapped[str] = mapped_column(String, nullable=True)
    practice_type: Mapped[str] = mapped_column(String, nullable=True)

    phone: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    website: Mapped[str] = mapped_column(String, nullable=True)
    facebook_url: Mapped[str] = mapped_column(String, nullable=True)
    instagram_url: Mapped[str] = mapped_column(String, nullable=True)

    street_address: Mapped[str] = mapped_column(String, nullable=True)
    suburb: Mapped[str] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=True)
    postcode: Mapped[str] = mapped_column(String, nullable=True)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=True)

    service_types: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    opening_hours_text: Mapped[str] = mapped_column(String, nullable=True)
    opening_hours_json: Mapped[str] = mapped_column(String, nullable=True)
    after_hours_available: Mapped[bool] = mapped_column(Boolean, nullable=True)
    after_hours_notes: Mapped[str] = mapped_column(String, nullable=True)
    emergency_referral: Mapped[str] = mapped_column(String, nullable=True)

    rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

