# 🐾 Pet Check — Application & Database

[![Docker](https://img.shields.io/badge/Docker-Ready-informational)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-informational)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-Backend-informational)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-informational)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-informational)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-informational)](https://alembic.sqlalchemy.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-Validation-informational)](https://docs.pydantic.dev/)
[![Pytest](https://img.shields.io/badge/Pytest-Tests-informational)](https://pytest.org/)

> Pet Check is a Dockerised backend + database designed for recording and managing pet records (and related user data).  
> This repo includes a PostgreSQL schema and seed scripts to quickly populate development data.

---

## ✨ Features

- **PostgreSQL** relational database for core entities (currently `users`, `pets`)
- **Seed data** scripts for fast local development (e.g., 100 users / 200 pets)
- **Container-first** workflow using Docker Compose
- Structured backend setup (API + DB) ready for extension (auth, inspections, reports, uploads, etc.)

---

## 🧰 Tech Stack

**Languages**
- [Python](https://www.python.org/)
- [SQL](https://www.postgresql.org/docs/current/sql.html)

**Frameworks & Libraries**
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Pydantic](https://docs.pydantic.dev/)

**Platform**
- [Docker](https://www.docker.com/)
- [PostgreSQL](https://www.postgresql.org/)

---

## 🗂️ Project Structure

> Your exact folders may differ — adjust this section to match your repo layout.

```text
pet-check/
├── backend/
│ ├── app/
│ │ ├── api/ # Route definitions
│ │ ├── models/ # SQLAlchemy models
│ │ ├── scripts/ # Seed & utility scripts
│ │ ├── database.py # DB connection config
│ │ └── main.py # FastAPI entry point
│ ├── requirements.txt
│ └── Dockerfile
├── docker-compose.yml
└── README.md

**🚀 Getting Started**
Prerequisites

Docker Desktop
 installed and running

1) Start the stack

From the repo root:

docker compose up -d --build

2) Confirm containers are running
docker ps

3) Seed the database (dev data)
docker exec -it petcheck_backend python -m app.scripts.seed_data

4) Quick DB sanity check

List tables:

docker exec -it petcheck_db psql -U postgres -d pet_check -c "\dt"


Count rows:

docker exec -it petcheck_db psql -U postgres -d pet_check -c "SELECT COUNT(*) FROM users;"
docker exec -it petcheck_db psql -U postgres -d pet_check -c "SELECT COUNT(*) FROM pets;"

**🧪 Useful Database Commands**

Open an interactive psql session:

docker exec -it petcheck_db psql -U postgres -d pet_check


Inside psql, common commands:

\dt              -- list tables
\d users         -- describe table
\d pets          -- describe table
SELECT NOW();    -- quick check
\q               -- quit

🧬 ER Diagram (Mermaid)

This ERD reflects the current baseline tables (users, pets).
Update the attributes below to match your actual columns when they evolve.

erDiagram
    USERS ||--o{ PETS : owns

    USERS {
        int id PK
        string full_name
        string email
        string phone
        timestamp created_at
    }

    PETS {
        int id PK
        int user_id FK
        string name
        string species
        string breed
        date date_of_birth
        timestamp created_at
    }



**🧭 Roadmap**

Authentication + role-based access (admin/inspector/user)

Pet check history / inspections table(s)

File uploads (photos, evidence)

Reporting + export (CSV/PDF)

CI pipeline (lint + tests + build)

**📸 Screenshots**



**📝 Licence**

Copyright (c) 2026 Daniel Broadby
All rights reserved.

