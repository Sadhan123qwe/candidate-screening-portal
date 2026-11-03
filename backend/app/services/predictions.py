"""Keeps stored predictions in step with the data they were computed from.

Predictions never touch application status. Only a recruiter's PATCH changes that.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ml import predictor as predictor_module
from app.ml.features import build_features
from app.models import Application, Prediction, utcnow


def features_for(application: Application) -> dict[str, float]:
    candidate, job = application.candidate, application.job
    return build_features(
        candidate.skill_names,
        candidate.experience_years,
        job.required_skill_names,
        job.preferred_skill_names,
        job.min_experience_years,
    )


def refresh_predictions(db: Session, applications: list[Application]) -> None:
    """Recompute and store predictions inside the caller's transaction."""
    predictor = predictor_module.get_predictor()

    if not predictor.available:
        # The inputs just changed and can't be rescored, so an old score would now be
        # wrong. Removing it lets startup compute a fresh one when the model returns.
        for application in applications:
            application.prediction = None
        return

    scores = predictor.score_many([features_for(application) for application in applications])
    for application, score in zip(applications, scores):
        if application.prediction is None:
            application.prediction = Prediction(
                label=score.label,
                probability=score.probability,
                model_version=predictor.model_version,
            )
        else:
            application.prediction.label = score.label
            application.prediction.probability = score.probability
            application.prediction.model_version = predictor.model_version
            application.prediction.computed_at = utcnow()
    db.flush()


def refresh_stale_predictions(db: Session) -> int:
    """Fill in missing predictions and those made by a different model version.

    Runs at startup rather than on read, so GET requests never write to the
    database and every row is current before the first request arrives.
    """
    predictor = predictor_module.get_predictor()
    if not predictor.available:
        return 0

    stale = db.scalars(
        select(Application)
        .outerjoin(Application.prediction)
        .where(
            Application.deleted_at.is_(None),
            or_(Prediction.id.is_(None), Prediction.model_version != predictor.model_version),
        )
    ).all()
    refresh_predictions(db, list(stale))
    return len(stale)
