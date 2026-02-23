"""Module: owners."""

import uuid
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
from app.api.v1.routes.deps import get_db
from app.db.models.owner import Owner
from app.db.models.user import User
from app.db.models.owner_pet import OwnerPet
from app.db.models.pet import Pet
from app.db.models.vet_visit import VetVisit
from app.db.models.organisation import Organisation

router = APIRouter()


# Validate and coerce UUID inputs from query/path payloads.
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("", summary="List owners (simple)")
def list_owners(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Owner.owner_id.label("id"),
            Owner.user_id.label("user_id"),
            Owner.verified_identity_level.label("verified_identity_level"),
            User.full_name.label("full_name"),
            User.email.label("email"),
            User.phone.label("phone"),
            User.address.label("address"),
        )
        .join(User, User.user_id == Owner.user_id)
        .offset(offset)
        .limit(limit)
    ).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        d["user_id"] = str(d["user_id"])

        owner_id = uuid.UUID(d["id"])
        year_ago = datetime.now(UTC) - timedelta(days=365)
        visit_count_year = db.execute(
            select(func.count(VetVisit.visit_id))
            .select_from(VetVisit)
            .join(Pet, Pet.pet_id == VetVisit.pet_id)
            .join(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
            .where(OwnerPet.owner_id == owner_id, VetVisit.visit_datetime >= year_ago)
        ).scalar_one()

        recent_visit = db.execute(
            select(
                VetVisit.visit_datetime.label("visit_datetime"),
                VetVisit.reason.label("reason"),
                VetVisit.notes_visible_to_owner.label("notes_visible_to_owner"),
                Organisation.name.label("clinic_name"),
            )
            .select_from(VetVisit)
            .join(Pet, Pet.pet_id == VetVisit.pet_id)
            .join(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
            .outerjoin(Organisation, Organisation.organisation_id == VetVisit.organisation_id)
            .where(OwnerPet.owner_id == owner_id)
            .order_by(desc(VetVisit.visit_datetime))
            .limit(1)
        ).mappings().first()

        pets_recent = db.execute(
            select(func.count(Pet.pet_id))
            .select_from(Pet)
            .join(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
            .where(OwnerPet.owner_id == owner_id, Pet.created_at >= datetime.now(UTC) - timedelta(days=90))
        ).scalar_one()

        d["new_pets_last_90d"] = int(pets_recent or 0)
        d["visits_last_12m"] = int(visit_count_year or 0)
        d["recent_visit_at"] = recent_visit["visit_datetime"] if recent_visit else None
        d["recent_visit_reason"] = recent_visit["reason"] if recent_visit else None
        d["recent_visit_notes"] = recent_visit["notes_visible_to_owner"] if recent_visit else None
        d["clinic_name"] = recent_visit["clinic_name"] if recent_visit else None
        out.append(d)
    return out


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/{owner_id}/pets", summary="List pets for owner")
def list_owner_pets(owner_id: str, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    rows = db.execute(
        select(
            Pet.pet_id.label("id"),
            Pet.name.label("name"),
            Pet.species.label("species"),
            Pet.breed.label("breed"),
            Pet.sex.label("sex"),
            Pet.microchip_number.label("microchip_number"),
            Pet.date_of_birth.label("date_of_birth"),
            Pet.created_at.label("created_at"),
        )
        .select_from(Pet)
        .join(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
        .where(OwnerPet.owner_id == oid)
        .order_by(desc(Pet.created_at))
    ).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        out.append(d)
    return out

