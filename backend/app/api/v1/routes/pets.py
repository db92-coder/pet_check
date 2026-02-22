"""Module: pets."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db
from app.db.models.owner import Owner
from app.db.models.owner_pet import OwnerPet
from app.db.models.pet import Pet
from app.db.models.user import User
from app.db.models.vaccination import Vaccination
from app.db.models.weight import Weight
from app.db.models.medication import Medication
from app.db.models.vet_visit import VetVisit
from app.db.models.organisation import Organisation

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class WeightCreatePayload(BaseModel):
    weight_kg: float
    measured_at: datetime | None = None


# -------------------------
# Helpers
# -------------------------
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


async def _read_image_file(photo: UploadFile | None) -> tuple[bytes | None, str | None]:
    if not photo:
        return None, None

    content_type = (photo.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Photo must be JPEG or PNG")

    data = await photo.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Photo must be 5MB or smaller")

    return data, content_type


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
    latest_clinic_id_sq = (
        select(VetVisit.organisation_id)
        .where(
            VetVisit.pet_id == Pet.pet_id,
            VetVisit.organisation_id.is_not(None),
        )
        .order_by(desc(VetVisit.visit_datetime))
        .limit(1)
        .scalar_subquery()
    )
    latest_clinic_name_sq = (
        select(Organisation.name)
        .join(VetVisit, VetVisit.organisation_id == Organisation.organisation_id)
        .where(
            VetVisit.pet_id == Pet.pet_id,
            VetVisit.organisation_id.is_not(None),
        )
        .order_by(desc(VetVisit.visit_datetime))
        .limit(1)
        .scalar_subquery()
    )

    stmt = (
        select(
            Pet.pet_id.label("id"),
            Pet.name.label("name"),
            Pet.species.label("species"),
            Pet.breed.label("breed"),
            Pet.sex.label("sex"),
            Pet.microchip_number.label("microchip_number"),
            Pet.photo_url.label("photo_url"),
            Pet.photo_mime_type.label("photo_mime_type"),
            Pet.date_of_birth.label("date_of_birth"),
            Pet.created_at.label("created_at"),

            Owner.owner_id.label("owner_id"),
            Owner.verified_identity_level.label("verified_identity_level"),

            User.user_id.label("user_id"),
            User.email.label("owner_email"),
            User.full_name.label("owner_full_name"),
            User.phone.label("owner_phone"),
            latest_clinic_id_sq.label("clinic_id"),
            latest_clinic_name_sq.label("clinic_name"),
        )
        .select_from(Pet)
        .outerjoin(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
        .outerjoin(Owner, Owner.owner_id == OwnerPet.owner_id)
        .outerjoin(User, User.user_id == Owner.user_id)
    )

    if user_id:
        uid = _parse_uuid(user_id, "user_id")
        stmt = stmt.where(User.user_id == uid)

    if owner_id:
        oid = _parse_uuid(owner_id, "owner_id")
        stmt = stmt.where(Owner.owner_id == oid)

    stmt = stmt.offset(offset).limit(limit)

    rows = db.execute(stmt).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        if d.get("id"):
            d["id"] = str(d["id"])
        if d.get("owner_id"):
            d["owner_id"] = str(d["owner_id"])
        if d.get("user_id"):
            d["user_id"] = str(d["user_id"])
        if d.get("clinic_id"):
            d["clinic_id"] = str(d["clinic_id"])

        d["has_photo"] = bool(d.get("photo_mime_type"))
        out.append(d)

    return out


@router.post("", summary="Create pet for an owner user")
async def create_pet(
    user_id: str = Form(...),
    name: str = Form(...),
    species: str = Form(...),
    breed: str | None = Form(default=None),
    sex: str | None = Form(default=None),
    microchip_number: str | None = Form(default=None),
    date_of_birth: date | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    uid = _parse_uuid(user_id, "user_id")

    owner = db.execute(select(Owner).where(Owner.user_id == uid)).scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner profile not found for user")

    photo_data, photo_mime_type = await _read_image_file(photo)

    pet = Pet(
        name=name.strip(),
        species=species.strip(),
        breed=_normalize_optional(breed),
        sex=_normalize_optional(sex),
        microchip_number=_normalize_optional(microchip_number),
        date_of_birth=date_of_birth,
        photo_data=photo_data,
        photo_mime_type=photo_mime_type,
        photo_url=None,
    )
    db.add(pet)
    db.flush()

    db.add(
        OwnerPet(
            owner_id=owner.owner_id,
            pet_id=pet.pet_id,
            start_date=date.today(),
            end_date=None,
            relationship_type="primary_owner",
        )
    )

    db.commit()
    db.refresh(pet)

    return {
        "id": str(pet.pet_id),
        "owner_id": str(owner.owner_id),
        "user_id": str(uid),
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "sex": pet.sex,
        "microchip_number": pet.microchip_number,
        "date_of_birth": pet.date_of_birth,
        "has_photo": bool(pet.photo_mime_type),
    }


@router.put("/{pet_id}", summary="Update pet details")
async def update_pet(
    pet_id: str,
    name: str = Form(...),
    species: str = Form(...),
    breed: str | None = Form(default=None),
    sex: str | None = Form(default=None),
    microchip_number: str | None = Form(default=None),
    date_of_birth: date | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id, "pet_id")

    pet = db.execute(select(Pet).where(Pet.pet_id == pid)).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    pet.name = name.strip()
    pet.species = species.strip()
    pet.breed = _normalize_optional(breed)
    pet.sex = _normalize_optional(sex)
    pet.microchip_number = _normalize_optional(microchip_number)
    pet.date_of_birth = date_of_birth

    if photo:
        photo_data, photo_mime_type = await _read_image_file(photo)
        pet.photo_data = photo_data
        pet.photo_mime_type = photo_mime_type
        pet.photo_url = None

    db.commit()
    db.refresh(pet)

    return {
        "id": str(pet.pet_id),
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "sex": pet.sex,
        "microchip_number": pet.microchip_number,
        "date_of_birth": pet.date_of_birth,
        "has_photo": bool(pet.photo_mime_type),
    }


@router.get("/{pet_id}/photo", summary="Get pet photo")
def get_pet_photo(
    pet_id: str,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id, "pet_id")
    pet = db.execute(select(Pet).where(Pet.pet_id == pid)).scalar_one_or_none()
    if not pet or not pet.photo_data:
        raise HTTPException(status_code=404, detail="Pet photo not found")

    return Response(content=pet.photo_data, media_type=pet.photo_mime_type or "image/jpeg")


@router.get("/{pet_id}", summary="Get pet detail")
def get_pet(
    pet_id: str,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id, "pet_id")

    stmt = select(Pet).where(Pet.pet_id == pid)
    pet = db.execute(stmt).scalars().first()

    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    return {
        "id": str(pet.pet_id),
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "sex": pet.sex,
        "microchip_number": pet.microchip_number,
        "photo_url": pet.photo_url,
        "has_photo": bool(pet.photo_mime_type),
        "date_of_birth": pet.date_of_birth,
        "created_at": pet.created_at,
    }


@router.get("/{pet_id}/weights", summary="List weights for a pet")
def list_pet_weights(
    pet_id: str,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id, "pet_id")

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


@router.post("/{pet_id}/weights", summary="Add weight for a pet")
def create_pet_weight(
    pet_id: str,
    payload: WeightCreatePayload,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id, "pet_id")
    pet = db.execute(select(Pet).where(Pet.pet_id == pid)).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    measured_at = payload.measured_at or datetime.utcnow()
    weight = Weight(
        pet_id=pid,
        visit_id=None,
        measured_at=measured_at,
        weight_kg=payload.weight_kg,
        measured_by=None,
    )
    db.add(weight)
    db.commit()
    db.refresh(weight)

    return {
        "id": str(weight.weight_id),
        "pet_id": str(weight.pet_id),
        "weight_kg": float(weight.weight_kg),
        "measured_at": weight.measured_at,
        "measured_by": None,
    }


@router.get("/{pet_id}/vaccinations", summary="List vaccinations for a pet")
def list_pet_vaccinations(
    pet_id: str,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id, "pet_id")

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


@router.get("/{pet_id}/medications", summary="List medications for a pet")
def list_pet_medications(
    pet_id: str,
    db: Session = Depends(get_db),
):
    pid = _parse_uuid(pet_id, "pet_id")
    rows = db.execute(
        select(
            Medication.medication_id.label("id"),
            Medication.pet_id.label("pet_id"),
            Medication.name.label("name"),
            Medication.dosage.label("dosage"),
            Medication.instructions.label("instructions"),
            Medication.start_date.label("start_date"),
            Medication.end_date.label("end_date"),
        )
        .where(Medication.pet_id == pid)
        .order_by(desc(Medication.start_date))
    ).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"]) if isinstance(d.get("id"), uuid.UUID) else d.get("id")
        d["pet_id"] = str(d["pet_id"]) if isinstance(d.get("pet_id"), uuid.UUID) else d.get("pet_id")
        out.append(d)
    return out

