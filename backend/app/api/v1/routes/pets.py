from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db  # adjust if your deps path differs
from app.models import Pet, Owner, Clinic  # adjust to your model imports

router = APIRouter()

@router.get("", summary="List pets (grid-ready)")
def list_pets(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    stmt = (
        select(
            Pet.id.label("id"),
            Pet.name.label("name"),
            Pet.species.label("species"),
            Pet.breed.label("breed"),
            Owner.full_name.label("owner_name"),
            Owner.suburb.label("suburb"),
            Clinic.name.label("clinic_name"),
        )
        .join(Owner, Owner.id == Pet.owner_id)
        .join(Clinic, Clinic.id == Pet.clinic_id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(stmt).mappings().all())
