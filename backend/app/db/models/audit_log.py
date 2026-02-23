"""Module: audit_log."""

import uuid
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.db.base import Base

# Stores immutable audit trail entries for key actions and integration events.
class AuditLog(Base):
    __tablename__ = "audit_log"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    meta: Mapped[dict] = mapped_column(JSON)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

