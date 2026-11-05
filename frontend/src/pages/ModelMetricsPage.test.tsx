import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import type { ClassificationResult, ModelMetrics } from "../api/types";
import { jsonResponse, mockFetch, renderWithProviders } from "../test/helpers";
import { ModelMetricsPage } from "./ModelMetricsPage";

function result(overrides: Partial<ClassificationResult> = {}): ClassificationResult {
  return {
    precision: 0.5,
    recall: 0.6,
    f1: 0.7,
    confusion_matrix: { tp: 20, fn: 5, fp: 15, tn: 60 },
    ...overrides,
  };
}

function makeMetrics(test: ModelMetrics["test"]): ModelMetrics {
  return {
    model_name: "logistic_regression",
    model_version: "v123",
    trained_at: "2026-03-09T00:00:00Z",
    decision_threshold: 0.5,
    threshold_selection: {
      method: "Out-of-fold predictions",
      default_threshold: 0.5,
      minimum_gain: 0.01,
      best_threshold: 0.47,
      best_mean_cv_f1: 0.71,
      default_mean_cv_f1: 0.705,
      gain: 0.005,
      adopted: false,
      selected_threshold: 0.5,
      reason: "The best threshold beat 0.5 by too little.",
    },
    dataset: {
      train_applications: 300,
      test_applications: 100,
      train_candidates: 150,
      test_candidates: 40,
      train_positive_rate: 0.3,
      test_positive_rate: 0.25,
      train_match_rate_with_all_required: 0.8,
      train_match_rate_without_all_required: 0.2,
    },
    baseline: { rule: "rule", threshold: 2 / 3, reason: "reason", train_f1: 0.7 },
    cross_validation: {
      method: "StratifiedGroupKFold",
      scoring: "f1",
      best_by_model: {},
      results: { logistic_regression: [{ params: { C: 1 }, mean_f1: 0.7, std_f1: 0.02 }] },
      best_model_summary: {
        logistic_regression: {
          f1: { mean: 0.712, std: 0.021 },
          precision: { mean: 0.633, std: 0.044 },
          recall: { mean: 0.845, std: 0.055 },
        },
      },
    },
    feature_importance: {
      method: "Permutation importance",
      scoring: "Drop in F1",
      features: [
        { feature: "required_overlap_ratio", mean: 0.211, std: 0.031 },
        { feature: "extra_skill_count", mean: -0.004, std: 0.008 },
      ],
    },
    chosen_model: { name: "logistic_regression", params: { C: 1 }, mean_cv_f1: 0.7 },
    test,
    precision_recall_curve: {
      average_precision: 0.777,
      points: [
        { threshold: 0.2, precision: 0.5, recall: 1 },
        { threshold: 0.5, precision: 0.8, recall: 0.5 },
        { threshold: null, precision: 1, recall: 0 },
      ],
    },
  };
}

describe("ModelMetricsPage", () => {
  // The chart library is loaded lazily, and compiling it from cold takes seconds. Without this,
  // whichever test happens to trigger it can pass the time limit on a fresh install, as in CI.
  beforeAll(async () => {
    await import("../components/ModelCharts");
  }, 60_000);

  it("takes every number from the API, with none hard-coded", async () => {
    const model = result({ precision: 0.8, recall: 0.5, f1: 0.61, confusion_matrix: { tp: 20, fn: 5, fp: 15, tn: 60 } });
    const baseline = result({ precision: 0.75, recall: 0.5, f1: 0.65, confusion_matrix: { tp: 20, fn: 5, fp: 18, tn: 57 } });
    mockFetch(() => jsonResponse(makeMetrics({ baseline, model })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByRole("region", { name: "Precision" })).toHaveTextContent("0.800Baseline 0.750 +0.050");
    expect(screen.getByRole("region", { name: "Recall" })).toHaveTextContent("0.500Baseline 0.500 ±0");
    expect(within(screen.getByRole("region", { name: "F1 score" })).getByText("−0.040")).toHaveClass("text-warn");

    expect(screen.getByText(/Logistic Regression · trained 9 Mar 2026 · tested once on 100 applications from 40 unseen candidates/)).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText("75")).toBeInTheDocument();
    expect(screen.getByText("≥ 2/3 required skills")).toBeInTheDocument();
  });

  it("colours correct cells and errors differently in the confusion matrix", async () => {
    mockFetch(() => jsonResponse(makeMetrics({ baseline: result(), model: result() })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByText("Correct catches")).toBeInTheDocument();
    expect(screen.getByText("Correct catches").closest(".matrix-cell")).toHaveClass("matrix-cell-ok");
    expect(screen.getByText("False alarms", { selector: "p" }).closest(".matrix-cell")).toHaveClass("matrix-cell-bad");
    expect(screen.getByText("True positives")).toBeInTheDocument();
  });

  it("builds the plain-language notes from the metrics", async () => {
    const model = result({ precision: 0.737, recall: 0.933, f1: 0.8, confusion_matrix: { tp: 28, fn: 2, fp: 10, tn: 60 } });
    const baseline = result({ f1: 0.79, confusion_matrix: { tp: 28, fn: 2, fp: 11, tn: 59 } });
    mockFetch(() => jsonResponse(makeMetrics({ baseline, model })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByText(/The model wins by one fewer false alarm\./)).toBeInTheDocument();
    expect(screen.getByText(/Accuracy \(88%\) is not the headline/)).toHaveTextContent("would still score 70%.");
    expect(screen.getByText(/Recall \(0\.933\) is higher than precision \(0\.737\)/)).toHaveTextContent("chosen on F1, not tuned for recall");
    expect(screen.queryByText(/Recall is favoured/)).not.toBeInTheDocument();
    expect(screen.getByText("Small synthetic data. Not validated for real hiring.")).toBeInTheDocument();
  });

  it("doesn't claim a win when the model is worse than the rule", async () => {
    const model = result({ f1: 0.6, confusion_matrix: { tp: 20, fn: 10, fp: 20, tn: 50 } });
    const baseline = result({ f1: 0.7, confusion_matrix: { tp: 25, fn: 5, fp: 10, tn: 60 } });
    mockFetch(() => jsonResponse(makeMetrics({ baseline, model })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByText(/The model doesn't beat the rule on this test set\./)).toBeInTheDocument();
    expect(screen.queryByText(/higher than precision \(0\.500\)/)).toBeInTheDocument();
    expect(screen.queryByText(/The model wins/)).not.toBeInTheDocument();
  });

  it("keeps the cross-validation results available, with the threshold decision", async () => {
    mockFetch(() => jsonResponse(makeMetrics({ baseline: result(), model: result() })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByText("Cross-validation and training data")).toBeInTheDocument();
    expect(screen.getByText("The best threshold beat 0.5 by too little.")).toBeInTheDocument();
    expect(screen.getByText("C=1")).toBeInTheDocument();
  });

  it("shows cross-validation as mean and standard deviation", async () => {
    mockFetch(() => jsonResponse(makeMetrics({ baseline: result(), model: result() })));
    renderWithProviders(<ModelMetricsPage />);

    const row = await screen.findByRole("region", { name: "Cross-validation" });
    expect(row).toHaveTextContent("0.712 \u00B1 0.021");
    expect(row).toHaveTextContent("0.633 \u00B1 0.044");
    expect(row).toHaveTextContent("0.845 \u00B1 0.055");
  });

  it("describes both charts, and gives importance plain labels and a table", async () => {
    mockFetch(() => jsonResponse(makeMetrics({ baseline: result({ precision: 0.8, recall: 0.5 }), model: result({ precision: 0.8, recall: 0.5 }) })));
    renderWithProviders(<ModelMetricsPage />);

    const curve = await screen.findByRole("img", { name: /Precision-recall curve/ });
    expect(curve).toHaveAccessibleName(expect.stringContaining("threshold 0.5"));
    expect(screen.getByText(/Average precision/)).toHaveTextContent("0.777");
    expect(screen.getByRole("img", { name: /Feature importance/ })).toBeInTheDocument();
    expect(screen.getByText("Required skills matched")).toBeInTheDocument();
    expect(screen.getByText("0.211 \u00B1 0.031")).toHaveClass("num");
  });

  it("shows an error with a retry when metrics are missing", async () => {
    mockFetch(() => jsonResponse({ detail: "No metrics found.", code: "METRICS_UNAVAILABLE" }, 404));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No metrics found.");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
