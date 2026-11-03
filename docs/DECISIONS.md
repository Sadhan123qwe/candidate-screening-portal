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
- **`updated_at` is set by hand when anything changes.** Skills live in other tables, so editing only skills would
  otherwise not touch the parent row or bump its version, and a concurrent edit could overwrite it.
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

## Testing

- **`TEST_DATABASE_URL` lets the API tests run on PostgreSQL.** The concurrency and constraint tests behave differently
  across engines, so they were run on both. The default stays SQLite so tests need no setup.
