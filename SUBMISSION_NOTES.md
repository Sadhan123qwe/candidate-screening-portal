# Submission notes

## Time spent

| Part | Hours |
|---|---|
| ML and model report | _to fill in_ |
| Storage and backend | _to fill in_ |
| Frontend | _to fill in_ |
| Documentation and review | _to fill in_ |
| **Total** | _to fill in_ |

## Completed

- Machine learning: shared feature function, baseline, grouped cross-validation, one final test evaluation, model report
- Storage: all nine guarantees in the README, each backed by code and tests
- Migrations, idempotent seed, backup, restore, `check_db` and `persistence_check`
- PostgreSQL option through `docker-compose.yml`, verified on PostgreSQL 16
- Full REST API with validation, consistent errors and JWT authentication
- All frontend pages, with loading, error and empty states and stale-update handling
- Backend and frontend test suites, and documentation
- Glass redesign of every screen, with contrast measured on the rendered pages
- Error analysis of every test-set mistake, saved by training and served by `GET /api/model/errors`
- GitHub Actions CI for the backend and frontend, rehearsed in a clean clone but not yet run on GitHub
- Cross-validation mean and spread for each model, a test-set precision-recall curve, and permutation feature importance
  on held-out training folds, all shown on the Model page
- A decision-threshold check on out-of-fold training predictions, with the decision and reason recorded
- A model report and README results generated from the training artifacts, with a test that catches drift
- Server-side sorting of applications, CSV export of the filtered list, and status and Potential Match counts per job
- A verified Quick start, screenshots of the running app, and a "What I'd do next" list

## Not done

Nothing from the final polish round was reverted or left out.

## Incomplete or limited

- No endpoint to restore a soft-deleted record. It currently needs a database change.
- Job and candidate lists aren't paginated, which is fine at this data size but wouldn't scale.
- There is one recruiter role, with no per-user permissions.
- Login has no rate limiting.
- Frontend automated tests cover login, applications, application detail, jobs, candidates and the model page. The job
  and candidate detail pages have no automated tests of their own. Every screen was also checked by driving the app in a
  browser, using a throwaway script that isn't part of this repo.
- Only the API-level tests were run on PostgreSQL. The file-based tests for backup, restore and seeding are SQLite-only.

## AI tools and external code

- **Claude Code** (Anthropic) was used to build this project, including code, tests and documentation.
- No code was copied from other projects. Open-source libraries are listed in `backend/requirements.txt` and
  `frontend/package.json`.
