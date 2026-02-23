"""Module: clinics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db
from app.db.models.organisation import Organisation
from app.db.models.organisation_member import OrganisationMember
from app.db.models.vet_visit import VetVisit

router = APIRouter()


# Validate and coerce UUID inputs from query/path payloads.
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


def _to_float(value: str | float | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _simulated_tas_coordinates(seed: int) -> tuple[float, float]:
    """
    Generate deterministic fallback coordinates within Tasmania bounds.
    This keeps distances/maps usable when source data lacks lat/lon.
    """
    # Rough TAS bounds
    lat_min, lat_max = -43.8, -39.2
    lon_min, lon_max = 143.7, 148.6
    # Deterministic pseudo-random fraction from stable seed
    frac_a = ((seed * 1103515245 + 12345) % 10_000) / 10_000.0
    frac_b = ((seed * 214013 + 2531011) % 10_000) / 10_000.0
    lat = lat_min + (lat_max - lat_min) * frac_a
    lon = lon_min + (lon_max - lon_min) * frac_b
    return (round(lat, 6), round(lon, 6))


# Approximate postcode centroids (TAS) used when imported data lacks lat/lon.
POSTCODE_COORDS_TAS: dict[str, tuple[float, float]] = {
    "7000": (-42.8821, 147.3272),  # Hobart
    "7005": (-42.9050, 147.3230),  # Sandy Bay
    "7008": (-42.8780, 147.3090),  # Lenah Valley / West Hobart
    "7009": (-42.8620, 147.2860),  # Moonah area
    "7011": (-42.8070, 147.2520),  # Claremont
    "7015": (-42.8360, 147.3530),  # Lindisfarne
    "7018": (-42.8720, 147.3650),  # Rosny/Bellerive
    "7050": (-42.9750, 147.3080),  # Kingston
    "7053": (-42.9850, 147.3200),  # Taroona/Kingston surrounds
    "7172": (-42.7360, 147.5790),  # Dodges Ferry
    "7173": (-42.7820, 147.5620),  # Sorell
    "7216": (-41.3210, 148.2410),  # St Helens
    "7249": (-41.4550, 147.1320),  # Kings Meadows/South Launceston
    "7250": (-41.4330, 147.1380),  # Launceston
    "7260": (-41.1670, 146.9560),  # Lilydale
    "7268": (-41.1570, 147.5180),  # Scottsdale
    "7275": (-41.2980, 146.9700),  # Exeter
    "7301": (-41.5400, 146.6600),  # Deloraine/Longford region
    "7304": (-41.3900, 146.3300),  # Sheffield
    "7306": (-41.1900, 146.1650),  # Devonport surrounds
    "7310": (-41.1760, 146.3510),  # Devonport
    "7315": (-41.1600, 146.1660),  # Ulverstone
    "7316": (-41.1100, 146.0700),  # Penguin
    "7320": (-41.0540, 145.9030),  # Burnie
    "7330": (-40.8440, 145.1240),  # Smithton
}

SUBURB_COORDS_TAS: dict[str, tuple[float, float]] = {
    "sandy bay": (-42.9050, 147.3230),
    "launceston": (-41.4330, 147.1380),
    "devonport": (-41.1760, 146.3510),
    "burnie": (-41.0540, 145.9030),
    "ulverstone": (-41.1600, 146.1660),
    "penguin": (-41.1100, 146.0700),
    "kingston": (-42.9750, 147.3080),
    "rosny park": (-42.8720, 147.3650),
    "lindisfarne": (-42.8360, 147.3530),
    "bellerive": (-42.8750, 147.3700),
    "claremont": (-42.8070, 147.2520),
    "st helens": (-41.3210, 148.2410),
    "sorell": (-42.7820, 147.5620),
    "smithton": (-40.8440, 145.1240),
}


def _jitter_from_seed(seed: int) -> tuple[float, float]:
    # Keep clinics in same suburb/postcode visible as separate points without moving far.
    d_lat = (((seed * 37) % 1000) / 1000.0 - 0.5) * 0.04
    d_lon = (((seed * 53) % 1000) / 1000.0 - 0.5) * 0.04
    return d_lat, d_lon


def _resolve_clinic_coordinates(clinic: Organisation, seed: int) -> tuple[float, float, bool]:
    # 1) Prefer stored coordinates if present.
    lat = _to_float(clinic.latitude)
    lon = _to_float(clinic.longitude)
    if lat is not None and lon is not None:
        return lat, lon, False

    # 2) Use postcode centroid when available.
    postcode = (clinic.postcode or "").strip()
    if postcode in POSTCODE_COORDS_TAS:
        base_lat, base_lon = POSTCODE_COORDS_TAS[postcode]
        j_lat, j_lon = _jitter_from_seed(seed)
        return round(base_lat + j_lat, 6), round(base_lon + j_lon, 6), True

    # 3) Fallback to suburb centroid.
    suburb_key = (clinic.suburb or "").strip().lower()
    if suburb_key in SUBURB_COORDS_TAS:
        base_lat, base_lon = SUBURB_COORDS_TAS[suburb_key]
        j_lat, j_lon = _jitter_from_seed(seed)
        return round(base_lat + j_lat, 6), round(base_lon + j_lon, 6), True

    # 4) Last resort for unknown suburb/postcode.
    lat, lon = _simulated_tas_coordinates(seed)
    return lat, lon, True


def _simulated_capacity_metrics(seed: int, staff_count: int, visits_30d: int) -> tuple[int, int]:
    """
    Provide deterministic mock numbers for upcoming visits/cancellations when live
    scheduling data is not yet available.
    """
    # Upcoming generally scales with staff and recent demand.
    baseline_upcoming = max(3, int(visits_30d * 0.35)) + max(1, staff_count // 3)
    spread = seed % 6
    upcoming = baseline_upcoming + spread

    # Cancellations typically 3-12% of upcoming.
    cancel_rate_bucket = 3 + (seed % 10)  # 3-12
    cancellations = max(0, int(round(upcoming * (cancel_rate_bucket / 100.0))))
    return upcoming, cancellations


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("", summary="List clinics with capacity/cancellation insights")
def list_clinics(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db)):
    clinics = db.execute(
        select(Organisation).where(Organisation.org_type == "vet_clinic").limit(limit)
    ).scalars().all()

    out = []
    for clinic in clinics:
        cid = clinic.organisation_id
        clinic_seed = cid.int % 1_000_000
        staff_count = db.execute(
            select(func.count(OrganisationMember.user_id)).where(OrganisationMember.organisation_id == cid)
        ).scalar_one()

        # Use Python-safe datetime boundaries for cross-dialect compatibility.
        dt_30 = datetime.now(UTC) - timedelta(days=30)
        visits_30d = db.execute(
            select(func.count(VetVisit.visit_id)).where(
                VetVisit.organisation_id == cid,
                VetVisit.visit_datetime >= dt_30,
            )
        ).scalar_one()

        cancellations_30d = db.execute(
            select(func.count(VetVisit.visit_id)).where(
                VetVisit.organisation_id == cid,
                VetVisit.visit_datetime >= dt_30,
                func.lower(func.coalesce(VetVisit.reason, "")).like("%cancel%"),
            )
        ).scalar_one()

        upcoming_7d = db.execute(
            select(func.count(VetVisit.visit_id)).where(
                VetVisit.organisation_id == cid,
                VetVisit.visit_datetime >= datetime.now(UTC),
                VetVisit.visit_datetime <= datetime.now(UTC) + timedelta(days=7),
            )
        ).scalar_one()

        # Simulate demand metrics if schedule/cancellation data is empty.
        if int(upcoming_7d or 0) == 0 and int(cancellations_30d or 0) == 0:
            sim_upcoming, sim_cancel = _simulated_capacity_metrics(
                clinic_seed,
                int(staff_count or 0),
                int(visits_30d or 0),
            )
            upcoming_7d = sim_upcoming
            cancellations_30d = sim_cancel
            metrics_simulated = True
        else:
            metrics_simulated = False

        lat, lon, geo_simulated = _resolve_clinic_coordinates(clinic, clinic_seed)

        out.append(
            {
                "id": str(cid),
                "name": clinic.name,
                "phone": clinic.phone,
                "email": clinic.email,
                "address": clinic.address,
                "suburb": clinic.suburb,
                "state": clinic.state,
                "postcode": clinic.postcode,
                "latitude": lat,
                "longitude": lon,
                "geo_simulated": geo_simulated,
                "staff_count": int(staff_count or 0),
                "visits_last_30d": int(visits_30d or 0),
                "cancellations_last_30d": int(cancellations_30d or 0),
                "upcoming_visits_next_7d": int(upcoming_7d or 0),
                "metrics_simulated": metrics_simulated,
            }
        )

    return out


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/{clinic_id}/staff", summary="List staff for a clinic")
def clinic_staff(clinic_id: str, db: Session = Depends(get_db)):
    cid = _parse_uuid(clinic_id, "clinic_id")
    from app.db.models.user import User

    rows = db.execute(
        select(
            User.user_id.label("user_id"),
            User.full_name.label("full_name"),
            User.email.label("email"),
            User.phone.label("phone"),
            User.role.label("role"),
            OrganisationMember.member_role.label("member_role"),
        )
        .select_from(OrganisationMember)
        .join(User, User.user_id == OrganisationMember.user_id)
        .where(OrganisationMember.organisation_id == cid)
    ).mappings().all()
    out = []
    for r in rows:
        d = dict(r)
        d["user_id"] = str(d["user_id"])
        out.append(d)
    return out

