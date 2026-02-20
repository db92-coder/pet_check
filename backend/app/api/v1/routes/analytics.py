from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db

router = APIRouter()


@router.get("/kpis")
def kpis(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    db: Session = Depends(get_db),
):
    # Optional filters (pets/owners/organisations remain total counts).
    params = {"start": start, "end": end, "org": organisation_id}

    visit_where = []
    if start:
        visit_where.append("vv.visit_datetime::date >= :start")
    if end:
        visit_where.append("vv.visit_datetime::date <= :end")
    if organisation_id:
        visit_where.append("vv.organisation_id::text = :org")
    visit_where_sql = ("WHERE " + " AND ".join(visit_where)) if visit_where else ""

    vax_where = []
    if start:
        vax_where.append("v.administered_at::date >= :start")
    if end:
        vax_where.append("v.administered_at::date <= :end")
    if organisation_id:
        vax_where.append(
            """
            EXISTS (
              SELECT 1
              FROM vet_visits vv
              WHERE vv.visit_id = v.visit_id
                AND vv.organisation_id::text = :org
            )
            """
        )
    vax_where_sql = ("WHERE " + " AND ".join(vax_where)) if vax_where else ""

    w_where = []
    if start:
        w_where.append("w.measured_at::date >= :start")
    if end:
        w_where.append("w.measured_at::date <= :end")
    if organisation_id:
        w_where.append(
            """
            EXISTS (
              SELECT 1
              FROM vet_visits vv
              WHERE vv.visit_id = w.visit_id
                AND vv.organisation_id::text = :org
            )
            """
        )
    w_where_sql = ("WHERE " + " AND ".join(w_where)) if w_where else ""

    q = text(
        f"""
      SELECT
        (SELECT COUNT(*)::int FROM pets)                        AS pets,
        (SELECT COUNT(*)::int FROM owners)                      AS owners,
        (SELECT COUNT(*)::int FROM organisations)               AS organisations,
        (SELECT COUNT(*)::int FROM vet_visits vv {visit_where_sql}) AS visits,
        (SELECT COUNT(*)::int FROM vaccinations v {vax_where_sql})  AS vaccinations,
        (SELECT COUNT(*)::int FROM weights w {w_where_sql})         AS weights
    """
    )
    return db.execute(q, params).mappings().one()


@router.get("/care-events-by-month")
def care_events_by_month(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    db: Session = Depends(get_db),
):
    params = {"start": start, "end": end, "org": organisation_id}

    # We treat visits + vaccinations + weights as care events.
    q = text(
        """
      WITH events AS (
        SELECT vv.visit_datetime AS dt, 'visit'::text AS kind
        FROM vet_visits vv
        WHERE (CAST(:start AS date) IS NULL OR visit_datetime::date >= CAST(:start AS date))
          AND (CAST(:end   AS date) IS NULL OR visit_datetime::date <= CAST(:end   AS date))
          AND (CAST(:org   AS text) IS NULL OR organisation_id::text = CAST(:org AS text))

        UNION ALL

        SELECT v.administered_at AS dt, 'vaccination'::text AS kind
        FROM vaccinations v
        WHERE (:start IS NULL OR v.administered_at::date >= :start)
          AND (:end   IS NULL OR v.administered_at::date <= :end)
          AND (CAST(:org AS text) IS NULL OR EXISTS (
                SELECT 1
                FROM vet_visits vv
                WHERE vv.visit_id = v.visit_id
                  AND vv.organisation_id::text = CAST(:org AS text)
              ))

        UNION ALL

        SELECT w.measured_at AS dt, 'weight'::text AS kind
        FROM weights w
        WHERE (CAST(:start AS date) IS NULL OR w.measured_at::date >= CAST(:start AS date))
          AND (:end   IS NULL OR w.measured_at::date <= :end)
          AND (CAST(:org AS text) IS NULL OR EXISTS (
                SELECT 1
                FROM vet_visits vv
                WHERE vv.visit_id = w.visit_id
                  AND vv.organisation_id::text = CAST(:org AS text)
              ))
      )
      SELECT
        to_char(date_trunc('month', dt), 'YYYY-MM') AS month,
        COUNT(*)::int AS total,
        SUM(CASE WHEN kind='visit' THEN 1 ELSE 0 END)::int AS visits,
        SUM(CASE WHEN kind='vaccination' THEN 1 ELSE 0 END)::int AS vaccinations,
        SUM(CASE WHEN kind='weight' THEN 1 ELSE 0 END)::int AS weights
      FROM events
      WHERE dt IS NOT NULL
      GROUP BY 1
      ORDER BY 1;
    """
    )
    return list(db.execute(q, params).mappings().all())


@router.get("/species-breakdown")
def species_breakdown(db: Session = Depends(get_db)):
    q = text(
        """
      SELECT
        COALESCE(NULLIF(species, ''), 'Unknown') AS species,
        COUNT(*)::int AS count
      FROM pets
      GROUP BY 1
      ORDER BY count DESC;
    """
    )
    return list(db.execute(q).mappings().all())


@router.get("/vaccinations-by-type")
def vaccinations_by_type(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    params = {"start": start, "end": end}
    q = text(
        """
      SELECT
        COALESCE(NULLIF(vaccine_type, ''), 'Unknown') AS type,
        COUNT(*)::int AS count
      FROM vaccinations
      WHERE (CAST(:start AS date) IS NULL OR administered_at::date >= CAST(:start AS date))
        AND (CAST(:end   AS date) IS NULL OR administered_at::date <= CAST(:end   AS date))
      GROUP BY 1
      ORDER BY count DESC;
    """
    )
    return list(db.execute(q, params).mappings().all())


@router.get("/top-organisations-by-visits")
def top_orgs_by_visits(
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    params = {"start": start, "end": end, "limit": limit}
    q = text(
        """
      SELECT
        o.organisation_id::text AS organisation_id,
        o.name AS organisation_name,
        COUNT(vv.visit_id)::int AS visits
      FROM vet_visits vv
      JOIN organisations o ON o.organisation_id = vv.organisation_id
      WHERE (CAST(:start AS date) IS NULL OR vv.visit_datetime::date >= CAST(:start AS date))
        AND (CAST(:end   AS date) IS NULL OR vv.visit_datetime::date <= CAST(:end   AS date))
      GROUP BY o.organisation_id, o.name
      ORDER BY visits DESC
      LIMIT :limit;
    """
    )
    return list(db.execute(q, params).mappings().all())


@router.get("/visits-by-reason")
def visits_by_reason(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    params = {"start": start, "end": end, "org": organisation_id, "limit": limit}
    q = text(
        """
      SELECT
        COALESCE(NULLIF(reason, ''), 'Unknown') AS reason,
        COUNT(*)::int AS count
      FROM vet_visits
      WHERE (CAST(:start AS date) IS NULL OR visit_datetime::date >= CAST(:start AS date))
        AND (CAST(:end   AS date) IS NULL OR visit_datetime::date <= CAST(:end   AS date))
        AND (CAST(:org   AS text) IS NULL OR organisation_id::text = CAST(:org   AS text))
      GROUP BY 1
      ORDER BY count DESC
      LIMIT :limit;
    """
    )
    return list(db.execute(q, params).mappings().all())
