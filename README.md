# Pet Protect

[![Docker](https://img.shields.io/badge/Docker-Ready-informational)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-informational)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-Backend-informational)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-informational)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-informational)](https://www.sqlalchemy.org/)
[![React](https://img.shields.io/badge/React-Frontend-informational)](https://react.dev/)

Pet Protect is a full-stack pet health management platform with role-based access, owner-facing pet care dashboards, analytics, and seeded development data.

## Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
- [Role Access Matrix](#role-access-matrix)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Highlights](#api-highlights)
- [Getting Started](#getting-started)
- [Database Seeding](#database-seeding)
- [Screenshots](#screenshots)
- [Troubleshooting](#troubleshooting)

## Overview

Pet Protect supports:

- Secure login based on credentials in the `users` table.
- Dynamic role-aware navigation and page access.
- Owner account creation with initial pet setup.
- Ongoing owner workflows: add/edit pets, upload pet photos, track weight trends.
- Pet health visibility: vaccinations, medications, microchip numbers.
- Admin analytics for organisation and care-event trends.

## Core Features

### Authentication and Users

- Login endpoint validates `email + password` against database records.
- User profile (`/auth/me`) resolves active identity and role.
- User roles persisted in DB (`users.role`): `ADMIN`, `VET`, `OWNER`.
- Owner self-registration flow from login page with initial pet details.

### Role-Based App Experience

- Dynamic sidebar and route access based on role.
- Admin and vet operational pages.
- Owner-focused dashboard and care visibility.

### Owner Dashboard

- Personal profile snapshot.
- Current pets list with editable details.
- Add Pet modal (floating dialog).
- Pet photo upload from local device (`jpg`, `jpeg`, `png`) stored in DB blob.
- Upcoming appointments.
- Vaccination due dates.
- Pet-level health summary including:
  - Microchip number
  - Current vaccinations
  - Current medications
- Weight tracking:
  - Add weight with date
  - Line trend chart by date (x-axis) and weight in kg (y-axis)

### Analytics

Admin analytics page includes:

- KPI totals
- Care events by month
- Vaccinations by type
- Top organisations by visits
- Visits by reason

## Role Access Matrix

| Route / Area | ADMIN | VET | OWNER |
|---|---:|---:|---:|
| Dashboard | Yes | Yes | Yes |
| Pets | Yes | Yes | No |
| Visits | Yes | Yes | No |
| Owners | Yes | Yes | No |
| Clinics | Yes | Yes | No |
| Staff | Yes | Yes | No |
| Users | Yes | Yes | No |
| Admin Analytics | Yes | No | No |

## Tech Stack

### Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- python-multipart (file uploads)

### Frontend

- React + Vite
- MUI
- Axios
- Nivo charts

### Infra

- Docker + Docker Compose

## Project Structure

```text
pet-check/
+-- backend/
�   +-- app/
�   �   +-- api/v1/routes/
�   �   +-- db/models/
�   �   +-- scripts/
�   �   +-- main.py
�   +-- requirements.txt
�   +-- Dockerfile
+-- frontend/
�   +-- src/
+-- services/
�   +-- mock_gov/
�   +-- mock_vet/
+-- pet_check_screenshots/
+-- docker-compose.yml
+-- README.md
```

## API Highlights

### Auth

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/register-owner` (multipart owner registration + pet photo upload)

### Pets

- `GET /api/v1/pets` (supports `user_id` / `owner_id` filtering)
- `POST /api/v1/pets` (add pet)
- `PUT /api/v1/pets/{pet_id}` (edit pet)
- `GET /api/v1/pets/{pet_id}/photo` (pet photo blob)
- `GET /api/v1/pets/{pet_id}/vaccinations`
- `GET /api/v1/pets/{pet_id}/medications`
- `GET /api/v1/pets/{pet_id}/weights`
- `POST /api/v1/pets/{pet_id}/weights`

### Analytics

- `GET /api/v1/analytics/kpis`
- `GET /api/v1/analytics/care-events-by-month`
- `GET /api/v1/analytics/vaccinations-by-type`
- `GET /api/v1/analytics/top-organisations-by-visits`
- `GET /api/v1/analytics/visits-by-reason`

## Getting Started

### Prerequisites

- Docker Desktop running

### Start the stack

From repo root:

```bash
docker compose up -d --build
```

### Verify containers

```bash
docker ps
```

## Database Seeding

Run seed:

```bash
docker exec -it petcheck_backend python -m app.scripts.seed_data
```

This will:

- Reset core data tables.
- Seed users with generated passwords and roles.
- Seed owners, pets, visits, weights, vaccinations, and medications.
- Export credentials CSV to:
  - `backend/app/scripts/seeded_user_credentials.csv`

### Optional utility scripts

Normalize existing user phone numbers to AU mobile format:

```bash
docker exec -it petcheck_backend python -m app.scripts.normalize_au_mobile_numbers
```

## Screenshots

Screenshots should live in the repository root under:

- `pet_check_screenshots/`

That location is already correct in your project.

### Login and Create User

![Login Page](pet_check_screenshots/login_page.png)
![Create User](pet_check_screenshots/create_user.png)

### Owner Experience

![Owner Dashboard With Due Dates](pet_check_screenshots/owner_dashboard_with_due_dates.png)
![Owner Dashboard With Scores](pet_check_screenshots/owner_dashboard_with_scores.png)
![Owner Add Pet](pet_check_screenshots/user_add_pet.png)

### Vet and Admin Experience

![Vet Page](pet_check_screenshots/vet_page_example.png)
![Vet Dashboard v2](pet_check_screenshots/vet_dashboard_v2.png)
![Vet Clinic Page](pet_check_screenshots/vet_clinic_page.png)
![Vet Owner Overview](pet_check_screenshots/vet_owner_overview.png)
![Vet Pet Lookup](pet_check_screenshots/vet_pet_lookup.png)
![Vet Staff Page](pet_check_screenshots/vet_staff_page.png)
![Admin Page](pet_check_screenshots/admin_page_example.png)
![Admin Dashboard](pet_check_screenshots/admin_dashboard.png)
![Admin Dashboard v2](pet_check_screenshots/admin_dashboard_v2.png)
![Admin Analytics](pet_check_screenshots/admin_analyics_page.png)
![Admin Analytics Updated](pet_check_screenshots/pet_protect_admin_analytics.png)

### Visits and Scheduling

![Initial Vet Visits Page](pet_check_screenshots/inital_vet_visits_page.png)

## Troubleshooting

### CSV not appearing locally after seed

Ensure backend has bind mount in `docker-compose.yml`:

```yaml
backend:
  volumes:
    - ./backend:/app
```

Then rerun seed.

### Roles in UI not matching DB

- Rebuild backend container.
- Clear browser auth cache (`access_token`, `auth_user`).
- Log in again and inspect `/api/v1/auth/login` response.

### Image upload errors

- Confirm `python-multipart` is installed (included in `backend/requirements.txt`).
- Ensure image is `jpg/jpeg/png` and within size limit.

## License

Copyright (c) 2026 Daniel Broadby
All rights reserved.
