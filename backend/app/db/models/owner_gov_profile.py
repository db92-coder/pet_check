"""Module: owner_gov_profile."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Holds simulated government/financial profile inputs used for eligibility scoring.
class OwnerGovProfile(Base):
    __tablename__ = "owner_gov_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("owners.owner_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    tax_file_number: Mapped[str] = mapped_column(String, nullable=False)
    ato_reference_number: Mapped[str] = mapped_column(String, nullable=False)
    taxable_income: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    assessed_tax_payable: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    receiving_centrelink_unemployment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    receiving_aged_pension: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    receiving_dva_pension: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    government_housing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    housing_status: Mapped[str] = mapped_column(String, nullable=False, default="rent")
    property_size_sqm: Mapped[int] = mapped_column(Integer, nullable=False, default=80)

    household_income: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    basic_living_expenses: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

