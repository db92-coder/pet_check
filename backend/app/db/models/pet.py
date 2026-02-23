"""Module: pet."""

import uuid
from datetime import datetime

from sqlalchemy import String, Date, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Core pet profile model used by visits, vaccinations, weights, and owner dashboards.
class Pet(Base):
    __tablename__ = "pets"

    # Primary Key
    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Basic Info
    name: Mapped[str] = mapped_column(String, nullable=False)
    species: Mapped[str] = mapped_column(String, nullable=False)
    breed: Mapped[str] = mapped_column(String, nullable=True)
    sex: Mapped[str] = mapped_column(String, nullable=True)
    microchip_number: Mapped[str] = mapped_column(String, nullable=True)
    photo_url: Mapped[str] = mapped_column(String, nullable=True)
    photo_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    photo_mime_type: Mapped[str] = mapped_column(String, nullable=True)

    # Optional Info
    date_of_birth: Mapped[datetime] = mapped_column(Date, nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

