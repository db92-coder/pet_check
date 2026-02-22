from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db

router = APIRouter()


def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


@router.get("/kpis")
def dashboard_kpis(
    role: str = Query(..., pattern="^(ADMIN|VET|OWNER)$"),
    user_id: str | None = None,
    db: Session = Depends(get_db),
):
    role_u = role.upper()

    if role_u == "ADMIN":
        summary_q = text(
            """
            SELECT
              (SELECT COUNT(*)::int FROM organisations WHERE org_type = 'vet_clinic') AS clinic_count,
              (SELECT COUNT(DISTINCT user_id)::int FROM organisation_members) AS staff_registered,
              (SELECT COUNT(*)::int FROM vet_visits WHERE visit_datetime::date = CURRENT_DATE) AS visits_today,
              (SELECT COUNT(*)::int FROM vet_visits WHERE visit_datetime >= date_trunc('week', NOW())) AS visits_week,
              (SELECT COUNT(*)::int FROM vet_visits WHERE visit_datetime >= date_trunc('month', NOW())) AS visits_month,
              (SELECT COUNT(*)::int
                 FROM vet_visits
                WHERE visit_datetime >= date_trunc('month', NOW())
                  AND (
                    LOWER(COALESCE(reason, '')) LIKE '%no show%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%no-show%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%cancel%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%did not attend%'
                  )
              ) AS missed_appointments_month,
              (SELECT COUNT(*)::int
                 FROM vet_visits
                WHERE visit_datetime >= date_trunc('month', NOW())
                  AND (
                    LOWER(COALESCE(reason, '')) LIKE '%injury%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%trauma%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%accident%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%fracture%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%wound%' OR
                    LOWER(COALESCE(reason, '')) LIKE '%bite%'
                  )
              ) AS injury_related_visits_month,
              (SELECT COUNT(*)::int
                 FROM pets p
                WHERE NOT EXISTS (
                  SELECT 1
                    FROM vet_visits vv
                   WHERE vv.pet_id = p.pet_id
                     AND vv.visit_datetime >= NOW() - INTERVAL '365 days'
                )
              ) AS concerns_unfollowed
            """
        )

        visits_by_clinic_q = text(
            """
            SELECT
              o.organisation_id::text AS organisation_id,
              o.name AS clinic_name,
              COUNT(vv.visit_id)::int AS visits
            FROM organisations o
            LEFT JOIN vet_visits vv ON vv.organisation_id = o.organisation_id
            WHERE o.org_type = 'vet_clinic'
            GROUP BY o.organisation_id, o.name
            ORDER BY visits DESC, clinic_name ASC
            LIMIT 8
            """
        )

        injury_by_clinic_q = text(
            """
            SELECT
              o.organisation_id::text AS organisation_id,
              o.name AS clinic_name,
              COUNT(vv.visit_id)::int AS injury_visits
            FROM organisations o
            JOIN vet_visits vv ON vv.organisation_id = o.organisation_id
            WHERE o.org_type = 'vet_clinic'
              AND vv.visit_datetime >= date_trunc('month', NOW())
              AND (
                LOWER(COALESCE(vv.reason, '')) LIKE '%injury%' OR
                LOWER(COALESCE(vv.reason, '')) LIKE '%trauma%' OR
                LOWER(COALESCE(vv.reason, '')) LIKE '%accident%' OR
                LOWER(COALESCE(vv.reason, '')) LIKE '%fracture%' OR
                LOWER(COALESCE(vv.reason, '')) LIKE '%wound%' OR
                LOWER(COALESCE(vv.reason, '')) LIKE '%bite%'
              )
            GROUP BY o.organisation_id, o.name
            ORDER BY injury_visits DESC, clinic_name ASC
            LIMIT 8
            """
        )

        return {
            "role": "ADMIN",
            "summary": dict(db.execute(summary_q).mappings().one()),
            "visits_by_clinic": list(db.execute(visits_by_clinic_q).mappings().all()),
            "injury_by_clinic": list(db.execute(injury_by_clinic_q).mappings().all()),
        }

    if role_u == "VET":
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required for VET dashboard KPIs")
        uid = _parse_uuid(user_id, "user_id")

        summary_q = text(
            """
            SELECT
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.vet_user_id = :uid
                  AND vv.visit_datetime::date = CURRENT_DATE
              ) AS appointments_today,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.vet_user_id = :uid
                  AND vv.visit_datetime >= date_trunc('week', NOW())
              ) AS appointments_week,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.vet_user_id = :uid
                  AND vv.visit_datetime >= date_trunc('month', NOW())
              ) AS appointments_month,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.vet_user_id = :uid
                  AND (
                    LOWER(COALESCE(vv.reason, '')) LIKE '%follow%' OR
                    LOWER(COALESCE(vv.notes_visible_to_owner, '')) LIKE '%follow%'
                  )
              ) AS concerns_to_action,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.vet_user_id = :uid
                  AND vv.visit_datetime >= date_trunc('month', NOW())
                  AND (
                    LOWER(COALESCE(vv.reason, '')) LIKE '%cancel%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%no show%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%did not attend%'
                  )
              ) AS cancellations_month,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.vet_user_id = :uid
                  AND vv.visit_datetime >= date_trunc('month', NOW())
                  AND (
                    LOWER(COALESCE(vv.reason, '')) LIKE '%injury%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%trauma%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%accident%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%fracture%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%wound%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%bite%'
                  )
              ) AS injury_cases_month,
              (SELECT COUNT(*)::int
                 FROM medications m
                WHERE m.end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '14 days'
                  AND EXISTS (
                    SELECT 1
                    FROM vet_visits vv
                    WHERE vv.pet_id = m.pet_id
                      AND vv.vet_user_id = :uid
                  )
              ) AS medications_due_review
            """
        )

        medication_demand_q = text(
            """
            SELECT
              m.name AS medication_name,
              COUNT(*)::int AS prescribed_count_30d
            FROM medications m
            WHERE m.start_date >= CURRENT_DATE - INTERVAL '30 days'
              AND EXISTS (
                SELECT 1
                FROM vet_visits vv
                WHERE vv.pet_id = m.pet_id
                  AND vv.vet_user_id = :uid
              )
            GROUP BY m.name
            ORDER BY prescribed_count_30d DESC, medication_name ASC
            LIMIT 8
            """
        )

        med_rows = list(db.execute(medication_demand_q, {"uid": uid}).mappings().all())
        stock_low_alerts = sum(1 for r in med_rows if int(r.get("prescribed_count_30d") or 0) >= 4)

        summary = dict(db.execute(summary_q, {"uid": uid}).mappings().one())
        summary["stock_low_alerts"] = stock_low_alerts

        return {
            "role": "VET",
            "summary": summary,
            "medication_demand": med_rows,
        }

    return {"role": role_u, "summary": {}}
