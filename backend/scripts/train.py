"""Offline training and evaluation. Run from backend/: python -m scripts.train

The order below matters. Everything up to `evaluate_on_test` uses training
candidates only, so the test score is an honest estimate of unseen candidates.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # Draw to a file; a training script should not need a display.

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sklearn  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support  # noqa: E402
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app.ml.features import FEATURE_NAMES, build_features  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"

RANDOM_STATE = 42
# The brief fixes the operating point. Tuning it per job would need more data than we have.
DECISION_THRESHOLD = 0.5
EXPECTED_TRAIN_ROWS = 400
EXPECTED_TEST_ROWS = 100

# Columns that may never become model inputs. tests/test_training_guard.py checks this.
FORBIDDEN_FEATURES = {
    "application_id",
    "candidate_id",
    "job_id",
    "name",
    "email",
    "match_label",
    "split",
    "status",
    "prediction",
    "probability",
}


def load_dataset() -> pd.DataFrame:
    """Join the fixed split on candidate_id and refuse to continue if it leaks."""
    applications = pd.read_csv(DATA_DIR / "ml_dataset.csv")
    split = pd.read_csv(DATA_DIR / "candidate_split.csv")

    # many_to_one fails loudly if a candidate were listed in the split file twice.
    dataset = applications.merge(split, on="candidate_id", how="left", validate="many_to_one")
    assert dataset["split"].notna().all(), "Every application needs a split"
    assert_split_is_valid(dataset)
    return dataset


def assert_split_is_valid(dataset: pd.DataFrame) -> None:
    train = dataset[dataset["split"] == "train"]
    test = dataset[dataset["split"] == "test"]
    overlap = set(train["candidate_id"]) & set(test["candidate_id"])
    assert not overlap, f"Candidates on both sides of the split: {sorted(overlap)}"
    assert len(train) == EXPECTED_TRAIN_ROWS, f"Expected {EXPECTED_TRAIN_ROWS} train rows, got {len(train)}"
    assert len(test) == EXPECTED_TEST_ROWS, f"Expected {EXPECTED_TEST_ROWS} test rows, got {len(test)}"


def assert_no_forbidden_features(columns: list[str]) -> None:
    leaked = set(columns) & FORBIDDEN_FEATURES
    assert not leaked, f"Forbidden columns among model inputs: {sorted(leaked)}"


def split_skills(value: str) -> list[str]:
    return [skill for skill in str(value).split(";") if skill]


def to_feature_frame(dataset: pd.DataFrame) -> pd.DataFrame:
    """Build the model inputs through the same function the API uses."""
    rows = [
        build_features(
            split_skills(row.candidate_skills),
            row.experience_years,
            split_skills(row.required_skills),
            split_skills(row.preferred_skills),
            row.minimum_experience_years,
        )
        for row in dataset.itertuples()
    ]
    features = pd.DataFrame(rows, columns=FEATURE_NAMES)
    assert_no_forbidden_features(list(features.columns))
    return features


def choose_baseline_threshold(ratios: pd.Series, labels: pd.Series) -> dict:
    """Pick t for 'predict 1 if required_overlap_ratio >= t' using training data only."""
    scores = [
        {"threshold": float(t), "f1": float(f1_score(labels, ratios >= t, zero_division=0))}
        for t in sorted(ratios.unique())
    ]
    # max() keeps the first of any tie, which is the lowest threshold.
    best = max(scores, key=lambda score: score["f1"])
    return {"threshold": best["threshold"], "train_f1": best["f1"], "all_thresholds": scores}


def tune_candidate_models(X: pd.DataFrame, y: pd.Series, groups: pd.Series) -> dict[str, GridSearchCV]:
    """Run grouped cross-validation for both model families on training data."""
    # Grouping by candidate stops one person's two applications from sitting on
    # both sides of a fold, which would flatter the CV score.
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    searches = {
        "logistic_regression": GridSearchCV(
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", LogisticRegression(class_weight="balanced", max_iter=2000)),
                ]
            ),
            {"model__C": [0.01, 0.1, 1, 10]},
            scoring="f1",
            cv=cv,
        ),
        "random_forest": GridSearchCV(
            Pipeline(
                [
                    (
                        "model",
                        RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE),
                    )
                ]
            ),
            {"model__n_estimators": [100, 300], "model__min_samples_leaf": [1, 5, 10]},
            scoring="f1",
            cv=cv,
        ),
    }
    for name, search in searches.items():
        print(f"Cross-validating {name}...")
        search.fit(X, y, groups=groups)
    return searches


def summarize_cv(search: GridSearchCV) -> list[dict]:
    results = search.cv_results_
    return [
        {
            "params": {key.replace("model__", ""): value for key, value in params.items()},
            "mean_f1": float(mean),
            "std_f1": float(std),
        }
        for params, mean, std in zip(results["params"], results["mean_test_score"], results["std_test_score"])
    ]


def classification_summary(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=1, zero_division=0
    )
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def build_error_analysis(test_rows: pd.DataFrame, X_test: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> dict:
    """Describe every test-set mistake, for the report. Nothing in training reads this file.

    Names, emails and candidate ids are deliberately left out.
    """
    titles = pd.read_csv(DATA_DIR / "jobs.csv").set_index("job_id")["title"]
    errors = []
    for position, row in enumerate(test_rows.itertuples()):
        probability = float(probabilities[position])
        predicted = int(probability >= threshold)
        if predicted == row.match_label:
            continue
        required = split_skills(row.required_skills)
        candidate_skills = set(split_skills(row.candidate_skills))
        features = X_test.iloc[position]
        errors.append(
            {
                "application_id": row.application_id,
                "error_type": "false_positive" if predicted == 1 else "false_negative",
                "job_title": str(titles[row.job_id]),
                "required_overlap_ratio": float(features["required_overlap_ratio"]),
                "required_skills_total": len(required),
                "missing_required_skills": [skill for skill in required if skill not in candidate_skills],
                "experience_years": float(row.experience_years),
                "minimum_experience_years": float(row.minimum_experience_years),
                "meets_experience": bool(features["meets_experience"]),
                "predicted_probability": probability,
                "true_label": int(row.match_label),
            }
        )
    errors.sort(key=lambda error: (error["error_type"], -error["predicted_probability"], error["application_id"]))
    return {"decision_threshold": threshold, "test_applications": len(test_rows), "errors": errors}


def build_model_version(params: dict, model_name: str) -> str:
    """A hash of data + parameters: retraining the same thing gives the same version.

    Stored predictions are only recomputed when the version changes, so a
    timestamp would trigger needless recomputation after an identical retrain.
    """
    digest = hashlib.sha256()
    for filename in ("ml_dataset.csv", "candidate_split.csv"):
        # Line endings are normalised so a Windows checkout hashes the same as Linux.
        digest.update((DATA_DIR / filename).read_bytes().replace(b"\r\n", b"\n"))
    digest.update(json.dumps({"model": model_name, "params": params, "features": FEATURE_NAMES}, sort_keys=True).encode())
    return digest.hexdigest()[:12]


def logistic_coefficients(pipeline: Pipeline) -> dict[str, float] | None:
    model = pipeline.named_steps["model"]
    if not hasattr(model, "coef_"):
        return None
    return {name: float(coef) for name, coef in zip(FEATURE_NAMES, model.coef_[0])}


def draw_confusion_matrices(baseline: dict, model: dict, model_name: str, path: Path) -> None:
    """Side-by-side counts on one shared single-hue scale, so the panels compare directly."""
    panels = [("Baseline", baseline["confusion_matrix"]), (model_name.replace("_", " ").title(), model["confusion_matrix"])]
    matrices = [np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]]) for _, m in panels]
    top = max(matrix.max() for matrix in matrices)
    ink, muted = "#1f2933", "#52606d"

    figure, axes = plt.subplots(1, 2, figsize=(8, 3.8), layout="constrained")
    for axis, (title, _), matrix in zip(axes, panels, matrices):
        axis.imshow(matrix, cmap="Blues", vmin=0, vmax=top)
        axis.set_title(title, color=ink, fontsize=12, loc="left")
        axis.set_xticks([0, 1], ["Needs Review", "Potential Match"], color=muted, fontsize=9)
        axis.set_yticks([0, 1], ["Needs Review", "Potential Match"], color=muted, fontsize=9, rotation=90, va="center")
        axis.set_xlabel("Predicted", color=muted, fontsize=9)
        axis.set_ylabel("Actual", color=muted, fontsize=9)
        axis.tick_params(length=0)
        for spine in axis.spines.values():
            spine.set_visible(False)
        for (row, column), count in np.ndenumerate(matrix):
            # Dark cells get white text so every count stays readable.
            axis.text(
                column, row, str(count), ha="center", va="center", fontsize=15,
                color="white" if count > top * 0.55 else ink,
            )
    figure.suptitle("Test set confusion matrix (100 applications)", color=ink, fontsize=13, x=0.02, ha="left")
    figure.savefig(path, dpi=150, facecolor="white")
    plt.close(figure)


def train() -> dict:
    dataset = load_dataset()
    features = to_feature_frame(dataset)
    labels = dataset["match_label"]

    is_train = dataset["split"] == "train"
    X_train, y_train = features[is_train], labels[is_train]
    X_test, y_test = features[~is_train], labels[~is_train]
    groups_train = dataset.loc[is_train, "candidate_id"]

    # --- Everything in this block sees training candidates only. ---
    baseline = choose_baseline_threshold(X_train["required_overlap_ratio"], y_train)
    searches = tune_candidate_models(X_train, y_train, groups_train)
    chosen_name = max(searches, key=lambda name: searches[name].best_score_)
    chosen = searches[chosen_name]
    # GridSearchCV has already refit the best parameters on the full training set.
    pipeline = chosen.best_estimator_
    chosen_params = {key.replace("model__", ""): value for key, value in chosen.best_params_.items()}
    has_all_required = X_train["has_all_required"] == 1

    # --- The approach is final. The test set is used once, below. ---
    test_probabilities = pipeline.predict_proba(X_test)[:, 1]
    model_predictions = (test_probabilities >= DECISION_THRESHOLD).astype(int)
    baseline_predictions = (X_test["required_overlap_ratio"] >= baseline["threshold"]).astype(int).to_numpy()
    model_metrics = classification_summary(y_test, model_predictions)
    baseline_metrics = classification_summary(y_test, baseline_predictions)
    error_analysis = build_error_analysis(dataset[~is_train], X_test, test_probabilities, DECISION_THRESHOLD)

    model_version = build_model_version(chosen_params, chosen_name)
    trained_at = datetime.now(timezone.utc).isoformat()

    metrics = {
        "model_name": chosen_name,
        "model_version": model_version,
        "trained_at": trained_at,
        "decision_threshold": DECISION_THRESHOLD,
        "dataset": {
            "train_applications": len(X_train),
            "test_applications": len(X_test),
            "train_candidates": int(groups_train.nunique()),
            "test_candidates": int(dataset.loc[~is_train, "candidate_id"].nunique()),
            "train_positive_rate": float(y_train.mean()),
            "test_positive_rate": float(y_test.mean()),
            "train_match_rate_with_all_required": float(y_train[has_all_required].mean()),
            "train_match_rate_without_all_required": float(y_train[~has_all_required].mean()),
        },
        "baseline": {
            "rule": "predict 1 if required_overlap_ratio >= threshold",
            "threshold": baseline["threshold"],
            "reason": "Highest F1 on the training set among the distinct ratio values; test labels were not used.",
            "train_f1": baseline["train_f1"],
            "train_thresholds": baseline["all_thresholds"],
        },
        "cross_validation": {
            "method": "StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42), grouped by candidate_id",
            "scoring": "F1 for class 1",
            "best_by_model": {name: float(search.best_score_) for name, search in searches.items()},
            "results": {name: summarize_cv(search) for name, search in searches.items()},
        },
        "chosen_model": {"name": chosen_name, "params": chosen_params, "mean_cv_f1": float(chosen.best_score_)},
        "test": {"baseline": baseline_metrics, "model": model_metrics},
        "logistic_coefficients": logistic_coefficients(pipeline),
    }

    ARTIFACTS_DIR.mkdir(exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "feature_names": FEATURE_NAMES,
            "threshold": DECISION_THRESHOLD,
            "model_name": chosen_name,
            "model_version": model_version,
            "sklearn_version": sklearn.__version__,
            "trained_at": trained_at,
            # A random forest has no per-row coefficients, so the predictor explains
            # a score by swapping each feature for its training average.
            "feature_means": {name: float(X_train[name].mean()) for name in FEATURE_NAMES},
        },
        ARTIFACTS_DIR / "model.joblib",
    )
    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (ARTIFACTS_DIR / "error_analysis.json").write_text(json.dumps(error_analysis, indent=2), encoding="utf-8")
    draw_confusion_matrices(baseline_metrics, model_metrics, chosen_name, ARTIFACTS_DIR / "confusion_matrix.png")
    return metrics


def main() -> None:
    metrics = train()
    print(f"Chosen model: {metrics['model_name']} {metrics['chosen_model']['params']}")
    print(f"Mean CV F1:   {metrics['chosen_model']['mean_cv_f1']:.3f}")
    for name in ("baseline", "model"):
        result = metrics["test"][name]
        print(f"Test {name:9s} precision={result['precision']:.3f} recall={result['recall']:.3f} f1={result['f1']:.3f}")
    print(f"Artifacts written to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
