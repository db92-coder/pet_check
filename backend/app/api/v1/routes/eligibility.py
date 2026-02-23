"""Module: eligibility."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db
from app.db.models.owner import Owner
from app.db.models.owner_gov_profile import OwnerGovProfile
from app.db.models.owner_pet import OwnerPet
from app.db.models.pet import Pet
from app.db.models.user import User
from app.db.models.vet_visit import VetVisit
from app.db.models.vet_cost_guideline import VetCostGuideline
from app.db.models.weight import Weight

router = APIRouter()


@dataclass
class PetAssessment:
    pet_id: str
    pet_name: str
    species: str
    size_class: str
    annual_min_cost: float
    lifetime_min_cost: float
    has_recent_visit: bool
    weight_discrepancy_flag: bool


# Validate and coerce UUID inputs from query/path payloads.
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        n = float(value)
        return n if n == n else default
    except Exception:
        return default


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, n))


def _size_class_from_weight(species: str, weight_kg: float | None) -> str:
    s = (species or "").strip().lower()
    if s == "horse":
        return "X-Large"
    if s == "bird":
        return "Small"
    if weight_kg is None:
        return "Medium"
    if weight_kg <= 10:
        return "Small"
    if weight_kg <= 25:
        return "Medium"
    if weight_kg <= 40:
        return "Large"
    return "X-Large"


def _guideline_map(db: Session) -> dict[tuple[str, str], VetCostGuideline]:
    rows = db.execute(select(VetCostGuideline)).scalars().all()
    mapping: dict[tuple[str, str], VetCostGuideline] = {}
    for row in rows:
        mapping[(row.species.strip().title(), row.size_class.strip().title())] = row
    return mapping


def _owner_pet_assessments(db: Session, owner_id: uuid.UUID, guideline_lookup: dict[tuple[str, str], VetCostGuideline]) -> list[PetAssessment]:
    pet_rows = db.execute(
        select(Pet)
        .join(OwnerPet, OwnerPet.pet_id == Pet.pet_id)
        .where(OwnerPet.owner_id == owner_id)
        .order_by(Pet.created_at.desc())
    ).scalars().all()

    out: list[PetAssessment] = []
    for pet in pet_rows:
        latest_weight = db.execute(
            select(Weight)
            .where(Weight.pet_id == pet.pet_id)
            .order_by(desc(Weight.measured_at))
            .limit(1)
        ).scalars().first()
        latest_weight_kg = _safe_float(latest_weight.weight_kg) if latest_weight else None

        size_class = _size_class_from_weight(pet.species or "", latest_weight_kg)
        key = ((pet.species or "").strip().title(), size_class)
        guideline = guideline_lookup.get(key) or guideline_lookup.get(((pet.species or "").strip().title(), "Medium"))
        if not guideline:
            # Fallback for unsupported species in guidelines.
            annual_min = 2200.0
            lifespan = 12
        else:
            annual_min = (
                _safe_float(guideline.annual_food_wet)
                + _safe_float(guideline.annual_food_dry)
                + _safe_float(guideline.annual_checkups)
                + _safe_float(guideline.annual_unscheduled)
                + _safe_float(guideline.annual_insurance)
            )
            lifespan = int(guideline.avg_lifespan_years or 12)

        latest_visit = db.execute(
            select(VetVisit)
            .where(VetVisit.pet_id == pet.pet_id)
            .order_by(desc(VetVisit.visit_datetime))
            .limit(1)
        ).scalars().first()
        cutoff = datetime.now(UTC) - timedelta(days=365)
        visit_dt = latest_visit.visit_datetime if latest_visit else None
        if visit_dt and visit_dt.tzinfo is None:
            visit_dt = visit_dt.replace(tzinfo=UTC)
        has_recent_visit = bool(visit_dt and visit_dt >= cutoff)

        latest_owner_weight = db.execute(
            select(Weight)
            .where(Weight.pet_id == pet.pet_id, Weight.visit_id.is_(None))
            .order_by(desc(Weight.measured_at))
            .limit(1)
        ).scalars().first()
        latest_vet_weight = db.execute(
            select(Weight)
            .where(Weight.pet_id == pet.pet_id, Weight.visit_id.is_not(None))
            .order_by(desc(Weight.measured_at))
            .limit(1)
        ).scalars().first()
        weight_flag = False
        if latest_owner_weight and latest_vet_weight:
            owner_w = _safe_float(latest_owner_weight.weight_kg)
            vet_w = _safe_float(latest_vet_weight.weight_kg)
            if vet_w > 0:
                delta = abs(owner_w - vet_w) / vet_w
                weight_flag = delta >= 0.20

        out.append(
            PetAssessment(
                pet_id=str(pet.pet_id),
                pet_name=pet.name or "Unnamed",
                species=(pet.species or "Unknown"),
                size_class=size_class,
                annual_min_cost=round(annual_min, 2),
                lifetime_min_cost=round(annual_min * lifespan, 2),
                has_recent_visit=has_recent_visit,
                weight_discrepancy_flag=weight_flag,
            )
        )
    return out


def _gov_score(profile: OwnerGovProfile, annual_required: float, pet_count: int) -> tuple[float, dict[str, Any]]:
    household_income = _safe_float(profile.household_income)
    expenses = _safe_float(profile.basic_living_expenses)
    tax_payable = _safe_float(profile.assessed_tax_payable)

    disposable_income = max(0.0, household_income - expenses - tax_payable)
    affordability_ratio = disposable_income / max(annual_required, 1.0)

    credit = int(profile.credit_score or 0)
    credit_component = _clamp((credit - 300) / 5.5, 0, 100)

    sqm_per_pet = (profile.property_size_sqm or 0) / max(pet_count, 1)
    housing_component = _clamp((sqm_per_pet / 35.0) * 100, 0, 100)

    support_penalty = 0.0
    if profile.receiving_centrelink_unemployment:
        support_penalty += 12.0
    if profile.receiving_aged_pension:
        support_penalty += 4.0
    if profile.receiving_dva_pension:
        support_penalty += 4.0

    affordability_component = _clamp(affordability_ratio * 50.0, 0, 100)
    raw = (0.50 * affordability_component) + (0.30 * credit_component) + (0.20 * housing_component) - support_penalty
    return round(_clamp(raw), 2), {
        "household_income": round(household_income, 2),
        "basic_living_expenses": round(expenses, 2),
        "assessed_tax_payable": round(tax_payable, 2),
        "disposable_income": round(disposable_income, 2),
        "affordability_ratio": round(affordability_ratio, 3),
        "credit_score": credit,
        "sqm_per_pet": round(sqm_per_pet, 2),
    }


def _vet_score(pets: list[PetAssessment]) -> tuple[float, dict[str, Any]]:
    if not pets:
        return 0.0, {"recent_visit_missing": 0, "weight_flags": 0}
    missing_recent = sum(1 for p in pets if not p.has_recent_visit)
    weight_flags = sum(1 for p in pets if p.weight_discrepancy_flag)
    pet_count = len(pets)

    score = 100.0
    score -= min(35.0, missing_recent * 12.0)
    score -= min(40.0, weight_flags * 15.0)
    score -= min(15.0, max(0, pet_count - 3) * 3.0)
    return round(_clamp(score), 2), {"recent_visit_missing": missing_recent, "weight_flags": weight_flags}


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/owner/{owner_id}")
def owner_eligibility(owner_id: str, db: Session = Depends(get_db)):
    oid = _parse_uuid(owner_id, "owner_id")
    owner = db.execute(select(Owner).where(Owner.owner_id == oid)).scalars().first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    user = db.execute(select(User).where(User.user_id == owner.user_id)).scalars().first()
    profile = db.execute(select(OwnerGovProfile).where(OwnerGovProfile.owner_id == oid)).scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Owner government profile not found")

    guideline_lookup = _guideline_map(db)
    pet_assessments = _owner_pet_assessments(db, oid, guideline_lookup)
    annual_required = sum(p.annual_min_cost for p in pet_assessments)

    vet_score, vet_meta = _vet_score(pet_assessments)
    gov_score, gov_meta = _gov_score(profile, annual_required, len(pet_assessments))

    overall = round((0.45 * vet_score) + (0.55 * gov_score), 2)
    risk_level = "LOW" if overall >= 70 else "MEDIUM" if overall >= 45 else "HIGH"

    return {
        "owner_id": str(oid),
        "user_id": str(owner.user_id),
        "owner_name": user.full_name if user else None,
        "owner_email": user.email if user else None,
        "pet_count": len(pet_assessments),
        "annual_required_cost_min": round(annual_required, 2),
        "vet_score": vet_score,
        "gov_score": gov_score,
        "overall_eligibility_score": overall,
        "risk_level": risk_level,
        "vet_meta": vet_meta,
        "gov_meta": gov_meta,
        "pets": [p.__dict__ for p in pet_assessments],
    }


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/owners")
def eligibility_leaderboard(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    owners = db.execute(select(Owner).limit(limit * 2)).scalars().all()
    guideline_lookup = _guideline_map(db)

    results = []
    for owner in owners:
        profile = db.execute(select(OwnerGovProfile).where(OwnerGovProfile.owner_id == owner.owner_id)).scalars().first()
        if not profile:
            continue
        user = db.execute(select(User).where(User.user_id == owner.user_id)).scalars().first()
        pet_assessments = _owner_pet_assessments(db, owner.owner_id, guideline_lookup)
        annual_required = sum(p.annual_min_cost for p in pet_assessments)
        vet_score, _ = _vet_score(pet_assessments)
        gov_score, _ = _gov_score(profile, annual_required, len(pet_assessments))
        overall = round((0.45 * vet_score) + (0.55 * gov_score), 2)
        results.append(
            {
                "owner_id": str(owner.owner_id),
                "user_id": str(owner.user_id),
                "owner_name": user.full_name if user else None,
                "owner_email": user.email if user else None,
                "pet_count": len(pet_assessments),
                "overall_eligibility_score": overall,
                "vet_score": vet_score,
                "gov_score": gov_score,
                "risk_level": "LOW" if overall >= 70 else "MEDIUM" if overall >= 45 else "HIGH",
            }
        )

    results.sort(key=lambda r: r["overall_eligibility_score"], reverse=True)
    return results[:limit]

