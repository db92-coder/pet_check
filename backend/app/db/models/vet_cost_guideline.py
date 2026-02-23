"""Module: vet_cost_guideline."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Reference cost guideline rows used in vet-side affordability/risk scoring.
class VetCostGuideline(Base):
    __tablename__ = "vet_cost_guidelines"

    guideline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    species: Mapped[str] = mapped_column(String, nullable=False)
    size_class: Mapped[str] = mapped_column(String, nullable=False)

    annual_food_wet: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    annual_food_dry: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    annual_checkups: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    annual_unscheduled: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    annual_insurance: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    avg_lifespan_years: Mapped[int] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

