"""Loads the trained model once and turns feature rows into predictions.

A missing or unreadable model never stops the app. The predictor simply reports
itself as unavailable, and the API returns null predictions with a message.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from app.config import get_settings
from app.ml.features import FEATURE_NAMES
from app.models import PredictionLabel

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = "Prediction unavailable: the model file is missing or could not be loaded."
TOP_FEATURE_COUNT = 3


@dataclass(frozen=True)
class Score:
    label: str
    probability: float


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    value: float
    contribution: float


class Predictor:
    def __init__(self, artifact: dict | None = None):
        self._artifact = artifact

    @classmethod
    def from_file(cls, path: Path) -> "Predictor":
        if not path.exists():
            logger.warning("Model file not found at %s. Predictions will show as unavailable.", path)
            return cls(None)
        try:
            artifact = joblib.load(path)
        except Exception:  # A damaged pickle can raise almost anything; it must not stop the app.
            logger.exception("Could not load model file %s. Predictions will show as unavailable.", path)
            return cls(None)

        # The saved column order must match the code, or every score would be silently wrong.
        if artifact["feature_names"] != FEATURE_NAMES:
            logger.error("Model features do not match app/ml/features.py. Retrain with: python -m scripts.train")
            return cls(None)
        if artifact["sklearn_version"] != sklearn.__version__:
            logger.warning(
                "Model was trained with scikit-learn %s but %s is installed.",
                artifact["sklearn_version"],
                sklearn.__version__,
            )
        return cls(artifact)

    @property
    def available(self) -> bool:
        return self._artifact is not None

    @property
    def model_version(self) -> str | None:
        return self._artifact["model_version"] if self._artifact else None

    def _positive_probabilities(self, rows: list[dict[str, float]]) -> list[float]:
        frame = pd.DataFrame(rows, columns=FEATURE_NAMES)
        return self._artifact["pipeline"].predict_proba(frame)[:, 1].tolist()

    def score_many(self, rows: list[dict[str, float]]) -> list[Score]:
        """Score in one batch, which is far faster than row by row for a forest."""
        if not rows:
            return []
        threshold = self._artifact["threshold"]
        return [
            Score(
                label=(PredictionLabel.POTENTIAL_MATCH if probability >= threshold else PredictionLabel.NEEDS_REVIEW).value,
                probability=probability,
            )
            for probability in self._positive_probabilities(rows)
        ]

    def explain(self, row: dict[str, float]) -> list[FeatureContribution]:
        """Return the features that moved this particular prediction the most."""
        model = self._artifact["pipeline"].named_steps["model"]
        if hasattr(model, "coef_"):
            contributions = self._linear_contributions(row)
        else:
            contributions = self._replacement_contributions(row)
        ranked = sorted(contributions, key=lambda item: abs(item.contribution), reverse=True)
        return ranked[:TOP_FEATURE_COUNT]

    def _linear_contributions(self, row: dict[str, float]) -> list[FeatureContribution]:
        """For logistic regression: coefficient x scaled value, in log-odds."""
        pipeline = self._artifact["pipeline"]
        frame = pd.DataFrame([row], columns=FEATURE_NAMES)
        scaled = pipeline.named_steps["scaler"].transform(frame)[0]
        coefficients = pipeline.named_steps["model"].coef_[0]
        return [
            FeatureContribution(name, row[name], float(coefficient * value))
            for name, coefficient, value in zip(FEATURE_NAMES, coefficients, scaled)
        ]

    def _replacement_contributions(self, row: dict[str, float]) -> list[FeatureContribution]:
        """For forests: how far the probability moves if a feature becomes average.

        Global feature importance would show the same list for every candidate,
        which says nothing about why this particular application scored as it did.
        """
        means = self._artifact["feature_means"]
        variants = [{**row, name: means[name]} for name in FEATURE_NAMES]
        probabilities = self._positive_probabilities([row, *variants])
        base, without_feature = probabilities[0], probabilities[1:]
        return [
            FeatureContribution(name, row[name], base - replaced)
            for name, replaced in zip(FEATURE_NAMES, without_feature)
        ]


_predictor: Predictor | None = None


def get_predictor() -> Predictor:
    """Load the artifact on first use and share it, since unpickling is slow."""
    global _predictor
    if _predictor is None:
        _predictor = Predictor.from_file(get_settings().artifact_path)
    return _predictor
