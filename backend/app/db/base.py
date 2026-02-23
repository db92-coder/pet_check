"""Module: base."""

from sqlalchemy.orm import DeclarativeBase

# Shared SQLAlchemy declarative base that all ORM models inherit from.
# This gives each model access to common metadata for table creation/migrations.
class Base(DeclarativeBase):
    pass

