from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.v1.routes.deps import get_db
from app.db.models.owner import Owner

router = APIRouter()

@router.get("", summary="List owners (simple)")
def list_owners(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Owner.owner_id.label("id"),
            Owner.user_id.label("user_id"),
            Owner.verified_identity_level.label("verified_identity_level"),
        )
        .offset(offset)
        .limit(limit)
    ).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        d["user_id"] = str(d["user_id"])
        out.append(d)
    return out
