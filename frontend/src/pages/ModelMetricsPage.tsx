import { useModelMetrics } from "../api/model";
import type { ClassificationResult, ModelMetrics } from "../api/types";
import { QueryBoundary } from "../components/QueryBoundary";
import { formatDateTime, formatPercent } from "../lib/format";

const CLOSE_CALL_ERRORS = 2;

const titleCase = (name: string) => name.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
const score = (value: number) => value.toFixed(3);

export function ModelMetricsPage() {
  const metrics = useModelMetrics();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Model metrics</h1>
      <QueryBoundary query={metrics}>{(data) => <MetricsContent metrics={data} />}</QueryBoundary>
    </div>
  );
}

function MetricsContent({ metrics }: { metrics: ModelMetrics }) {
  const { baseline, model } = metrics.test;
  const baselineErrors = baseline.confusion_matrix.fp + baseline.confusion_matrix.fn;
  const modelErrors = model.confusion_matrix.fp + model.confusion_matrix.fn;
  // Worked out from the data, so the wording stays true after a retrain.
  const isTooCloseToCall = Math.abs(baselineErrors - modelErrors) <= CLOSE_CALL_ERRORS;

  return (
    <div className="space-y-4">
      <section className="card space-y-2 p-5 text-sm text-gray-700">
        <p>
          <span className="font-medium text-gray-900">{titleCase(metrics.model_name)}</span> was selected by
          cross-validated F1 on training candidates only. On the {metrics.dataset.test_applications} test applications
          it makes {modelErrors} errors, against {baselineErrors} for a one-line skill-coverage rule.
          {isTooCloseToCall && " That difference is too small to call it better than the rule."}
        </p>
        <p>
          These labels are synthetic and noisy, so the scores measure how well an artificial pattern is recovered, not
          real suitability for a job. Predictions are suggestions and never change an application's status.
        </p>
        <p className="text-xs text-gray-500">
          Version {metrics.model_version}, trained {formatDateTime(metrics.trained_at)}. Decision threshold{" "}
          {metrics.decision_threshold}.
        </p>
      </section>

      <section className="card overflow-hidden">
        <h2 className="border-b border-gray-200 px-4 py-3 text-sm font-semibold text-gray-900">
          Test set: baseline vs. model (class 1, Potential Match)
        </h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-2">Approach</th>
                <th className="px-4 py-2 text-right">Precision</th>
                <th className="px-4 py-2 text-right">Recall</th>
                <th className="px-4 py-2 text-right">F1</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              <ResultRow label={`Baseline (ratio >= ${score(metrics.baseline.threshold)})`} result={baseline} />
              <ResultRow label={titleCase(metrics.model_name)} result={model} />
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <ConfusionMatrix title="Baseline" result={baseline} />
        <ConfusionMatrix title={titleCase(metrics.model_name)} result={model} />
      </div>

      <section className="card overflow-hidden">
        <h2 className="border-b border-gray-200 px-4 py-3 text-sm font-semibold text-gray-900">Cross-validation on training data</h2>
        <p className="px-4 pt-3 text-xs text-gray-500">{metrics.cross_validation.method}</p>
        <div className="overflow-x-auto">
          <table className="mt-2 min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-2">Model</th>
                <th className="px-4 py-2">Parameters</th>
                <th className="px-4 py-2 text-right">Mean F1</th>
                <th className="px-4 py-2 text-right">Std</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {Object.entries(metrics.cross_validation.results).flatMap(([name, results]) =>
                results.map((result) => {
                  const parameters = Object.entries(result.params).map(([key, value]) => `${key}=${value}`).join(", ");
                  return (
                    <tr key={`${name}-${parameters}`}>
                      <td className="px-4 py-1.5 text-gray-700">{titleCase(name)}</td>
                      <td className="px-4 py-1.5 text-gray-600">{parameters}</td>
                      <td className="px-4 py-1.5 text-right tabular-nums text-gray-700">{score(result.mean_f1)}</td>
                      <td className="px-4 py-1.5 text-right tabular-nums text-gray-500">{score(result.std_f1)}</td>
                    </tr>
                  );
                }),
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card p-5 text-sm text-gray-700">
        <h2 className="mb-2 font-semibold text-gray-900">Data</h2>
        <ul className="list-inside list-disc space-y-1">
          <li>
            {metrics.dataset.train_applications} training and {metrics.dataset.test_applications} test applications, from{" "}
            {metrics.dataset.train_candidates} and {metrics.dataset.test_candidates} separate candidates.
          </li>
          <li>
            {formatPercent(metrics.dataset.train_positive_rate)} of training labels are "Potential Match", so F1 is
            reported rather than accuracy.
          </li>
          <li>
            Training candidates with every required skill match {formatPercent(metrics.dataset.train_match_rate_with_all_required)} of
            the time, and others {formatPercent(metrics.dataset.train_match_rate_without_all_required)}.
          </li>
        </ul>
      </section>
    </div>
  );
}

function ResultRow({ label, result }: { label: string; result: ClassificationResult }) {
  return (
    <tr>
      <td className="px-4 py-2 text-gray-800">{label}</td>
      <td className="px-4 py-2 text-right tabular-nums text-gray-700">{score(result.precision)}</td>
      <td className="px-4 py-2 text-right tabular-nums text-gray-700">{score(result.recall)}</td>
      <td className="px-4 py-2 text-right font-medium tabular-nums text-gray-900">{score(result.f1)}</td>
    </tr>
  );
}

function ConfusionMatrix({ title, result }: { title: string; result: ClassificationResult }) {
  const { tn, fp, fn, tp } = result.confusion_matrix;
  return (
    <section className="card p-4">
      <h2 className="mb-3 text-sm font-semibold text-gray-900">Confusion matrix: {title}</h2>
      <table className="w-full text-center text-sm">
        <caption className="sr-only">Actual label by predicted label for {title}</caption>
        <thead className="text-xs text-gray-500">
          <tr>
            <td />
            <th scope="col" className="pb-2 font-medium">Predicted Needs Review</th>
            <th scope="col" className="pb-2 font-medium">Predicted Potential Match</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          <tr>
            <th scope="row" className="py-1 pr-2 text-left text-xs font-medium text-gray-500">Actual Needs Review</th>
            <td className="rounded bg-gray-50 py-3 text-lg font-semibold text-gray-900">{tn}</td>
            <td className="rounded bg-gray-50 py-3 text-lg text-gray-700">{fp}</td>
          </tr>
          <tr>
            <th scope="row" className="py-1 pr-2 text-left text-xs font-medium text-gray-500">Actual Potential Match</th>
            <td className="rounded bg-gray-50 py-3 text-lg text-gray-700">{fn}</td>
            <td className="rounded bg-gray-50 py-3 text-lg font-semibold text-gray-900">{tp}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}
