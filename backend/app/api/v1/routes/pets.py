from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.api.v1.routes.deps import get_db

from app.db.models.pet import Pet
from app.db.models.weight import Weight
from app.db.models.vaccination import Vaccination
from sqlalchemy import select, outerjoin
from app.db.models.owner_pet import OwnerPet
from app.db.models.owner import Owner
from app.db.models.user import User

router = APIRouter()


# -------------------------
# Helpers
# -------------------------
def _parse_uuid(pet_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(pet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid pet_id (must be UUID)")


# -------------------------
# Endpoints
# -------------------------

@router.get("", summary="List pets (with owner info)")
def list_pets(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    stmt = (
        select(
            Pet.pet_id.label("id"),
            Pet.name.label("name"),
            Pet.species.label("species"),
            Pet.breed.label("breed"),
            Pet.sex.label("sex"),
            Pet.date_of_birth.label("date_of_birth"),
            Pet.created_at.label("created_at"),

            Owner.owner_id.label("owner_id"),
            Owner.verified_identity_level.label("verified_identity_level"),

            User.user_id.label("user_id"),
            User.email.label("owner_email"),
            # if your User has these fields, keep them; otherwise remove:
            getattr(User, "first_name", None).label("owner_first_name") if hasattr(User, "first_name") else None,
            getattr(User, "last_name", None).label("owner_last_name") if hasattr(User, "last_name") else None,
        )
        .select_from(Pet)
        .outerjoin(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
        .outerjoin(Owner, Owner.owner_id == OwnerPet.owner_id)
        .outerjoin(User, User.user_id == Owner.user_id)
        .offset(offset)
        .limit(limit)
    )

    rows = db.execute(stmt).mappings().all()

    out = []
    for r in rows:
        d = dict(r)

        # UUIDs -> strings for frontend
        if d.get("id"): d["id"] = str(d["id"])
        if d.get("owner_id"): d["owner_id"] = str(d["owner_id"])
        if d.get("user_id"): d["user_id"] = str(d["user_id"])

        # Remove keys where we dynamically inserted None columns
        d = {k: v for k, v in d.items() if k is not None}
        out.append(d)

    return out



@router.get("/{pet_id}", summary="Get pet detail")
def get_pet(
    pet_id: str,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id)

    stmt = select(Pet).where(Pet.pet_id == pid)
    pet = db.execute(stmt).scalars().first()

    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    # return a JSON-friendly dict (avoid ORM serialization issues)
    return {
        "id": str(pet.pet_id),
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "sex": pet.sex,
        "date_of_birth": pet.date_of_birth,
        "created_at": pet.created_at,
    }


@router.get("/{pet_id}/weights", summary="List weights for a pet")
def list_pet_weights(
    pet_id: str,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id)

    # Adjust column names if your Weight model differs
    stmt = (
        select(
            Weight.weight_id.label("id") if hasattr(Weight, "weight_id") else Weight.id.label("id"),
            Weight.pet_id.label("pet_id"),
            # common possibilities:
            getattr(Weight, "weight_kg", None).label("weight_kg") if hasattr(Weight, "weight_kg") else getattr(Weight, "weight", None).label("weight"),
            getattr(Weight, "measured_on", None).label("measured_on") if hasattr(Weight, "measured_on") else getattr(Weight, "recorded_at", None).label("recorded_at"),
            getattr(Weight, "created_at", None).label("created_at") if hasattr(Weight, "created_at") else None,
        )
        .where(Weight.pet_id == pid)
        .order_by(desc(getattr(Weight, "measured_on", getattr(Weight, "recorded_at", Weight.pet_id))))
        .limit(limit)
    )

    rows = db.execute(stmt).mappings().all()

    # Clean up any None keys from the dynamic selection above
    cleaned = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"]) if isinstance(d.get("id"), uuid.UUID) else d.get("id")
        d["pet_id"] = str(d["pet_id"]) if isinstance(d.get("pet_id"), uuid.UUID) else d.get("pet_id")
        cleaned.append({k: v for k, v in d.items() if k is not None})
    return cleaned


@router.get("/{pet_id}/vaccinations", summary="List vaccinations for a pet")
def list_pet_vaccinations(
    pet_id: str,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id)

    # Adjust column names if your Vaccination model differs
    stmt = (
        select(
            Vaccination.vaccination_id.label("id") if hasattr(Vaccination, "vaccination_id") else Vaccination.id.label("id"),
            Vaccination.pet_id.label("pet_id"),
            getattr(Vaccination, "vaccine_type", None).label("vaccine_type") if hasattr(Vaccination, "vaccine_type") else getattr(Vaccination, "type", None).label("type"),
            getattr(Vaccination, "administered_on", None).label("administered_on") if hasattr(Vaccination, "administered_on") else getattr(Vaccination, "date", None).label("date"),
            getattr(Vaccination, "created_at", None).label("created_at") if hasattr(Vaccination, "created_at") else None,
        )
        .where(Vaccination.pet_id == pid)
        .order_by(desc(getattr(Vaccination, "administered_on", getattr(Vaccination, "date", Vaccination.pet_id))))
        .limit(limit)
    )

    rows = db.execute(stmt).mappings().all()

    cleaned = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"]) if isinstance(d.get("id"), uuid.UUID) else d.get("id")
        d["pet_id"] = str(d["pet_id"]) if isinstance(d.get("pet_id"), uuid.UUID) else d.get("pet_id")
        cleaned.append({k: v for k, v in d.items() if k is not None})
    return cleaned
