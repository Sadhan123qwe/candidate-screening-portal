"""The single feature function shared by training and serving.

Training (scripts/train.py) and the live predictor both call build_features.
Keeping one implementation is what prevents training/serving skew: a feature
cannot be computed one way offline and another way in production.

Inputs are skills and experience only. IDs, names, emails, match_label, split,
recruiter status and stored predictions must never be added here.
"""

from collections.abc import Iterable

# The fixed column order. The saved model expects exactly this order, so a new
# feature means retraining rather than just editing this list.
FEATURE_NAMES: list[str] = [
    "required_overlap_ratio",
    "required_missing_count",
    "has_all_required",
    "preferred_overlap_ratio",
    "skill_jaccard",
    "extra_skill_count",
    "candidate_skill_count",
    "experience_years",
    "min_experience_years",
    "experience_gap",
    "meets_experience",
]


def build_features(
    candidate_skills: Iterable[str],
    experience_years: float,
    required_skills: Iterable[str],
    preferred_skills: Iterable[str],
    min_experience_years: float,
) -> dict[str, float]:
    """Turn one candidate-job pair into the model's numeric inputs."""
    candidate = set(candidate_skills)
    required = set(required_skills)
    preferred = set(preferred_skills)
    job_skills = required | preferred

    matched_required = candidate & required

    # A job with no requirements is fully covered by anyone, so the ratio is 1.0.
    required_ratio = len(matched_required) / len(required) if required else 1.0

    # Having no preferred skills gives no bonus evidence, so the ratio stays 0.0.
    preferred_ratio = len(candidate & preferred) / len(preferred) if preferred else 0.0

    all_skills = candidate | job_skills
    jaccard = len(candidate & job_skills) / len(all_skills) if all_skills else 0.0

    return {
        "required_overlap_ratio": required_ratio,
        "required_missing_count": float(len(required - candidate)),
        "has_all_required": float(required <= candidate),
        "preferred_overlap_ratio": preferred_ratio,
        "skill_jaccard": jaccard,
        "extra_skill_count": float(len(candidate - job_skills)),
        "candidate_skill_count": float(len(candidate)),
        "experience_years": float(experience_years),
        "min_experience_years": float(min_experience_years),
        "experience_gap": float(experience_years) - float(min_experience_years),
        "meets_experience": float(experience_years >= min_experience_years),
    }
