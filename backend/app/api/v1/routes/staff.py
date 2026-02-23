"""Module: staff."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db
from app.db.models.organisation import Organisation
from app.db.models.organisation_member import OrganisationMember
from app.db.models.staff_leave import StaffLeave
from app.db.models.user import User

router = APIRouter()


class LeaveRequestCreate(BaseModel):
    user_id: str
    organisation_id: str
    start_date: date
    end_date: date
    reason: str | None = None


# Validate and coerce UUID inputs from query/path payloads.
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("", summary="Staff dashboard payload by clinic context")
def staff_dashboard(
    user_id: str,
    organisation_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    uid = _parse_uuid(user_id, "user_id")
    user = db.execute(select(User).where(User.user_id == uid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    is_admin = (user.role or "").upper() == "ADMIN"

    member_clinic_ids = [
        row.organisation_id
        for row in db.execute(
            select(OrganisationMember.organisation_id).where(OrganisationMember.user_id == uid)
        ).scalars().all()
    ]
    if is_admin:
        allowed_clinic_ids = db.execute(
            select(Organisation.organisation_id).where(Organisation.org_type == "vet_clinic")
        ).scalars().all()
    else:
        allowed_clinic_ids = member_clinic_ids

    clinic_ids = list(allowed_clinic_ids)

    if organisation_id:
        req_cid = _parse_uuid(organisation_id, "organisation_id")
        if (not is_admin) and req_cid not in member_clinic_ids:
            raise HTTPException(status_code=403, detail="User is not a member of requested clinic")
        if is_admin and req_cid not in allowed_clinic_ids:
            raise HTTPException(status_code=404, detail="Requested clinic not found")
        clinic_ids = [req_cid]

    if not clinic_ids:
        return {"clinics": [], "staff": [], "leave_now": [], "leave_upcoming": [], "policies": []}

    staff_rows = db.execute(
        select(
            OrganisationMember.organisation_id.label("organisation_id"),
            OrganisationMember.member_role.label("member_role"),
            User.user_id.label("user_id"),
            User.full_name.label("full_name"),
            User.email.label("email"),
            User.phone.label("phone"),
        )
        .select_from(OrganisationMember)
        .join(User, User.user_id == OrganisationMember.user_id)
        .where(OrganisationMember.organisation_id.in_(clinic_ids))
    ).mappings().all()

    today = date.today()
    leave_now_rows = db.execute(
        select(StaffLeave).where(
            StaffLeave.organisation_id.in_(clinic_ids),
            StaffLeave.status == "APPROVED",
            StaffLeave.start_date <= today,
            StaffLeave.end_date >= today,
        )
    ).scalars().all()

    leave_upcoming_rows = db.execute(
        select(StaffLeave).where(
            StaffLeave.organisation_id.in_(clinic_ids),
            or_(
                StaffLeave.status == "PENDING",
                and_(
                    StaffLeave.status == "APPROVED",
                    StaffLeave.start_date > today,
                ),
            ),
        )
    ).scalars().all()

    user_lookup = {
        u.user_id: u
        for u in db.execute(
            select(User).where(User.user_id.in_([row.user_id for row in leave_now_rows + leave_upcoming_rows]))
        ).scalars().all()
    }

    clinic_ids_out = list(allowed_clinic_ids)
    clinic_lookup = {
        c.organisation_id: c
        for c in db.execute(select(Organisation).where(Organisation.organisation_id.in_(clinic_ids_out))).scalars().all()
    }
    clinics = [
        {
            "id": str(cid),
            "name": clinic_lookup.get(cid).name if clinic_lookup.get(cid) else str(cid),
        }
        for cid in clinic_ids_out
    ]
    policies = [
        {"id": "onboarding", "title": "Onboarding Handbook", "category": "Onboarding"},
        {"id": "leave-policy", "title": "Leave and Entitlements Policy", "category": "HR"},
        {"id": "clinical-protocols", "title": "Clinical Safety Protocols", "category": "Clinical"},
        {"id": "incident-form", "title": "Incident Report Form", "category": "Forms"},
        {"id": "med-order-form", "title": "Medication Order Request Form", "category": "Forms"},
    ]

    staff = []
    for row in staff_rows:
        d = dict(row)
        d["organisation_id"] = str(d["organisation_id"])
        d["user_id"] = str(d["user_id"])
        staff.append(d)

    def leave_to_dict(leave: StaffLeave):
        u = user_lookup.get(leave.user_id)
        return {
            "leave_id": str(leave.leave_id),
            "organisation_id": str(leave.organisation_id),
            "user_id": str(leave.user_id),
            "staff_name": u.full_name if u else None,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "reason": leave.reason,
            "status": leave.status,
        }

    return {
        "clinics": clinics,
        "staff": staff,
        "leave_now": [leave_to_dict(l) for l in leave_now_rows],
        "leave_upcoming": [leave_to_dict(l) for l in leave_upcoming_rows],
        "policies": policies,
    }


# Endpoint: handles HTTP request/response mapping for this route.
@router.post("/leave", summary="Apply for leave")
def apply_leave(payload: LeaveRequestCreate, db: Session = Depends(get_db)):
    uid = _parse_uuid(payload.user_id, "user_id")
    cid = _parse_uuid(payload.organisation_id, "organisation_id")

    member = db.execute(
        select(OrganisationMember).where(
            OrganisationMember.user_id == uid,
            OrganisationMember.organisation_id == cid,
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="User is not a member of clinic")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    leave = StaffLeave(
        organisation_id=cid,
        user_id=uid,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=(payload.reason or "").strip() or None,
        status="PENDING",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)

    return {
        "leave_id": str(leave.leave_id),
        "organisation_id": str(leave.organisation_id),
        "user_id": str(leave.user_id),
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "reason": leave.reason,
        "status": leave.status,
    }

