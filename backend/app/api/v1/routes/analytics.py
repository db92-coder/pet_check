from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db

router = APIRouter()

@router.get("/visits-by-month", summary="Visits by month (line chart)")
def visits_by_month(db: Session = Depends(get_db)):
    q = text("""
      SELECT
        to_char(date_trunc('month', v.visit_date), 'YYYY-MM') AS month,
        COUNT(*)::int AS visits
      FROM visits v
      WHERE v.visit_date IS NOT NULL
      GROUP BY 1
      ORDER BY 1;
    """)
    return list(db.execute(q).mappings().all())

@router.get("/suburbs", summary="Suburb ranking (table/bar)")
def suburb_ranking(db: Session = Depends(get_db)):
    q = text("""
      SELECT
        o.suburb AS suburb,
        COUNT(DISTINCT o.id)::int AS owners,
        COUNT(DISTINCT p.id)::int AS pets,
        COUNT(v.id)::int AS visits
      FROM owners o
      JOIN pets p ON p.owner_id = o.id
      LEFT JOIN visits v ON v.pet_id = p.id
      WHERE o.suburb IS NOT NULL AND o.suburb <> ''
      GROUP BY o.suburb
      ORDER BY visits DESC, pets DESC
      LIMIT 50;
    """)
    return list(db.execute(q).mappings().all())

@router.get("/vaccinations-by-type", summary="Vaccinations by type (pie chart)")
def vaccinations_by_type(db: Session = Depends(get_db)):
    q = text("""
      SELECT
        v.vaccine_type AS type,
        COUNT(*)::int AS count
      FROM vaccinations v
      WHERE v.vaccine_type IS NOT NULL AND v.vaccine_type <> ''
      GROUP BY v.vaccine_type
      ORDER BY count DESC;
    """)
    return list(db.execute(q).mappings().all())
