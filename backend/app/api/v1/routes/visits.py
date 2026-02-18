from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.api.deps import get_db
from app.models import Visit, Pet, Owner, Clinic  # adjust

router = APIRouter()

@router.get("", summary="List visits (grid-ready)")
def list_visits(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    stmt = (
        select(
            Visit.id.label("id"),
            Visit.visit_date.label("visit_date"),
            Pet.name.label("pet_name"),
            Owner.full_name.label("owner_name"),
            Owner.suburb.label("suburb"),
            Clinic.name.label("clinic_name"),
            Visit.reason.label("reason"),
        )
        .join(Pet, Pet.id == Visit.pet_id)
        .join(Owner, Owner.id == Pet.owner_id)
        .join(Clinic, Clinic.id == Visit.clinic_id)
        .order_by(desc(Visit.visit_date))
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(stmt).mappings().all())
