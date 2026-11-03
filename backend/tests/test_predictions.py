"""Predictions are stored, stay fresh, and their absence never breaks the app."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, engine
from app.ml import predictor as predictor_module
from app.ml.features import FEATURE_NAMES, build_features
from app.ml.predictor import Predictor
from app.models import Prediction
from app.services.predictions import refresh_stale_predictions


def _stored_prediction(application_id: int) -> Prediction | None:
    with SessionLocal() as db:
        return db.scalar(select(Prediction).where(Prediction.application_id == application_id))


def _refresh_stale() -> int:
    with Session(engine) as db, db.begin():
        return refresh_stale_predictions(db)


def test_prediction_is_stored_on_application_create(make_application):
    application = make_application()

    stored = _stored_prediction(application["id"])

    assert stored is not None
    assert stored.label in ("Potential Match", "Needs Review")
    assert 0 <= stored.probability <= 1
    assert stored.model_version == predictor_module.get_predictor().model_version
    assert application["prediction"]["label"] == stored.label
    assert application["prediction"]["probability"] == stored.probability


def test_application_detail_includes_the_top_three_features(client, auth_headers, make_application):
    application = make_application()

    detail = client.get(f"/api/applications/{application['id']}", headers=auth_headers).json()

    assert len(detail["top_features"]) == 3
    assert all(item["feature"] in FEATURE_NAMES for item in detail["top_features"])
    contributions = [abs(item["contribution"]) for item in detail["top_features"]]
    assert contributions == sorted(contributions, reverse=True)


def test_changing_candidate_skills_recomputes_the_prediction(client, auth_headers, make_job, make_candidate):
    job = make_job(required_skills=["python", "sql", "docker"], preferred_skills=[], min_experience_years=0)
    candidate = make_candidate(skills=["excel"], experience_years=2)
    application = client.post(
        "/api/applications", json={"candidate_id": candidate["id"], "job_id": job["id"]}, headers=auth_headers
    ).json()
    before = _stored_prediction(application["id"])

    client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "skills": ["python", "sql", "docker"]},
        headers=auth_headers,
    )

    after = _stored_prediction(application["id"])
    assert after.probability > before.probability
    assert after.computed_at > before.computed_at


def test_changing_candidate_name_does_not_recompute(client, auth_headers, make_application):
    application = make_application()
    candidate = client.get(f"/api/candidates/{application['candidate_id']}", headers=auth_headers).json()
    before = _stored_prediction(application["id"])

    client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "name": "Only The Name Changed"},
        headers=auth_headers,
    )

    assert _stored_prediction(application["id"]).computed_at == before.computed_at


def test_changing_job_requirements_recomputes_the_prediction(client, auth_headers, make_job, make_candidate):
    job = make_job(required_skills=["python"], preferred_skills=[], min_experience_years=0)
    candidate = make_candidate(skills=["python"], experience_years=2)
    application = client.post(
        "/api/applications", json={"candidate_id": candidate["id"], "job_id": job["id"]}, headers=auth_headers
    ).json()
    before = _stored_prediction(application["id"])

    client.patch(
        f"/api/jobs/{job['id']}",
        json={"version": job["version"], "required_skills": ["rust", "go", "kotlin"], "min_experience_years": 5},
        headers=auth_headers,
    )

    after = _stored_prediction(application["id"])
    assert after.probability < before.probability
    assert after.computed_at > before.computed_at


def test_predictions_from_another_model_version_are_recomputed(make_application):
    application = make_application()
    with SessionLocal() as db, db.begin():
        stored = db.scalar(select(Prediction).where(Prediction.application_id == application["id"]))
        stored.model_version = "an-older-model"

    assert _refresh_stale() == 1
    assert _stored_prediction(application["id"]).model_version == predictor_module.get_predictor().model_version
    assert _refresh_stale() == 0


def test_with_no_model_the_application_is_created_and_prediction_is_null(
    client, auth_headers, make_job, make_candidate, model_missing
):
    body = {"candidate_id": make_candidate()["id"], "job_id": make_job()["id"]}

    created = client.post("/api/applications", json=body, headers=auth_headers)

    assert created.status_code == 201
    assert created.json()["prediction"] is None
    assert "unavailable" in created.json()["prediction_message"].lower()
    assert _stored_prediction(created.json()["id"]) is None

    detail = client.get(f"/api/applications/{created.json()['id']}", headers=auth_headers).json()
    assert detail["prediction"] is None
    assert detail["top_features"] == []

    listing = client.get("/api/applications", params={"job_id": body["job_id"]}, headers=auth_headers).json()
    assert listing["items"][0]["prediction"] is None

    # Tidy up: an active application with no prediction would fail the end-of-suite check.
    client.delete(f"/api/applications/{created.json()['id']}", headers=auth_headers)


def test_health_reports_a_missing_model_without_failing(client, model_missing):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["model_loaded"] is False
    assert response.json()["model_version"] is None


def test_prediction_is_recomputed_when_the_model_returns_after_inputs_changed(
    client, auth_headers, make_application, monkeypatch
):
    application = make_application()
    candidate = client.get(f"/api/candidates/{application['candidate_id']}", headers=auth_headers).json()

    monkeypatch.setattr(predictor_module, "_predictor", Predictor(None))
    client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "skills": ["brand-new-skill"]},
        headers=auth_headers,
    )
    # The old score no longer describes this candidate, so it must not survive.
    assert _stored_prediction(application["id"]) is None

    monkeypatch.undo()
    _refresh_stale()
    assert _stored_prediction(application["id"]) is not None


def test_predictor_reports_unavailable_for_a_missing_file(tmp_path):
    predictor = Predictor.from_file(tmp_path / "does-not-exist.joblib")
    assert predictor.available is False
    assert predictor.model_version is None


def test_predictor_reports_unavailable_for_a_damaged_file(tmp_path):
    damaged = tmp_path / "damaged.joblib"
    damaged.write_bytes(b"this is not a model")
    assert Predictor.from_file(damaged).available is False


def test_real_model_scores_a_strong_match_above_a_weak_one():
    predictor = Predictor.from_file(get_settings().artifact_path)
    strong = build_features(["python", "sql", "docker"], 3, ["python", "sql"], ["docker"], 1)
    weak = build_features(["excel"], 0, ["python", "sql"], ["docker"], 1)

    strong_score, weak_score = predictor.score_many([strong, weak])

    assert strong_score.probability > weak_score.probability
    assert strong_score.label == "Potential Match"
    assert weak_score.label == "Needs Review"


def test_logistic_regression_contributions_use_coefficient_times_scaled_value():
    """The forest was chosen on this data, but a retrain could pick logistic regression."""
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rows = [
        build_features(["python", "sql"], 2, ["python", "sql"], [], 1),
        build_features(["excel"], 0, ["python", "sql"], [], 1),
        build_features(["python"], 1, ["python", "sql"], [], 1),
        build_features(["python", "sql", "go"], 3, ["python", "sql"], [], 1),
    ]
    frame = pd.DataFrame(rows, columns=FEATURE_NAMES)
    pipeline = Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression())]).fit(frame, [1, 0, 0, 1])
    predictor = Predictor(
        {"pipeline": pipeline, "threshold": 0.5, "model_version": "test", "feature_names": FEATURE_NAMES}
    )

    top = predictor.explain(rows[0])

    scaled = pipeline.named_steps["scaler"].transform(frame.iloc[[0]])[0]
    coefficients = pipeline.named_steps["model"].coef_[0]
    expected = {name: coefficient * value for name, coefficient, value in zip(FEATURE_NAMES, coefficients, scaled)}
    assert len(top) == 3
    for item in top:
        assert abs(item.contribution - expected[item.feature]) < 1e-9
