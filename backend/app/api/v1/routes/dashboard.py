"""Module: dashboard."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db

router = APIRouter()

RSPCA_KB_BASE = "https://kb.rspca.org.au/categories/companion-animals"

# Companion-animal links shown to every owner regardless of species.
COMMON_COMPANION_SECTIONS = [
    {"title": "Choosing a Pet", "url": f"{RSPCA_KB_BASE}/choosing-a-pet"},
    {"title": "Pet Ownership", "url": f"{RSPCA_KB_BASE}/pet-ownership"},
    {"title": "Desexing", "url": f"{RSPCA_KB_BASE}/desexing"},
    {"title": "Household and Garden Dangers", "url": f"{RSPCA_KB_BASE}/household-and-garden-dangers"},
    {"title": "Pet Food", "url": f"{RSPCA_KB_BASE}/pet-food"},
    {"title": "Pets and Holidays", "url": f"{RSPCA_KB_BASE}/pets-and-holidays"},
]

# Species-specific resource sections for owner education links.
OWNER_RESOURCE_LIBRARY: dict[str, dict] = {
    "CAT": {
        "title": "Cats",
        "category_url": f"{RSPCA_KB_BASE}/cats",
        "summary": "Care, behaviour, kitten guidance, and health information for cats.",
        "subcategories": [
            {"title": "General", "url": f"{RSPCA_KB_BASE}/cats/general"},
            {"title": "Caring for my Cat", "url": f"{RSPCA_KB_BASE}/cats/caring-for-my-cat"},
            {"title": "Kittens", "url": f"{RSPCA_KB_BASE}/cats/kittens"},
            {"title": "Behaviour", "url": f"{RSPCA_KB_BASE}/cats/behaviour"},
            {"title": "Health Issues", "url": f"{RSPCA_KB_BASE}/cats/health-issues"},
            {"title": "Cat Management", "url": f"{RSPCA_KB_BASE}/cats/cat-management"},
        ],
    },
    "DOG": {
        "title": "Dogs",
        "category_url": f"{RSPCA_KB_BASE}/dogs",
        "summary": "Care and ownership resources for dogs.",
        "subcategories": [
            {"title": "General", "url": f"{RSPCA_KB_BASE}/dogs/general"},
            {"title": "Caring for my Dog", "url": f"{RSPCA_KB_BASE}/dogs/caring-for-my-dog"},
            {"title": "Puppies", "url": f"{RSPCA_KB_BASE}/dogs/puppies"},
            {"title": "Behaviour", "url": f"{RSPCA_KB_BASE}/dogs/behaviour"},
            {"title": "Health Issues", "url": f"{RSPCA_KB_BASE}/dogs/health-issues"},
            {"title": "Training", "url": f"{RSPCA_KB_BASE}/dogs/training"},
            {"title": "Adopting a Greyhound", "url": f"{RSPCA_KB_BASE}/dogs/adopting-a-greyhound"},
        ],
    },
    "RABBIT": {
        "title": "Rabbits",
        "category_url": f"{RSPCA_KB_BASE}/rabbits",
        "summary": "Housing, feeding, and welfare guidance for rabbits.",
        "subcategories": [
            {"title": "All Rabbit Resources", "url": f"{RSPCA_KB_BASE}/rabbits"},
        ],
    },
    "FISH": {
        "title": "Fish",
        "category_url": f"{RSPCA_KB_BASE}/fish",
        "summary": "Aquarium setup and fish welfare guidance.",
        "subcategories": [
            {"title": "All Fish Resources", "url": f"{RSPCA_KB_BASE}/fish"},
        ],
    },
    "BIRD": {
        "title": "Birds",
        "category_url": f"{RSPCA_KB_BASE}/birds",
        "summary": "Care and enrichment resources for birds.",
        "subcategories": [
            {"title": "All Bird Resources", "url": f"{RSPCA_KB_BASE}/birds"},
        ],
    },
    "GUINEA_PIG": {
        "title": "Guinea Pigs",
        "category_url": f"{RSPCA_KB_BASE}/other-pets/guinea-pigs",
        "summary": "Guidance for diet, social needs, and habitat.",
        "subcategories": [
            {"title": "Guinea Pigs", "url": f"{RSPCA_KB_BASE}/other-pets/guinea-pigs"},
        ],
    },
    "REPTILE": {
        "title": "Reptiles",
        "category_url": f"{RSPCA_KB_BASE}/other-pets/reptiles",
        "summary": "Habitat and species-appropriate care information for reptiles.",
        "subcategories": [
            {"title": "Reptiles", "url": f"{RSPCA_KB_BASE}/other-pets/reptiles"},
        ],
    },
}

# Additional section shown when owner has species that map to "Other Pets".
OTHER_PETS_SECTION = {
    "species": "OTHER_PET",
    "title": "Other Pets",
    "summary": "Specialist care guidance for non-cat/dog companion animals.",
    "category_url": f"{RSPCA_KB_BASE}/other-pets",
    "subcategories": [
        {"title": "Reptiles", "url": f"{RSPCA_KB_BASE}/other-pets/reptiles"},
        {"title": "Birds", "url": f"{RSPCA_KB_BASE}/other-pets/birds"},
        {"title": "Rats and Mice", "url": f"{RSPCA_KB_BASE}/other-pets/rats-and-mice"},
        {"title": "Ferrets", "url": f"{RSPCA_KB_BASE}/other-pets/ferrets"},
        {"title": "Guinea Pigs", "url": f"{RSPCA_KB_BASE}/other-pets/guinea-pigs"},
        {"title": "Other Animals", "url": f"{RSPCA_KB_BASE}/other-pets/other-animals"},
    ],
}

OTHER_PET_TRIGGER_SPECIES = {
    "REPTILE",
    "BIRD",
    "RAT",
    "MOUSE",
    "RAT_MOUSE",
    "FERRET",
    "GUINEA_PIG",
    "OTHER_PET",
}


def _normalize_species_key(value: str | None) -> str | None:
    if not value:
        return None
    s = value.strip().upper()
    if not s:
        return None
    aliases = {
        "DOGS": "DOG",
        "CATS": "CAT",
        "RABBITS": "RABBIT",
        "FISHES": "FISH",
        "BIRDS": "BIRD",
        "GUINEA PIG": "GUINEA_PIG",
        "GUINEA-PIG": "GUINEA_PIG",
        "GUINEA PIGS": "GUINEA_PIG",
        "GUINEA-PIGS": "GUINEA_PIG",
        "REPTILES": "REPTILE",
        "RATS": "RAT",
        "MICE": "MOUSE",
        "RATS AND MICE": "RAT_MOUSE",
        "RATS-AND-MICE": "RAT_MOUSE",
        "FERRETS": "FERRET",
        "OTHER PET": "OTHER_PET",
        "OTHER PETS": "OTHER_PET",
    }
    return aliases.get(s, s.replace(" ", "_"))


# Validate and coerce UUID inputs from query/path payloads.
def _parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} (must be UUID)")


# Endpoint: handles HTTP request/response mapping for this route.
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

        clinics_q = text(
            """
            SELECT om.organisation_id::text AS organisation_id, o.name AS clinic_name
            FROM organisation_members om
            JOIN organisations o ON o.organisation_id = om.organisation_id
            WHERE om.user_id = :uid
            ORDER BY o.name
            """
        )
        clinic_rows = list(db.execute(clinics_q, {"uid": uid}).mappings().all())
        clinic_ids = [row["organisation_id"] for row in clinic_rows if row.get("organisation_id")]
        if not clinic_ids:
            return {
                "role": "VET",
                "summary": {
                    "appointments_today": 0,
                    "appointments_week": 0,
                    "appointments_month": 0,
                    "concerns_to_action": 0,
                    "cancellations_month": 0,
                    "injury_cases_month": 0,
                    "medications_due_review": 0,
                    "stock_low_alerts": 0,
                },
                "clinics": [],
                "medication_demand": [],
            }

        summary_q = text(
            """
            SELECT
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.organisation_id::text = ANY(:clinic_ids)
                  AND vv.visit_datetime::date = CURRENT_DATE
              ) AS appointments_today,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.organisation_id::text = ANY(:clinic_ids)
                  AND vv.visit_datetime >= date_trunc('week', NOW())
              ) AS appointments_week,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.organisation_id::text = ANY(:clinic_ids)
                  AND vv.visit_datetime >= date_trunc('month', NOW())
              ) AS appointments_month,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.organisation_id::text = ANY(:clinic_ids)
                  AND (
                    LOWER(COALESCE(vv.reason, '')) LIKE '%follow%' OR
                    LOWER(COALESCE(vv.notes_visible_to_owner, '')) LIKE '%follow%'
                  )
              ) AS concerns_to_action,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.organisation_id::text = ANY(:clinic_ids)
                  AND vv.visit_datetime >= date_trunc('month', NOW())
                  AND (
                    LOWER(COALESCE(vv.reason, '')) LIKE '%cancel%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%no show%' OR
                    LOWER(COALESCE(vv.reason, '')) LIKE '%did not attend%'
                  )
              ) AS cancellations_month,
              (SELECT COUNT(*)::int
                 FROM vet_visits vv
                WHERE vv.organisation_id::text = ANY(:clinic_ids)
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
                      AND vv.organisation_id::text = ANY(:clinic_ids)
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
                  AND vv.organisation_id::text = ANY(:clinic_ids)
              )
            GROUP BY m.name
            ORDER BY prescribed_count_30d DESC, medication_name ASC
            LIMIT 8
            """
        )

        query_params = {"uid": uid, "clinic_ids": clinic_ids}
        med_rows = list(db.execute(medication_demand_q, query_params).mappings().all())
        stock_low_alerts = sum(1 for r in med_rows if int(r.get("prescribed_count_30d") or 0) >= 4)

        summary = dict(db.execute(summary_q, query_params).mappings().one())
        summary["stock_low_alerts"] = stock_low_alerts

        return {
            "role": "VET",
            "summary": summary,
            "clinics": clinic_rows,
            "medication_demand": med_rows,
        }

    return {"role": role_u, "summary": {}}


# Endpoint: handles HTTP request/response mapping for this route.
@router.get("/owner-faq")
def owner_faq_resources(
    user_id: str | None = Query(default=None),
    species: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    selected_species = _normalize_species_key(species) or "ALL"
    species_filters: list[str] = []

    # If user_id is provided, derive species filters from the owner's active pets.
    if user_id:
        uid = _parse_uuid(user_id, "user_id")
        species_rows = db.execute(
            text(
                """
                SELECT DISTINCT UPPER(COALESCE(NULLIF(p.species, ''), 'UNKNOWN')) AS species
                FROM pets p
                JOIN owner_pets op ON op.pet_id = p.pet_id
                JOIN owners o ON o.owner_id = op.owner_id
                WHERE o.user_id = :uid
                  AND op.end_date IS NULL
                ORDER BY species
                """
            ),
            {"uid": uid},
        ).scalars().all()
        species_filters = [s for s in ([_normalize_species_key(x) for x in species_rows]) if s]

    available_species = sorted(set([s for s in species_filters if s in OWNER_RESOURCE_LIBRARY]))
    if not available_species:
        available_species = sorted(OWNER_RESOURCE_LIBRARY.keys())

    # Add synthetic "OTHER_PET" option if owner has species covered by the Other Pets hub.
    has_other_pet_species = bool(set(species_filters) & OTHER_PET_TRIGGER_SPECIES)
    if has_other_pet_species and "OTHER_PET" not in available_species:
        available_species.append("OTHER_PET")
        available_species = sorted(available_species)

    if selected_species != "ALL" and selected_species not in available_species:
        selected_species = "ALL"

    if selected_species == "ALL":
        section_keys = available_species
    else:
        section_keys = [selected_species]

    species_sections = []
    for key in section_keys:
        if key == "OTHER_PET":
            species_sections.append(OTHER_PETS_SECTION)
            continue
        section = OWNER_RESOURCE_LIBRARY.get(key)
        if not section:
            continue
        species_sections.append(
            {
                "species": key,
                "title": section["title"],
                "summary": section["summary"],
                "category_url": section["category_url"],
                "subcategories": section["subcategories"],
            }
        )

    return {
        "source_name": "RSPCA Knowledgebase",
        "source_url": RSPCA_KB_BASE,
        "common_sections": COMMON_COMPANION_SECTIONS,
        "selected_species": selected_species,
        "available_species": ["ALL"] + available_species,
        "species_sections": species_sections,
        "disclaimer": (
            "Resources link to publicly available RSPCA guidance and may change over time. "
            "Refer to the source page for the latest information."
        ),
    }

