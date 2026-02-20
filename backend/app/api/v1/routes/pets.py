from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.api.v1.routes.deps import get_db

from app.db.models.pet import Pet
from app.db.models.weight import Weight
from app.db.models.vaccination import Vaccination
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
def list_pets(
    limit: int = 200,
    offset: int = 0,
    user_id: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
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
            User.full_name.label("owner_full_name"),
            User.phone.label("owner_phone"),
        )
        .select_from(Pet)
        .outerjoin(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
        .outerjoin(Owner, Owner.owner_id == OwnerPet.owner_id)
        .outerjoin(User, User.user_id == Owner.user_id)
    )

    if user_id:
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id (must be UUID)")
        stmt = stmt.where(User.user_id == uid)

    if owner_id:
        try:
            oid = uuid.UUID(owner_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid owner_id (must be UUID)")
        stmt = stmt.where(Owner.owner_id == oid)

    stmt = stmt.offset(offset).limit(limit)

    rows = db.execute(stmt).mappings().all()

    out = []
    for r in rows:
        d = dict(r)

        # UUIDs -> strings for frontend
        if d.get("id"): d["id"] = str(d["id"])
        if d.get("owner_id"): d["owner_id"] = str(d["owner_id"])
        if d.get("user_id"): d["user_id"] = str(d["user_id"])

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

    stmt = (
        select(
            Weight.weight_id.label("id"),
            Weight.pet_id.label("pet_id"),
            Weight.weight_kg.label("weight_kg"),
            Weight.measured_at.label("measured_at"),
            Weight.measured_by.label("measured_by"),
        )
        .where(Weight.pet_id == pid)
        .order_by(desc(Weight.measured_at))
        .limit(limit)
    )

    rows = db.execute(stmt).mappings().all()

    cleaned = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"]) if isinstance(d.get("id"), uuid.UUID) else d.get("id")
        d["pet_id"] = str(d["pet_id"]) if isinstance(d.get("pet_id"), uuid.UUID) else d.get("pet_id")
        d["measured_by"] = str(d["measured_by"]) if isinstance(d.get("measured_by"), uuid.UUID) else d.get("measured_by")
        cleaned.append(d)
    return cleaned


@router.get("/{pet_id}/vaccinations", summary="List vaccinations for a pet")
def list_pet_vaccinations(
    pet_id: str,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id)

    stmt = (
        select(
            Vaccination.vaccination_id.label("id"),
            Vaccination.pet_id.label("pet_id"),
            Vaccination.visit_id.label("visit_id"),
            Vaccination.vaccine_type.label("vaccine_type"),
            Vaccination.batch_number.label("batch_number"),
            Vaccination.administered_at.label("administered_at"),
            Vaccination.due_at.label("due_at"),
        )
        .where(Vaccination.pet_id == pid)
        .order_by(desc(Vaccination.administered_at))
        .limit(limit)
    )

    rows = db.execute(stmt).mappings().all()

    cleaned = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"]) if isinstance(d.get("id"), uuid.UUID) else d.get("id")
        d["pet_id"] = str(d["pet_id"]) if isinstance(d.get("pet_id"), uuid.UUID) else d.get("pet_id")
        d["visit_id"] = str(d["visit_id"]) if isinstance(d.get("visit_id"), uuid.UUID) else d.get("visit_id")
        cleaned.append(d)
    return cleaned
