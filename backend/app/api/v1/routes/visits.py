"""Module: visits."""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, text, func
from app.api.v1.routes.deps import get_db
from app.db.models.vet_visit import VetVisit
from app.db.models.pet import Pet
from app.db.models.owner import Owner
from app.db.models.owner_pet import OwnerPet
from app.db.models.user import User
from app.db.models.organisation import Organisation


class VisitCreatePayload(BaseModel):
    pet_id: str
    organisation_id: str | None = None
    vet_user_id: str | None = None
    visit_datetime: datetime
    reason: str | None = None
    notes_visible_to_owner: str | None = None


class VisitCancelPayload(BaseModel):
    reason: str | None = None

router = APIRouter()


# Validate and coerce UUID inputs from query/path payloads.
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("", summary="List visits (simple)")
def list_visits(
    limit: int = 200,
    offset: int = 0,
    start_date: date | None = None,
    end_date: date | None = None,
    organisation_id: str | None = Query(default=None),
    include_cancelled: bool = True,
    db: Session = Depends(get_db),
):
    stmt = (
        select(
            VetVisit.visit_id.label("id"),
            VetVisit.pet_id.label("pet_id"),
            VetVisit.organisation_id.label("organisation_id"),
            VetVisit.vet_user_id.label("vet_user_id"),
            VetVisit.visit_datetime.label("visit_datetime"),
            VetVisit.reason.label("reason"),
            VetVisit.notes_visible_to_owner.label("notes_visible_to_owner"),
            Pet.name.label("pet_name"),
            Pet.species.label("pet_species"),
            Pet.breed.label("pet_breed"),
            Pet.sex.label("pet_sex"),
            Pet.microchip_number.label("pet_microchip_number"),
            Pet.date_of_birth.label("pet_date_of_birth"),
            User.email.label("owner_email"),
            User.full_name.label("owner_full_name"),
            Organisation.name.label("clinic_name"),
        )
        .select_from(VetVisit)
        .join(Pet, Pet.pet_id == VetVisit.pet_id)
        .outerjoin(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
        .outerjoin(Owner, Owner.owner_id == OwnerPet.owner_id)
        .outerjoin(User, User.user_id == Owner.user_id)
        .outerjoin(Organisation, Organisation.organisation_id == VetVisit.organisation_id)
        .order_by(desc(VetVisit.visit_datetime))
    )

    if start_date:
        stmt = stmt.where(VetVisit.visit_datetime >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        stmt = stmt.where(VetVisit.visit_datetime <= datetime.combine(end_date, datetime.max.time()))
    if organisation_id:
        oid = _parse_uuid(organisation_id, "organisation_id")
        stmt = stmt.where(VetVisit.organisation_id == oid)
    if not include_cancelled:
        stmt = stmt.where(~func.lower(func.coalesce(VetVisit.reason, "")).like("%cancel%"))

    rows = db.execute(stmt.offset(offset).limit(limit)).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        d["pet_id"] = str(d["pet_id"])
        if d.get("organisation_id"):
            d["organisation_id"] = str(d["organisation_id"])
        if d.get("vet_user_id"):
            d["vet_user_id"] = str(d["vet_user_id"])
        out.append(d)
    return out


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/calendar-summary", summary="Visit totals per day for month view")
def visits_calendar_summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    organisation_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # Parse YYYY-MM safely and compute month bounds in Python to stay DB-agnostic.
    try:
        month_start = datetime.strptime(f"{month}-01", "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format (expected YYYY-MM)")

    if month_start.month == 12:
        month_end = datetime(month_start.year + 1, 1, 1)
    else:
        month_end = datetime(month_start.year, month_start.month + 1, 1)

    stmt = select(VetVisit.visit_datetime, VetVisit.reason).where(
        VetVisit.visit_datetime >= month_start,
        VetVisit.visit_datetime < month_end,
    )
    if organisation_id:
        oid = _parse_uuid(organisation_id, "organisation_id")
        stmt = stmt.where(VetVisit.organisation_id == oid)

    rows = db.execute(stmt).all()

    # Aggregate per-day in Python for consistent behavior across Postgres/SQLite.
    day_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"total_visits": 0, "cancelled_or_missed": 0})
    for visit_datetime, reason in rows:
        if visit_datetime is None:
            continue
        day_key = visit_datetime.date().isoformat()
        day_counts[day_key]["total_visits"] += 1

        reason_text = (reason or "").lower()
        if ("cancel" in reason_text) or ("no show" in reason_text) or ("did not attend" in reason_text):
            day_counts[day_key]["cancelled_or_missed"] += 1

    out = []
    for day in sorted(day_counts.keys()):
        out.append(
            {
                "day": day,
                "total_visits": int(day_counts[day]["total_visits"]),
                "cancelled_or_missed": int(day_counts[day]["cancelled_or_missed"]),
            }
        )
    return out


# Endpoint: handles HTTP request/response mapping for this route.
@router.post("", summary="Create a visit")
def create_visit(payload: VisitCreatePayload, db: Session = Depends(get_db)):
    pet_id = _parse_uuid(payload.pet_id, "pet_id")
    pet = db.execute(select(Pet).where(Pet.pet_id == pet_id)).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    organisation_uuid = _parse_uuid(payload.organisation_id, "organisation_id") if payload.organisation_id else None
    vet_user_uuid = _parse_uuid(payload.vet_user_id, "vet_user_id") if payload.vet_user_id else None

    visit = VetVisit(
        pet_id=pet_id,
        organisation_id=organisation_uuid,
        vet_user_id=vet_user_uuid,
        visit_datetime=payload.visit_datetime,
        reason=(payload.reason or "General check").strip(),
        notes_visible_to_owner=(payload.notes_visible_to_owner or "").strip() or None,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)

    return {
        "id": str(visit.visit_id),
        "pet_id": str(visit.pet_id),
        "organisation_id": str(visit.organisation_id) if visit.organisation_id else None,
        "vet_user_id": str(visit.vet_user_id) if visit.vet_user_id else None,
        "visit_datetime": visit.visit_datetime,
        "reason": visit.reason,
        "notes_visible_to_owner": visit.notes_visible_to_owner,
    }


# Endpoint: handles HTTP request/response mapping for this route.
@router.patch("/{visit_id}/cancel", summary="Cancel a visit")
def cancel_visit(visit_id: str, payload: VisitCancelPayload, db: Session = Depends(get_db)):
    vid = _parse_uuid(visit_id, "visit_id")
    visit = db.execute(select(VetVisit).where(VetVisit.visit_id == vid)).scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    reason_suffix = (payload.reason or "Cancelled by clinic").strip()
    visit.reason = f"Cancelled: {reason_suffix}"
    db.commit()
    db.refresh(visit)

    return {
        "id": str(visit.visit_id),
        "reason": visit.reason,
    }

