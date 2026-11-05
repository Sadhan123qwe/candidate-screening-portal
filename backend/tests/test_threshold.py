"""The decision threshold: selected from training data only, and actually used when serving."""

import json

import numpy as np
import pytest

from app.config import get_settings
from app.ml.features import FEATURE_NAMES
from app.ml.predictor import Predictor
from app.models import PredictionLabel
from scripts.train import DEFAULT_THRESHOLD, MIN_THRESHOLD_GAIN, build_model_version, select_threshold


def _folds_where_low_threshold_wins():
    # Every real match scores 0.4, above every non-match, so only a threshold under 0.5 finds them.
    labels = np.array([1, 1, 1, 0, 0, 0])
    probabilities = np.array([0.4, 0.4, 0.4, 0.1, 0.1, 0.1])
    return [(labels, probabilities)] * 5


def _folds_where_default_is_best():
    labels = np.array([1, 1, 1, 0, 0, 0])
    probabilities = np.array([0.9, 0.9, 0.9, 0.1, 0.1, 0.1])
    return [(labels, probabilities)] * 5


def test_a_clear_gain_is_adopted():
    decision = select_threshold(_folds_where_low_threshold_wins())

    assert decision["adopted"] is True
    assert decision["selected_threshold"] == decision["best_threshold"] < DEFAULT_THRESHOLD
    assert decision["gain"] >= MIN_THRESHOLD_GAIN


def test_no_gain_keeps_the_default():
    decision = select_threshold(_folds_where_default_is_best())

    assert decision["adopted"] is False
    assert decision["selected_threshold"] == DEFAULT_THRESHOLD
    assert str(DEFAULT_THRESHOLD) in decision["reason"]


def test_a_gain_below_the_minimum_keeps_the_default():
    # One of many positives is rescued below 0.5, a real gain but far below the required minimum.
    labels = np.array([1] * 200 + [0] * 200)
    probabilities = np.array([0.9] * 199 + [0.45] + [0.1] * 200)

    decision = select_threshold([(labels, probabilities)])

    assert 0 < decision["gain"] < MIN_THRESHOLD_GAIN
    assert decision["adopted"] is False
    assert decision["selected_threshold"] == DEFAULT_THRESHOLD


def test_a_different_threshold_gives_a_different_model_version():
    # Stored labels are recomputed only when the version changes.
    params = {"n_estimators": 300}
    assert build_model_version(params, "random_forest", 0.5) != build_model_version(params, "random_forest", 0.4)
    assert build_model_version(params, "random_forest", 0.5) == build_model_version(params, "random_forest", 0.5)


def test_saved_metrics_record_the_decision():
    metrics = json.loads(get_settings().metrics_path.read_text(encoding="utf-8"))
    decision = metrics["threshold_selection"]

    assert metrics["decision_threshold"] == decision["selected_threshold"]
    assert decision["adopted"] == (decision["gain"] >= decision["minimum_gain"])
    assert "training candidates only" in decision["method"]
    assert decision["reason"]


class _FixedPipeline:
    """Always gives the same probability, so only the threshold decides the label."""

    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, frame):
        return np.array([[1 - self.probability, self.probability]] * len(frame))


@pytest.mark.parametrize(
    ("threshold", "expected"),
    [(0.4, PredictionLabel.POTENTIAL_MATCH), (0.5, PredictionLabel.POTENTIAL_MATCH), (0.6, PredictionLabel.NEEDS_REVIEW)],
)
def test_predictor_uses_the_stored_threshold(threshold, expected):
    predictor = Predictor(
        {"pipeline": _FixedPipeline(0.5), "threshold": threshold, "feature_names": FEATURE_NAMES, "model_version": "test"}
    )

    score = predictor.score_many([dict.fromkeys(FEATURE_NAMES, 0.0)])[0]

    assert score.label == expected.value
