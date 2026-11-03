# Candidate Screening & Application Management Portal

A recruiter portal for managing jobs, candidates and applications, with an integrated ML model that suggests which
applications look like a potential match. Built as a take-home assignment for Rock One Solutions.

The model only ever suggests. An application's status changes only when a recruiter changes it.

All data is synthetic. The dataset is in `backend/data/`, and its own rules are in `backend/data/README.md`.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18, Vite, TypeScript, React Router, TanStack Query, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| Database | SQLAlchemy 2.0 ORM, Alembic migrations, SQLite by default, PostgreSQL by changing `DATABASE_URL` |
| Auth | JWT bearer tokens (PyJWT), passwords hashed with bcrypt |
| ML | pandas, scikit-learn, joblib |
| Tests | pytest and FastAPI TestClient, Vitest and React Testing Library |

## Architecture

```mermaid
flowchart LR
    Browser["React app<br/>TanStack Query"] -->|"JSON + JWT"| Routers

    subgraph Backend["FastAPI backend"]
        Routers["routers/<br/>thin HTTP layer"] --> Services["services/<br/>business logic"]
        Services --> Predictor["ml/predictor.py"]
        Predictor --> Features["ml/features.py"]
    end

    Services -->|"one transaction per request"| DB[("SQLite or PostgreSQL")]
    Artifact["artifacts/model.joblib"] -->|"loaded once"| Predictor

    subgraph Offline["Offline, run by hand"]
        Train["scripts/train.py"] --> Features
        Train --> Artifact
        Seed["scripts/seed.py"] --> DB
    end
```

More detail is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and the reasoning behind every non-obvious choice is in
[docs/DECISIONS.md](docs/DECISIONS.md).

## Prerequisites

- Python 3.11+
- Node 18+ to build and run the frontend. The frontend **tests** need Node 22.12+, because the Vitest version that has
  no known vulnerabilities requires it.

## Setup (PowerShell)

```powershell
cd backend; python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt; copy .env.example .env
alembic upgrade head; python -m scripts.train; python -m scripts.seed
uvicorn app.main:app --reload
```

Leave that running. Open a second terminal in `backend\` and run:

```powershell
cd ..\frontend; npm install; npm run dev
```

Then open <http://localhost:5173>.

`python -m scripts.train` is optional, because the trained model is committed in `backend/artifacts/`. Retraining gives
the same `model_version` and the same scores.

### If your machine restricts PowerShell scripts

`Activate.ps1` and `npm.ps1` are scripts, so some policies block them. You don't need to change a policy:

- Skip activation and call the virtual environment directly, for example
  `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
  Use `.venv\Scripts\python.exe -m alembic upgrade head` for migrations.
- Use `npm.cmd` in place of `npm`.

## Demo login

| Email | Password |
|---|---|
| `recruiter@demo.com` | `Demo@12345` |

## Running the tests

```powershell
# Backend, from backend\ with the virtual environment active
pytest -q

# Frontend, from frontend\
npm test
```

Backend tests use a temporary SQLite file with real migrations applied, so they never touch `storage/app.db`. To run the
API tests on PostgreSQL, set `$env:TEST_DATABASE_URL` to an empty database.

## How persistence works

- **Where the data lives:** `backend/storage/app.db`, set by `DATABASE_URL` in `backend/.env`. A relative path is always
  resolved from `backend/`, so starting the server from another folder can't create a second database. The folder is
  created automatically if it's missing.
- **Migrations:** the schema is managed only by Alembic, and `create_all` is never used. The server also runs
  `alembic upgrade head` on startup, after taking a backup.
- **Backups:** every server start takes an automatic backup into `storage/backups/` and keeps the last 10. Manual and
  pre-restore backups are never deleted automatically.

| Task | Command (from `backend\`) |
|---|---|
| Take a backup (safe while the server runs) | `python -m scripts.backup_db` |
| Restore a backup (stop the server first) | `python -m scripts.restore_db storage\backups\app-20260101-120000.db` |
| Check database health | `python -m scripts.check_db` |
| Prove data survives a crash | `python -m scripts.persistence_check` |

**To reset everything:** stop the server, then run:

```powershell
Remove-Item storage\app.db*
alembic upgrade head; python -m scripts.seed
```

### Using PostgreSQL

No code changes are needed:

```powershell
docker compose up -d
$env:DATABASE_URL = "postgresql+psycopg://portal:portal@localhost:5432/portal"
cd backend; alembic upgrade head; python -m scripts.seed; uvicorn app.main:app --reload
```

Data stays in a named Docker volume across `docker compose down` and `up`. The backup and restore scripts are for SQLite
only and say so on PostgreSQL, where you would use `pg_dump`.

## Data storage & reliability

The rule: nothing a recruiter enters is ever lost, silently overwritten, duplicated or half-saved.

| # | Guarantee | How it's enforced | Tested by |
|---|---|---|---|
| 1 | **Durable.** A successful write is on disk before the response is sent. | The session dependency uses `scope="function"`, so the commit runs before the response. `PRAGMA synchronous=FULL` syncs each commit to disk. | `test_failed_commit_returns_an_error_instead_of_success`, `test_data_survives_disposing_the_engine`, `scripts/persistence_check.py` |
| 2 | **Atomic.** Each request saves everything or nothing. | One session per request, committed on success and rolled back on any exception. | `test_atomicity.py`, `test_failed_seed_leaves_database_untouched` |
| 3 | **No duplicates.** | `UNIQUE` constraints in the database, with no check-then-insert in app code. `IntegrityError` becomes a 409. | `test_duplicates.py`, `test_concurrency.py` |
| 4 | **No lost updates.** | `version` columns with SQLAlchemy's `version_id_col`, so every UPDATE includes `WHERE version = ?`. An old version gets 409 `STALE_UPDATE`. | `test_stale_update.py`, `test_two_simultaneous_status_updates_cannot_both_win`, `ApplicationsPage.test.tsx` |
| 5 | **No hard deletes.** | `deleted_at` on jobs, candidates and applications. The API has no way to remove a row. | `test_soft_delete.py` |
| 6 | **Full history.** | One `audit_log` row per write, in the same transaction, plus `status_history` for the timeline. | `test_audit.py`, `test_status.py` |
| 7 | **Recoverable.** | Automatic backup on every start, before migrations. Manual backup and restore scripts use SQLite's online backup API. | `test_backup_restore.py` |
| 8 | **Verifiable.** | `check_db` runs `integrity_check` and `foreign_key_check`, counts rows, and reports orphans and missing predictions. It exits non-zero on any problem. | Run after every seed and at the end of the test suite. `tests/conftest.py` fails the suite if the checks don't pass. |
| 9 | **Times in UTC.** | `UTCDateTime` refuses naive datetimes and always returns aware UTC. The server sets all times, and request models reject unknown fields. | `test_timestamps_are_timezone_aware_utc`, `test_client_cannot_set_timestamps` |

## API overview

Every route except login and health needs a `Authorization: Bearer <token>` header. Interactive docs are at
<http://localhost:8000/docs> while the server is running.

| Method and path | Purpose |
|---|---|
| `POST /api/auth/login` | Get a token |
| `GET /api/auth/me` | Current user |
| `GET /api/health` | Database reachable, model loaded, model version |
| `GET, POST /api/jobs` | List or create jobs |
| `GET, PATCH, DELETE /api/jobs/{id}` | Read (with counts by status), update or soft-delete a job |
| `GET, POST /api/candidates` | List (`?search=` on name, email or skill) or create candidates |
| `GET, PATCH, DELETE /api/candidates/{id}` | Read (with applications), update or soft-delete a candidate |
| `GET, POST /api/applications` | Paginated list (`job_id`, `status`, `search`, `page`, `page_size`) or create. A duplicate returns 409 |
| `GET, DELETE /api/applications/{id}` | Read (with prediction and top features) or soft-delete |
| `PATCH /api/applications/{id}/status` | Change status. Requires `version` |
| `GET /api/applications/{id}/history` | Status timeline |
| `GET /api/model/metrics` | Saved training and evaluation results |

Errors always look like `{"detail": "...", "code": "DUPLICATE_APPLICATION"}`. Validation errors also include `errors`, a
list of `{field, message}`.

Updates (`PATCH`) must send the `version` they read. Deletes accept an optional `?version=`.

## Model results

| Test set, class 1 | Precision | Recall | F1 |
|---|---|---|---|
| Baseline (`required_overlap_ratio >= 0.667`) | 0.718 | 0.933 | 0.812 |
| Random Forest | 0.737 | 0.933 | 0.824 |

The model beats a one-line rule by a single application out of 100, which isn't a meaningful difference. The labels are
mostly driven by skill coverage, so a simple rule already captures most of the signal. The full results and limitations
are in [docs/MODEL_REPORT.md](docs/MODEL_REPORT.md).

## Assumptions

- There is one role, recruiter, and any recruiter can edit any record.
- Soft-deleted rows keep their unique values, so a deleted candidate's email can't be reused. No restore endpoint exists
  yet.
- Deleting a candidate or job also soft-deletes its applications.
- Job and candidate lists aren't paginated, because the brief specifies only search and the data is small. The
  applications list is paginated.
- The server runs as a single process when using SQLite, because startup backup and migration aren't coordinated
  across workers.
