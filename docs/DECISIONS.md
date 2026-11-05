# Decisions

Every non-obvious choice and the reason for it. Newest thinking is grouped by topic, not by date.

## Project setup

- **Source files were named `README.md.txt` and `data_dictionary.md.txt`** on disk. They are stored in
  `backend/data/` as `README.md` and `data_dictionary.md`, the names the brief uses. Content is unchanged.
- **Dependencies are pinned to exact versions.** `model.joblib` is only safe to load with the scikit-learn
  version that trained it, and the commit-before-response guarantee relies on a specific FastAPI feature.

## Build order

- **The persistence gate needed some API before "the API" phase.** The brief says to run `persistence_check` before
  building the API, but that script drives the server over HTTP. So phase 3 includes the storage layer plus the thin
  routes the gate and the storage tests need (login, create, update, delete, status, history, get by id). Phase 4 adds
  everything else. All logic was already in `services/`, so this adds very little code.
- **Update and delete routes beyond the brief's list.** Section 4 lists no `PATCH` for jobs or candidates, but section 3
  requires versioned updates and prediction refresh when skills or experience change, so `PATCH /api/jobs/{id}` and
  `PATCH /api/candidates/{id}` were added. Section 3 wins if the two conflict.

## Storage

- **`Depends(get_db, scope="function")` instead of a plain `yield` dependency.** Since FastAPI 0.118, the code after
  `yield` runs after the response is sent by default. A client could be told 201 and the commit could then fail, which
  directly breaks the durability guarantee. `scope="function"` runs it before the response.
  `test_failed_commit_returns_an_error_instead_of_success` proves it.
- **`PRAGMA synchronous=FULL` in addition to the three required pragmas.** WAL's commonly recommended `NORMAL` can lose
  the most recent commits on power failure. Commits are slightly slower, which suits a low-traffic recruiter tool.
- **No "does it exist?" check before inserting an application.** A check-then-insert has a race window. The insert goes
  straight to the database, and the unique constraint decides which of two simultaneous requests wins.
- **SQLAlchemy's `version_id_col` for optimistic locking.** Every UPDATE gets `WHERE version = ?`. `assert_version`
  catches a client holding an old copy, and the WHERE clause catches two requests that passed that check together.
- **`mark_row_changed` forces the parent's UPDATE when anything changes.** Skills live in other tables, so editing only
  skills would otherwise not touch the parent row or bump its version, and a concurrent edit could overwrite it. Setting
  `updated_at` alone was not enough. The test suite caught this: Windows' clock can return the same time twice, so the
  value didn't change and SQLAlchemy skipped the UPDATE. `flag_modified` makes it unconditional.
- **pysqlite's default transaction behaviour is kept.** It starts a transaction at the first write, not the first read.
  So a request's first write waits on `busy_timeout` instead of failing, because it never has to upgrade a stale read
  snapshot to a write lock. The cost is that reads before the first write aren't in the transaction, which is why
  anything decided on those reads is re-checked (`version`, unique constraints, the parent re-read below).
- **Parents are re-read after inserting an application.** A candidate could be soft-deleted between the 404 check and
  the insert. Re-reading with the write lock held (`FOR UPDATE` on PostgreSQL) closes that window, and delete queries
  for child applications only after flushing its own write, so neither side can miss the other.
- **`ON CONFLICT DO NOTHING` for new skills rather than a SAVEPOINT retry.** Two requests can add the same new skill at
  once. SAVEPOINTs are unreliable under pysqlite's default transaction handling, and this needs no retry loop.
- **Soft-deleted rows keep their unique values.** A deleted candidate's email can't be reused, and a deleted application
  can't be re-created for the same pair. Both return a 409 that says why. The alternative (partial unique indexes) would
  allow two rows for the same person, and the brief asks for a plain `UNIQUE` constraint. There is no restore endpoint
  yet, so bringing one back currently needs a database change.
- **Deleting a candidate or job also soft-deletes its applications**, each with its own audit row. Otherwise the
  applications table would show rows pointing at records that no longer appear anywhere. `check_db` treats any such row
  as a problem.
- **DELETE takes an optional `?version=`.** The brief specifies plain DELETE routes. An optional version keeps them
  working as specified, and lets the UI also refuse to delete a record that changed since it was loaded.
- **Audit rows cover jobs, candidates and applications, not predictions.** Predictions are derived values with their own
  `model_version` and `computed_at`. Auditing them would add a row per rescore, and it would break "one audit row per
  write" from the recruiter's point of view. Skill changes are recorded in the parent's before and after snapshots.
- **Seeded rows have audit rows with `user_id` null,** meaning "the system", so the history is complete from the start.
- **An update that changes nothing writes nothing:** no version bump, no audit row, no history row.
- **Automatic backups are named `app-auto-*` and are the only ones pruned.** The last 10 are kept. Manual (`app-*`) and
  pre-restore (`app-prerestore-*`) backups are never deleted automatically, because a recruiter's deliberate backup
  shouldn't disappear after ten restarts.
- **Restore detects "in use" by leaving WAL mode.** `BEGIN EXCLUSIVE` isn't enough, because in WAL mode an idle server
  holds no lock and the test would pass with the server running. Changing journal mode needs sole access to the file.
- **A failed migration relies on the startup backup.** SQLite with pysqlite doesn't reliably run DDL in a transaction,
  which is why the backup happens before migrations.

## Predictions

- **Stale predictions are recomputed eagerly at startup, not lazily on read.** Reads stay read-only, and every row is
  current before the first request. The cost is a slower startup after a retrain, about a second for 500 rows.
- **`model_version` is a hash of the training data and parameters,** not a timestamp, so retraining the same thing keeps
  the version and doesn't trigger a pointless rescore of every row.
- **With no model loaded, the API returns null for every prediction, even when one is stored,** as the brief asks.
  Stored rows stay, unless the inputs change while the model is missing. Those rows are removed, because they would be
  wrong, and startup recomputes them once the model is back.
- **Top features are computed on read, not stored.** They aren't in the required schema, and stored predictions are
  already refreshed whenever the inputs change, so the two can't disagree.
- **Replacement contributions for the random forest.** See `docs/MODEL_REPORT.md`.
- **The model report is generated from the artifacts.** `scripts/build_report.py` fills
  `scripts/model_report_template.md` from `metrics.json` and `error_analysis.json`, and a test fails if the committed
  report or README results are out of date. Numbers can't drift, and sentences that depend on a result, such as how the
  model compares with the baseline, are worked out from it.
- **`GET /api/model/errors` includes the true label of test-set mistakes.** `match_label` otherwise stays out of the
  portal. This is the one deliberate exception: it needs a login, covers only held-out test applications, and has no
  names or emails. Nothing in training reads the error analysis, so it can't leak into the model.

## Frontend

- **Node support is split: 18+ to run the app, 22.12+ for its tests.** The brief asks for Node 18+, and `vite` 6 supports
  it. A production build was verified on Node 18.20. But every Vitest release that runs on Node 18 has a critical
  `npm audit` finding, and the fixed releases need Node 22.12+. Clean audits seemed worth asking a little more of whoever
  runs the frontend tests, since the app itself still runs on Node 18.
- **React Router 7 rather than 6.** Version 6 has an open-redirect advisory fixed only in 7. Version 7 still supports
  React 18, and the migration was a one-line change. Its package declares Node 20+, but it runs in the browser, and the
  Node 18 build still works.
- **Every successful write refreshes all queries.** It is less efficient than targeted invalidation, but a status change
  affects the table, the job's counts and the candidate's page, and at this scale correctness matters far more.
- **The status dropdown isn't optimistic.** It shows what the server last confirmed, so a failed update can't leave a
  status on screen that was never saved.
- **Forms remount on a new `version`.** Using `key={job.version}` is the simplest way to guarantee that a form can't keep
  showing values older than the record it would overwrite. The cost is that a stale update discards what was typed, and
  the message asks the recruiter to review.
- **Tooltips use the `title` attribute.** It's plain and accessible enough for the hover text the brief asks for, and it
  needs no extra library.
- **The metrics page shows the confusion matrix as a table, not the PNG.** The numbers are readable and accessible, and
  the API doesn't need to serve image files. The PNG stays in `artifacts/` and in the model report.

## Decision threshold

- **The threshold is checked on training data, and moved only on clear evidence.** `select_threshold` in
  `scripts/train.py` finds the threshold with the highest mean F1 across out-of-fold predictions from grouped CV on
  training candidates, and adopts it only if it beats 0.5 by at least 0.01. That rule was fixed before seeing any result.
  The test set plays no part.
- **The decision and its reason are recorded, not retyped.** See `threshold_selection` in `backend/artifacts/metrics.json`
  and the "Decision threshold" section of `docs/MODEL_REPORT.md`, which is generated from it. The result is also shown in
  the details section of the Model page.
- **The minimum gain exists because the check flatters itself.** The best threshold is picked and scored on the same
  predictions, so a tiny gain is expected even from noise.
- **`model_version` now includes the threshold.** Stored predictions are recomputed only when the version changes, so
  without this a new threshold would leave old labels in the database. Including it changed the version once, with no
  change to the model or its scores.

## Data added for the glass redesign

The redesigned screens needed data the API didn't return. Everything below is read-only and additive: existing fields,
routes and defaults behave as before, and storage, models and migrations are untouched. All of it is tested in
`backend/tests/test_design_data.py`.

- **`GET /api/applications/summary`** returns `{total, applied, shortlisted, rejected}` for the status filter chips. It
  takes the list's `job_id`, `search` and `prediction` filters, but not `status`, so each chip shows how many rows
  clicking it would give.
- **`prediction` filter on `GET /api/applications`.** The design has a Prediction filter, and filtering in the browser
  would only cover the current page. Leaving the parameter out gives the same results as before.
- **`GET /api/stats`** returns job, candidate and application totals for the login page. It's public because that page
  is shown before login, and it exposes only counts. `/api/health` was left alone, because its job is reporting health.
- **New fields on application rows:** `candidate_email`, `candidate_experience_years`, `required_matched` and
  `required_total`. They come from relationships that the list already loads, so they add no per-row queries.
- **New fields on application detail:** the required and preferred skills split into matched and missing, other
  candidate skills, the job minimum, the experience gap, the profile summary and `imported_from_dataset`. The last one
  lets the timeline say a record came from the dataset rather than from a recruiter.
- **`application_count` on candidates.** It comes from one grouped query, the same way jobs get their counts.
- **Application search still covers name, email and job title.** The design's placeholder says "name, email or skill",
  but adding skills would change what an existing search returns, so the placeholder describes what search really does.

## Glass redesign

- **Some colours are lighter than the design's, to reach 4.5:1 contrast.** The design's text colours measure as low as
  1.7:1 where glass sits over the bright blobs. Darkening the glass enough to fix that flattened the look, so the blobs
  keep their specified size and opacity on desktop, and the fix goes on the text instead: `--muted`, `--faint`, `--ok`
  and `--info` are lighter, with new `--accent-text` and `--bad-text`. Thin dark layers (`--glass-under`, `--pill-under`)
  sit under the glass and tinted pills. The blue blob also moved 70px left, off the page titles. All of this is in
  `src/styles/tokens.css` with a comment on each change. Contrast was measured against rendered pixels, not calculated
  from the token values, because blur and blobs change what's behind the text.
- **Blobs are smaller on phones.** At their desktop size they cover a whole 390px screen, leaving nowhere calm for text.
- **Status pills are real `<select>` elements.** The select sits invisibly on top of the styled pill, so keyboard, screen
  reader and touch behaviour all come from the browser, and there's no custom dropdown to maintain.
- **Application details moved from a modal to a page**, at `/applications/:id`, so they can be linked to and refreshed.
  The breadcrumb returns to the filtered list you came from.
- **Delete isn't in the design, but stays available.** Soft delete is a required feature, so it sits as a quiet button at
  the bottom of the Set status card.
- **Cross-validation and training data stay on the Model page, collapsed.** The design leaves them out, but they were
  already there and they're part of being honest about the model.
- **Twenty-five rows per page, as before.** The design's mock-up shows 8, but that would mean more clicking for no gain.
- **A 409 for a soft-deleted application keeps the server's wording.** The design's banner offers to open the existing
  application, and a deleted one can't be opened.

## Testing

- **`TEST_DATABASE_URL` lets the API tests run on PostgreSQL.** The concurrency and constraint tests behave differently
  across engines, so they were run on both. The default stays SQLite so tests need no setup.
