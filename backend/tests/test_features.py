"""build_features gives the expected values for known inputs, including edge cases."""

import pytest

from app.ml.features import FEATURE_NAMES, build_features


def test_known_inputs_give_expected_values():
    features = build_features(
        candidate_skills=["python", "sql", "excel", "git"],
        experience_years=2,
        required_skills=["python", "sql", "docker", "aws"],
        preferred_skills=["git", "linux"],
        min_experience_years=1,
    )

    assert features == {
        "required_overlap_ratio": 0.5,  # 2 of 4
        "required_missing_count": 2,  # docker, aws
        "has_all_required": 0,
        "preferred_overlap_ratio": 0.5,  # git of git, linux
        "skill_jaccard": pytest.approx(3 / 7),  # python, sql, git of 7 distinct skills
        "extra_skill_count": 1,  # excel
        "candidate_skill_count": 4,
        "experience_years": 2,
        "min_experience_years": 1,
        "experience_gap": 1,
        "meets_experience": 1,
    }


def test_candidate_with_every_required_skill():
    features = build_features(["python", "sql"], 1, ["python", "sql"], [], 1)

    assert features["required_overlap_ratio"] == 1.0
    assert features["required_missing_count"] == 0
    assert features["has_all_required"] == 1
    assert features["meets_experience"] == 1  # Exactly the minimum counts as meeting it.
    assert features["experience_gap"] == 0


def test_job_with_no_required_skills_has_ratio_one():
    features = build_features(["python"], 0, [], ["sql"], 0)

    assert features["required_overlap_ratio"] == 1.0
    assert features["required_missing_count"] == 0
    assert features["has_all_required"] == 1


def test_job_with_no_preferred_skills_has_ratio_zero():
    assert build_features(["python"], 0, ["python"], [], 0)["preferred_overlap_ratio"] == 0.0


def test_no_skills_anywhere_does_not_divide_by_zero():
    features = build_features([], 0, [], [], 0)

    assert features["skill_jaccard"] == 0.0
    assert features["candidate_skill_count"] == 0
    assert features["extra_skill_count"] == 0


def test_under_experience_gives_a_negative_gap():
    features = build_features(["python"], 0.5, ["python"], [], 2)

    assert features["experience_gap"] == -1.5
    assert features["meets_experience"] == 0


def test_repeated_skills_are_only_counted_once():
    features = build_features(["python", "python"], 1, ["python", "python"], [], 0)

    assert features["candidate_skill_count"] == 1
    assert features["required_overlap_ratio"] == 1.0


def test_skills_are_exact_tokens_not_substrings():
    # The data dictionary calls this out: java and javascript are different skills.
    assert build_features(["javascript"], 0, ["java"], [], 0)["required_overlap_ratio"] == 0.0


def test_output_keys_match_the_fixed_column_order():
    assert list(build_features([], 0, [], [], 0)) == FEATURE_NAMES
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))
