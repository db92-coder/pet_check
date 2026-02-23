"""Module: analytics."""

import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db

router = APIRouter()


def _query_care_events_by_month(
    db: Session,
    *,
    start: date | None,
    end: date | None,
    organisation_id: str | None,
    month: str | None,
    vaccine_type: str | None,
    visit_reason: str | None,
):
    params = {
        "start": start,
        "end": end,
        "org": organisation_id,
        "month": month,
        "vaccine_type": vaccine_type,
        "visit_reason": visit_reason,
    }

    q = text(
        """
      WITH events AS (
        SELECT vv.visit_datetime AS dt, 'visit'::text AS kind
        FROM vet_visits vv
        WHERE (CAST(:start AS date) IS NULL OR vv.visit_datetime::date >= CAST(:start AS date))
          AND (CAST(:end   AS date) IS NULL OR vv.visit_datetime::date <= CAST(:end   AS date))
          AND (CAST(:org   AS text) IS NULL OR vv.organisation_id::text = CAST(:org AS text))
          AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', vv.visit_datetime), 'YYYY-MM') = CAST(:month AS text))
          AND (CAST(:visit_reason AS text) IS NULL OR COALESCE(NULLIF(vv.reason, ''), 'Unknown') = CAST(:visit_reason AS text))

        UNION ALL

        SELECT v.administered_at AS dt, 'vaccination'::text AS kind
        FROM vaccinations v
        WHERE (CAST(:start AS date) IS NULL OR v.administered_at::date >= CAST(:start AS date))
          AND (CAST(:end   AS date) IS NULL OR v.administered_at::date <= CAST(:end   AS date))
          AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', v.administered_at), 'YYYY-MM') = CAST(:month AS text))
          AND (CAST(:vaccine_type AS text) IS NULL OR COALESCE(NULLIF(v.vaccine_type, ''), 'Unknown') = CAST(:vaccine_type AS text))
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
          AND (CAST(:end   AS date) IS NULL OR w.measured_at::date <= CAST(:end   AS date))
          AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', w.measured_at), 'YYYY-MM') = CAST(:month AS text))
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


def _query_vaccinations_by_type(
    db: Session,
    *,
    start: date | None,
    end: date | None,
    organisation_id: str | None,
    month: str | None,
    vaccine_type: str | None,
):
    params = {
        "start": start,
        "end": end,
        "org": organisation_id,
        "month": month,
        "vaccine_type": vaccine_type,
    }
    q = text(
        """
      SELECT
        COALESCE(NULLIF(v.vaccine_type, ''), 'Unknown') AS type,
        COUNT(*)::int AS count
      FROM vaccinations v
      WHERE (CAST(:start AS date) IS NULL OR v.administered_at::date >= CAST(:start AS date))
        AND (CAST(:end   AS date) IS NULL OR v.administered_at::date <= CAST(:end   AS date))
        AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', v.administered_at), 'YYYY-MM') = CAST(:month AS text))
        AND (CAST(:vaccine_type AS text) IS NULL OR COALESCE(NULLIF(v.vaccine_type, ''), 'Unknown') = CAST(:vaccine_type AS text))
        AND (CAST(:org AS text) IS NULL OR EXISTS (
              SELECT 1
              FROM vet_visits vv
              WHERE vv.visit_id = v.visit_id
                AND vv.organisation_id::text = CAST(:org AS text)
            ))
      GROUP BY 1
      ORDER BY count DESC;
    """
    )
    return list(db.execute(q, params).mappings().all())


def _query_top_orgs_by_visits(
    db: Session,
    *,
    start: date | None,
    end: date | None,
    organisation_id: str | None,
    month: str | None,
    visit_reason: str | None,
    limit: int,
):
    params = {
        "start": start,
        "end": end,
        "org": organisation_id,
        "month": month,
        "visit_reason": visit_reason,
        "limit": limit,
    }
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
        AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', vv.visit_datetime), 'YYYY-MM') = CAST(:month AS text))
        AND (CAST(:org   AS text) IS NULL OR vv.organisation_id::text = CAST(:org AS text))
        AND (CAST(:visit_reason AS text) IS NULL OR COALESCE(NULLIF(vv.reason, ''), 'Unknown') = CAST(:visit_reason AS text))
      GROUP BY o.organisation_id, o.name
      ORDER BY visits DESC
      LIMIT :limit;
    """
    )
    return list(db.execute(q, params).mappings().all())


def _query_visits_by_reason(
    db: Session,
    *,
    start: date | None,
    end: date | None,
    organisation_id: str | None,
    month: str | None,
    visit_reason: str | None,
    limit: int,
):
    params = {
        "start": start,
        "end": end,
        "org": organisation_id,
        "month": month,
        "visit_reason": visit_reason,
        "limit": limit,
    }
    q = text(
        """
      SELECT
        COALESCE(NULLIF(vv.reason, ''), 'Unknown') AS reason,
        COUNT(*)::int AS count
      FROM vet_visits vv
      WHERE (CAST(:start AS date) IS NULL OR vv.visit_datetime::date >= CAST(:start AS date))
        AND (CAST(:end   AS date) IS NULL OR vv.visit_datetime::date <= CAST(:end   AS date))
        AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', vv.visit_datetime), 'YYYY-MM') = CAST(:month AS text))
        AND (CAST(:org   AS text) IS NULL OR vv.organisation_id::text = CAST(:org AS text))
        AND (CAST(:visit_reason AS text) IS NULL OR COALESCE(NULLIF(vv.reason, ''), 'Unknown') = CAST(:visit_reason AS text))
      GROUP BY 1
      ORDER BY count DESC
      LIMIT :limit;
    """
    )
    return list(db.execute(q, params).mappings().all())


# Endpoint: handles HTTP request/response mapping for this route.
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


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/care-events-by-month")
def care_events_by_month(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    vaccine_type: str | None = None,
    visit_reason: str | None = None,
    db: Session = Depends(get_db),
):
    return _query_care_events_by_month(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        vaccine_type=vaccine_type,
        visit_reason=visit_reason,
    )


# Endpoint: handles HTTP request/response mapping for this route.
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


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/vaccinations-by-type")
def vaccinations_by_type(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    vaccine_type: str | None = None,
    db: Session = Depends(get_db),
):
    return _query_vaccinations_by_type(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        vaccine_type=vaccine_type,
    )


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/top-organisations-by-visits")
def top_orgs_by_visits(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    visit_reason: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return _query_top_orgs_by_visits(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        visit_reason=visit_reason,
        limit=limit,
    )


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/visits-by-reason")
def visits_by_reason(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    visit_reason: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return _query_visits_by_reason(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        visit_reason=visit_reason,
        limit=limit,
    )


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/filter-options")
def analytics_filter_options(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
):
    params = {"start": start, "end": end, "org": organisation_id, "month": month}

    orgs_q = text(
        """
      SELECT organisation_id::text AS organisation_id, name
      FROM organisations
      ORDER BY name;
    """
    )
    months_q = text(
        """
      WITH months AS (
        SELECT to_char(date_trunc('month', vv.visit_datetime), 'YYYY-MM') AS month
        FROM vet_visits vv
        WHERE (CAST(:start AS date) IS NULL OR vv.visit_datetime::date >= CAST(:start AS date))
          AND (CAST(:end   AS date) IS NULL OR vv.visit_datetime::date <= CAST(:end   AS date))
          AND (CAST(:org   AS text) IS NULL OR vv.organisation_id::text = CAST(:org AS text))
        UNION
        SELECT to_char(date_trunc('month', v.administered_at), 'YYYY-MM') AS month
        FROM vaccinations v
        WHERE (CAST(:start AS date) IS NULL OR v.administered_at::date >= CAST(:start AS date))
          AND (CAST(:end   AS date) IS NULL OR v.administered_at::date <= CAST(:end   AS date))
          AND (CAST(:org AS text) IS NULL OR EXISTS (
                SELECT 1
                FROM vet_visits vv
                WHERE vv.visit_id = v.visit_id
                  AND vv.organisation_id::text = CAST(:org AS text)
              ))
        UNION
        SELECT to_char(date_trunc('month', w.measured_at), 'YYYY-MM') AS month
        FROM weights w
        WHERE (CAST(:start AS date) IS NULL OR w.measured_at::date >= CAST(:start AS date))
          AND (CAST(:end   AS date) IS NULL OR w.measured_at::date <= CAST(:end   AS date))
          AND (CAST(:org AS text) IS NULL OR EXISTS (
                SELECT 1
                FROM vet_visits vv
                WHERE vv.visit_id = w.visit_id
                  AND vv.organisation_id::text = CAST(:org AS text)
              ))
      )
      SELECT month
      FROM months
      WHERE month IS NOT NULL
      ORDER BY month;
    """
    )
    vaccine_types_q = text(
        """
      SELECT DISTINCT COALESCE(NULLIF(v.vaccine_type, ''), 'Unknown') AS vaccine_type
      FROM vaccinations v
      WHERE (CAST(:start AS date) IS NULL OR v.administered_at::date >= CAST(:start AS date))
        AND (CAST(:end   AS date) IS NULL OR v.administered_at::date <= CAST(:end   AS date))
        AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', v.administered_at), 'YYYY-MM') = CAST(:month AS text))
        AND (CAST(:org AS text) IS NULL OR EXISTS (
              SELECT 1
              FROM vet_visits vv
              WHERE vv.visit_id = v.visit_id
                AND vv.organisation_id::text = CAST(:org AS text)
            ))
      ORDER BY vaccine_type;
    """
    )
    visit_reasons_q = text(
        """
      SELECT DISTINCT COALESCE(NULLIF(vv.reason, ''), 'Unknown') AS visit_reason
      FROM vet_visits vv
      WHERE (CAST(:start AS date) IS NULL OR vv.visit_datetime::date >= CAST(:start AS date))
        AND (CAST(:end   AS date) IS NULL OR vv.visit_datetime::date <= CAST(:end   AS date))
        AND (CAST(:month AS text) IS NULL OR to_char(date_trunc('month', vv.visit_datetime), 'YYYY-MM') = CAST(:month AS text))
        AND (CAST(:org   AS text) IS NULL OR vv.organisation_id::text = CAST(:org AS text))
      ORDER BY visit_reason;
    """
    )

    organisations = list(db.execute(orgs_q).mappings().all())
    months = [r["month"] for r in db.execute(months_q, params).mappings().all()]
    vaccine_types = [r["vaccine_type"] for r in db.execute(vaccine_types_q, params).mappings().all()]
    visit_reasons = [r["visit_reason"] for r in db.execute(visit_reasons_q, params).mappings().all()]

    return {
        "organisations": organisations,
        "months": months,
        "vaccine_types": vaccine_types,
        "visit_reasons": visit_reasons,
    }


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/export")
def export_analytics(
    start: date | None = None,
    end: date | None = None,
    organisation_id: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    vaccine_type: str | None = None,
    visit_reason: str | None = None,
    db: Session = Depends(get_db),
):
    care_rows = _query_care_events_by_month(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        vaccine_type=vaccine_type,
        visit_reason=visit_reason,
    )
    vax_rows = _query_vaccinations_by_type(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        vaccine_type=vaccine_type,
    )
    top_org_rows = _query_top_orgs_by_visits(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        visit_reason=visit_reason,
        limit=50,
    )
    reason_rows = _query_visits_by_reason(
        db,
        start=start,
        end=end,
        organisation_id=organisation_id,
        month=month,
        visit_reason=visit_reason,
        limit=50,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["dataset", "group_1", "group_2", "metric", "value"])

    for row in care_rows:
        month_value = row.get("month")
        writer.writerow(["care_events_by_month", month_value, "", "total", row.get("total", 0)])
        writer.writerow(["care_events_by_month", month_value, "", "visits", row.get("visits", 0)])
        writer.writerow(["care_events_by_month", month_value, "", "vaccinations", row.get("vaccinations", 0)])
        writer.writerow(["care_events_by_month", month_value, "", "weights", row.get("weights", 0)])

    for row in vax_rows:
        writer.writerow(["vaccinations_by_type", row.get("type"), "", "count", row.get("count", 0)])

    for row in top_org_rows:
        writer.writerow(
            [
                "top_organisations_by_visits",
                row.get("organisation_name") or "Unknown",
                row.get("organisation_id") or "",
                "visits",
                row.get("visits", 0),
            ]
        )

    for row in reason_rows:
        writer.writerow(["visits_by_reason", row.get("reason"), "", "count", row.get("count", 0)])

    buffer.seek(0)
    filename = f"analytics_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="text/csv", headers=headers)

