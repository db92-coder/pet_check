"""Module: clinics."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db
from app.db.models.organisation import Organisation
from app.db.models.organisation_member import OrganisationMember
from app.db.models.vet_visit import VetVisit

router = APIRouter()


def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


@router.get("", summary="List clinics with capacity/cancellation insights")
def list_clinics(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db)):
    clinics = db.execute(
        select(Organisation).where(Organisation.org_type == "vet_clinic").limit(limit)
    ).scalars().all()

    out = []
    for clinic in clinics:
        cid = clinic.organisation_id
        staff_count = db.execute(
            select(func.count(OrganisationMember.user_id)).where(OrganisationMember.organisation_id == cid)
        ).scalar_one()
        # Use Python-safe datetime boundary for cross-dialect compatibility.
        from datetime import datetime, timedelta, UTC
        dt_30 = datetime.now(UTC) - timedelta(days=30)
        visits_30d = db.execute(
            select(func.count(VetVisit.visit_id)).where(
                VetVisit.organisation_id == cid,
                VetVisit.visit_datetime >= dt_30,
            )
        ).scalar_one()

        cancellations_30d = db.execute(
            select(func.count(VetVisit.visit_id)).where(
                VetVisit.organisation_id == cid,
                VetVisit.visit_datetime >= dt_30,
                func.lower(func.coalesce(VetVisit.reason, "")).like("%cancel%"),
            )
        ).scalar_one()

        upcoming_7d = db.execute(
            select(func.count(VetVisit.visit_id)).where(
                VetVisit.organisation_id == cid,
                VetVisit.visit_datetime >= datetime.now(UTC),
                VetVisit.visit_datetime <= datetime.now(UTC) + timedelta(days=7),
            )
        ).scalar_one()

        out.append(
            {
                "id": str(cid),
                "name": clinic.name,
                "phone": clinic.phone,
                "email": clinic.email,
                "address": clinic.address,
                "suburb": clinic.suburb,
                "state": clinic.state,
                "postcode": clinic.postcode,
                "latitude": clinic.latitude,
                "longitude": clinic.longitude,
                "staff_count": int(staff_count or 0),
                "visits_last_30d": int(visits_30d or 0),
                "cancellations_last_30d": int(cancellations_30d or 0),
                "upcoming_visits_next_7d": int(upcoming_7d or 0),
            }
        )

    return out


@router.get("/{clinic_id}/staff", summary="List staff for a clinic")
def clinic_staff(clinic_id: str, db: Session = Depends(get_db)):
    cid = _parse_uuid(clinic_id, "clinic_id")
    from app.db.models.user import User

    rows = db.execute(
        select(
            User.user_id.label("user_id"),
            User.full_name.label("full_name"),
            User.email.label("email"),
            User.phone.label("phone"),
            User.role.label("role"),
            OrganisationMember.member_role.label("member_role"),
        )
        .select_from(OrganisationMember)
        .join(User, User.user_id == OrganisationMember.user_id)
        .where(OrganisationMember.organisation_id == cid)
    ).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["user_id"] = str(d["user_id"])
        out.append(d)
    return out

