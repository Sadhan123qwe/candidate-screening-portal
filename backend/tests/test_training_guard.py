"""Guards against the two classic ways to fool yourself in ML: leakage and a contaminated split."""

import pandas as pd
import pytest

from app.ml.features import FEATURE_NAMES
from app.models import Application
from scripts.train import (
    FORBIDDEN_FEATURES,
    assert_no_forbidden_features,
    assert_split_is_valid,
    load_dataset,
    to_feature_frame,
)


def test_no_forbidden_columns_among_model_inputs():
    assert not set(FEATURE_NAMES) & FORBIDDEN_FEATURES
    assert list(to_feature_frame(load_dataset()).columns) == FEATURE_NAMES


def test_forbidden_column_check_actually_catches_leaks():
    for column in ("candidate_id", "job_id", "match_label", "split", "email", "name", "status"):
        with pytest.raises(AssertionError):
            assert_no_forbidden_features(["required_overlap_ratio", column])


def test_train_and_test_candidates_are_disjoint_with_expected_sizes():
    dataset = load_dataset()
    train = dataset[dataset["split"] == "train"]
    test = dataset[dataset["split"] == "test"]

    assert not set(train["candidate_id"]) & set(test["candidate_id"])
    assert (len(train), len(test)) == (400, 100)
    assert (train["candidate_id"].nunique(), test["candidate_id"].nunique()) == (200, 50)


def test_split_check_catches_a_candidate_on_both_sides():
    dataset = load_dataset()
    contaminated: pd.DataFrame = dataset.copy()
    test_row = contaminated.index[contaminated["split"] == "test"][0]
    contaminated.loc[test_row, "candidate_id"] = contaminated.loc[
        contaminated["split"] == "train", "candidate_id"
    ].iloc[0]

    with pytest.raises(AssertionError, match="both sides"):
        assert_split_is_valid(contaminated)


def test_match_label_is_not_stored_in_the_portal_database():
    """match_label is an offline training target only."""
    assert "match_label" not in Application.__table__.columns
