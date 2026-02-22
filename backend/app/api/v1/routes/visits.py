from datetime import date, datetime
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


def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


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


@router.get("/calendar-summary", summary="Visit totals per day for month view")
def visits_calendar_summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    organisation_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    params = {"month": month, "org": organisation_id}
    q = text(
        """
      SELECT
        to_char(date_trunc('day', vv.visit_datetime), 'YYYY-MM-DD') AS day,
        COUNT(*)::int AS total_visits,
        SUM(
          CASE
            WHEN LOWER(COALESCE(vv.reason, '')) LIKE '%cancel%'
              OR LOWER(COALESCE(vv.reason, '')) LIKE '%no show%'
              OR LOWER(COALESCE(vv.reason, '')) LIKE '%did not attend%'
            THEN 1 ELSE 0
          END
        )::int AS cancelled_or_missed
      FROM vet_visits vv
      WHERE to_char(date_trunc('month', vv.visit_datetime), 'YYYY-MM') = :month
        AND (:org IS NULL OR vv.organisation_id::text = :org)
      GROUP BY 1
      ORDER BY 1
    """
    )
    return list(db.execute(q, params).mappings().all())


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
