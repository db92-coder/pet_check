"""Module: owners."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db
from app.db.models.organisation import Organisation
from app.db.models.owner import Owner
from app.db.models.owner_pet import OwnerPet
from app.db.models.pet import Pet
from app.db.models.user import User
from app.db.models.vet_visit import VetVisit

router = APIRouter()


# Validate and coerce UUID inputs from query/path payloads.
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


def _ensure_owner_exists(db: Session, owner_id: uuid.UUID) -> None:
    # Fail early if caller references a non-existent owner id.
    exists = db.execute(select(Owner.owner_id).where(Owner.owner_id == owner_id)).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Owner not found")


def _ensure_owner_pet_link(db: Session, owner_id: uuid.UUID, pet_id: uuid.UUID) -> None:
    # Ensure notes/flags cannot be linked to pets that are outside this owner profile.
    linked = db.execute(
        select(OwnerPet.pet_id).where(
            OwnerPet.owner_id == owner_id,
            OwnerPet.pet_id == pet_id,
        )
    ).scalar_one_or_none()
    if not linked:
        raise HTTPException(status_code=400, detail="Pet is not linked to this owner")


class OwnerNoteCreate(BaseModel):
    pet_id: str | None = None
    author_user_id: str | None = None
    note_text: str = Field(min_length=3, max_length=4000)
    note_type: str = Field(default="GENERAL", min_length=2, max_length=60)


class ConcernCreate(BaseModel):
    pet_id: str | None = None
    raised_by_user_id: str | None = None
    severity: str = Field(default="MEDIUM", min_length=3, max_length=20)
    category: str = Field(default="WELFARE", min_length=3, max_length=60)
    description: str = Field(min_length=3, max_length=4000)


class ConcernUpdate(BaseModel):
    status: str = Field(default="OPEN", min_length=3, max_length=20)
    resolution_notes: str | None = None
    resolved_by_user_id: str | None = None


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

        recent_note = db.execute(
            text(
                """
                SELECT n.note_text
                FROM owner_notes n
                WHERE n.owner_id = :owner_id
                  AND n.deleted_at IS NULL
                ORDER BY n.created_at DESC
                LIMIT 1
                """
            ),
            {"owner_id": owner_id},
        ).scalar_one_or_none()

        open_concerns = db.execute(
            text(
                """
                SELECT COUNT(*)::int
                FROM concern_flags c
                WHERE c.owner_id = :owner_id
                  AND UPPER(COALESCE(c.status, 'OPEN')) = 'OPEN'
                """
            ),
            {"owner_id": owner_id},
        ).scalar_one()

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
        d["recent_clinical_note"] = recent_note
        d["open_concern_count"] = int(open_concerns or 0)
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


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/{owner_id}/notes", summary="List owner notes")
def list_owner_notes(owner_id: str, limit: int = 100, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    _ensure_owner_exists(db, oid)
    rows = db.execute(
        text(
            """
            SELECT
              n.note_id::text AS id,
              n.owner_id::text AS owner_id,
              n.pet_id::text AS pet_id,
              p.name AS pet_name,
              n.author_user_id::text AS author_user_id,
              u.full_name AS author_name,
              n.note_text AS note_text,
              n.note_type AS note_type,
              n.created_at AS created_at
            FROM owner_notes n
            LEFT JOIN pets p ON p.pet_id = n.pet_id
            LEFT JOIN users u ON u.user_id = n.author_user_id
            WHERE n.owner_id = :owner_id
              AND n.deleted_at IS NULL
            ORDER BY n.created_at DESC
            LIMIT :limit
            """
        ),
        {"owner_id": oid, "limit": limit},
    ).mappings().all()
    return [dict(r) for r in rows]


# Endpoint: handles HTTP request/response mapping for this route.
@router.post("/{owner_id}/notes", summary="Create owner note")
def create_owner_note(owner_id: str, payload: OwnerNoteCreate, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    _ensure_owner_exists(db, oid)
    pet_uuid = _parse_uuid(payload.pet_id, "pet_id") if payload.pet_id else None
    author_uuid = _parse_uuid(payload.author_user_id, "author_user_id") if payload.author_user_id else None

    if pet_uuid:
        _ensure_owner_pet_link(db, oid, pet_uuid)

    row = db.execute(
        text(
            """
            INSERT INTO owner_notes (
              note_id, owner_id, pet_id, author_user_id, note_text, note_type, created_at
            )
            VALUES (
              :note_id, :owner_id, :pet_id, :author_user_id, :note_text, :note_type, :created_at
            )
            RETURNING note_id::text AS id
            """
        ),
        {
            "note_id": uuid.uuid4(),
            "owner_id": oid,
            "pet_id": pet_uuid,
            "author_user_id": author_uuid,
            "note_text": payload.note_text.strip(),
            "note_type": payload.note_type.strip().upper(),
            "created_at": datetime.now(UTC),
        },
    ).mappings().one()
    db.commit()
    return {"id": row["id"]}


# Endpoint: handles HTTP request/response mapping for this route.
@router.delete("/{owner_id}/notes/{note_id}", summary="Delete owner note")
def delete_owner_note(owner_id: str, note_id: str, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    nid = _parse_uuid(note_id, "note_id")
    _ensure_owner_exists(db, oid)
    updated = db.execute(
        text(
            """
            UPDATE owner_notes
            SET deleted_at = :deleted_at
            WHERE owner_id = :owner_id
              AND note_id = :note_id
              AND deleted_at IS NULL
            """
        ),
        {"deleted_at": datetime.now(UTC), "owner_id": oid, "note_id": nid},
    )
    db.commit()
    if updated.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/{owner_id}/concerns", summary="List owner concern flags")
def list_owner_concerns(owner_id: str, status: str = "ALL", limit: int = 100, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    _ensure_owner_exists(db, oid)
    status_u = status.upper().strip()
    status_sql = ""
    params: dict[str, object] = {"owner_id": oid, "limit": limit}
    if status_u != "ALL":
        status_sql = "AND UPPER(COALESCE(c.status, 'OPEN')) = :status"
        params["status"] = status_u
    rows = db.execute(
        text(
            f"""
            SELECT
              c.flag_id::text AS id,
              c.owner_id::text AS owner_id,
              c.pet_id::text AS pet_id,
              p.name AS pet_name,
              c.raised_by_user_id::text AS raised_by_user_id,
              raised.full_name AS raised_by_name,
              c.severity AS severity,
              c.status AS status,
              c.category AS category,
              c.description AS description,
              c.created_at AS created_at,
              c.resolved_at AS resolved_at,
              c.resolution_notes AS resolution_notes,
              c.resolved_by_user_id::text AS resolved_by_user_id,
              resolved.full_name AS resolved_by_name
            FROM concern_flags c
            LEFT JOIN pets p ON p.pet_id = c.pet_id
            LEFT JOIN users raised ON raised.user_id = c.raised_by_user_id
            LEFT JOIN users resolved ON resolved.user_id = c.resolved_by_user_id
            WHERE c.owner_id = :owner_id
              {status_sql}
            ORDER BY c.created_at DESC
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


# Endpoint: handles HTTP request/response mapping for this route.
@router.post("/{owner_id}/concerns", summary="Create concern flag")
def create_owner_concern(owner_id: str, payload: ConcernCreate, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    _ensure_owner_exists(db, oid)
    pet_uuid = _parse_uuid(payload.pet_id, "pet_id") if payload.pet_id else None
    raised_uuid = _parse_uuid(payload.raised_by_user_id, "raised_by_user_id") if payload.raised_by_user_id else None
    if pet_uuid:
        _ensure_owner_pet_link(db, oid, pet_uuid)

    row = db.execute(
        text(
            """
            INSERT INTO concern_flags (
              flag_id, owner_id, pet_id, raised_by_user_id, severity, status, category, description, created_at
            )
            VALUES (
              :flag_id, :owner_id, :pet_id, :raised_by_user_id, :severity, 'OPEN', :category, :description, :created_at
            )
            RETURNING flag_id::text AS id
            """
        ),
        {
            "flag_id": uuid.uuid4(),
            "owner_id": oid,
            "pet_id": pet_uuid,
            "raised_by_user_id": raised_uuid,
            "severity": payload.severity.strip().upper(),
            "category": payload.category.strip().upper(),
            "description": payload.description.strip(),
            "created_at": datetime.now(UTC),
        },
    ).mappings().one()
    db.commit()
    return {"id": row["id"]}


# Endpoint: handles HTTP request/response mapping for this route.
@router.patch("/{owner_id}/concerns/{flag_id}", summary="Update concern flag")
def update_owner_concern(owner_id: str, flag_id: str, payload: ConcernUpdate, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    fid = _parse_uuid(flag_id, "flag_id")
    _ensure_owner_exists(db, oid)
    resolved_by_uuid = _parse_uuid(payload.resolved_by_user_id, "resolved_by_user_id") if payload.resolved_by_user_id else None
    status_u = payload.status.strip().upper()
    resolved_at = datetime.now(UTC) if status_u in {"RESOLVED", "CLOSED"} else None
    result = db.execute(
        text(
            """
            UPDATE concern_flags
            SET
              status = :status,
              resolution_notes = :resolution_notes,
              resolved_at = :resolved_at,
              resolved_by_user_id = :resolved_by_user_id
            WHERE owner_id = :owner_id
              AND flag_id = :flag_id
            """
        ),
        {
            "status": status_u,
            "resolution_notes": (payload.resolution_notes or "").strip() or None,
            "resolved_at": resolved_at,
            "resolved_by_user_id": resolved_by_uuid,
            "owner_id": oid,
            "flag_id": fid,
        },
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Concern flag not found")
    return {"ok": True}
