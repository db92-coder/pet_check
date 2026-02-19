from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.api.v1.routes.deps import get_db
from app.db.models.vet_visit import VetVisit

router = APIRouter()

@router.get("", summary="List visits (simple)")
def list_visits(limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            VetVisit.visit_id.label("id"),
            VetVisit.pet_id.label("pet_id"),
            VetVisit.visit_datetime.label("visit_datetime"),
            VetVisit.reason.label("reason"),
        )
        .order_by(desc(VetVisit.visit_datetime))
        .offset(offset)
        .limit(limit)
    ).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        d["pet_id"] = str(d["pet_id"])
        out.append(d)
    return out
