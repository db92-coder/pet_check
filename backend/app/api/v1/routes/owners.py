from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db
from app.models import Owner

router = APIRouter()

@router.get("", summary="List owners (grid-ready)")
def list_owners(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    stmt = (
        select(
            Owner.id.label("id"),
            Owner.full_name.label("full_name"),
            Owner.suburb.label("suburb"),
            Owner.phone.label("phone"),
            Owner.email.label("email"),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(stmt).mappings().all())
