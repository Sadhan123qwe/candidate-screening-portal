import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
    },
    chosen_model: { name: "logistic_regression", params: { C: 1 }, mean_cv_f1: 0.7 },
    test,
  };
}

describe("ModelMetricsPage", () => {
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
    const model = result({ f1: 0.8, confusion_matrix: { tp: 28, fn: 2, fp: 10, tn: 60 } });
    const baseline = result({ f1: 0.79, confusion_matrix: { tp: 28, fn: 2, fp: 11, tn: 59 } });
    mockFetch(() => jsonResponse(makeMetrics({ baseline, model })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByText(/The model wins by one fewer false alarm\./)).toBeInTheDocument();
    expect(screen.getByText(/Accuracy \(88%\) is not the headline/)).toHaveTextContent("would still score 70%.");
    expect(screen.getByText("Small synthetic data. Not validated for real hiring.")).toBeInTheDocument();
  });

  it("doesn't claim a win when the model is worse than the rule", async () => {
    const model = result({ f1: 0.6, confusion_matrix: { tp: 20, fn: 10, fp: 20, tn: 50 } });
    const baseline = result({ f1: 0.7, confusion_matrix: { tp: 25, fn: 5, fp: 10, tn: 60 } });
    mockFetch(() => jsonResponse(makeMetrics({ baseline, model })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByText(/The model doesn't beat the rule on this test set\./)).toBeInTheDocument();
    expect(screen.queryByText(/The model wins/)).not.toBeInTheDocument();
  });

  it("keeps the cross-validation results available", async () => {
    mockFetch(() => jsonResponse(makeMetrics({ baseline: result(), model: result() })));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByText("Cross-validation and training data")).toBeInTheDocument();
    expect(screen.getByText("C=1")).toBeInTheDocument();
  });

  it("shows an error with a retry when metrics are missing", async () => {
    mockFetch(() => jsonResponse({ detail: "No metrics found.", code: "METRICS_UNAVAILABLE" }, 404));
    renderWithProviders(<ModelMetricsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No metrics found.");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
