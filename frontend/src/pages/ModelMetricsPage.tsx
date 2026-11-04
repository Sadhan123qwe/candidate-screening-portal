import { useModelMetrics } from "../api/model";
import type { ClassificationResult, ModelMetrics } from "../api/types";
import { QueryBoundary } from "../components/QueryBoundary";
import { GlassCard } from "../components/ui/GlassCard";
import { PageHeader } from "../components/ui/PageHeader";
import { formatDate, formatDateTime, formatPercent } from "../lib/format";

const titleCase = (name: string) => name.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const score = (value: number) => value.toFixed(3);
const SAME_SCORE = 0.0005;

/** 0.6667 becomes "2/3", which reads better than a long decimal. */
function asFraction(value: number): string {
  for (let denominator = 1; denominator <= 10; denominator += 1) {
    const numerator = Math.round(value * denominator);
    if (Math.abs(value - numerator / denominator) < 0.001) return `${numerator}/${denominator}`;
  }
  return value.toFixed(2);
}

function countOf(count: number, one: string, many: string): string {
  return `${count === 1 ? "one" : count} ${count === 1 ? one : many}`;
}

/** Built from the results, so the wording stays true after a retrain. */
function comparisonSentence(baseline: ClassificationResult, model: ClassificationResult): string {
  const fewerAlarms = baseline.confusion_matrix.fp - model.confusion_matrix.fp;
  const fewerMisses = baseline.confusion_matrix.fn - model.confusion_matrix.fn;
  const parts: string[] = [];
  if (fewerAlarms > 0) parts.push(`${countOf(fewerAlarms, "fewer false alarm", "fewer false alarms")}`);
  if (fewerMisses > 0) parts.push(`${countOf(fewerMisses, "fewer missed match", "fewer missed matches")}`);

  if (fewerAlarms >= 0 && fewerMisses >= 0 && parts.length > 0) return `The model wins by ${parts.join(" and ")}.`;
  if (fewerAlarms === 0 && fewerMisses === 0) return "The model and the rule make the same errors.";
  if (model.f1 > baseline.f1) return "The model scores slightly higher overall, but makes more of one kind of error.";
  return "The model doesn't beat the rule on this test set.";
}

export function ModelMetricsPage() {
  const metrics = useModelMetrics();
  return <QueryBoundary query={metrics}>{(data) => <MetricsContent metrics={data} />}</QueryBoundary>;
}

function MetricsContent({ metrics }: { metrics: ModelMetrics }) {
  const { baseline, model } = metrics.test;
  const { tp, fn, fp, tn } = model.confusion_matrix;
  const realMatches = tp + fn;
  const notMatches = fp + tn;
  const total = realMatches + notMatches;
  const modelName = titleCase(metrics.model_name);

  return (
    <div>
      <PageHeader
        title="Model"
        subtitle={`${modelName} · trained ${formatDate(metrics.trained_at)} · tested once on ${metrics.dataset.test_applications} applications from ${metrics.dataset.test_candidates} unseen candidates`}
        aside={
          <p className="test-set-pill">
            Test set: <span className="num">{realMatches}</span> real matches &middot; <span className="num">{notMatches}</span> not
          </p>
        }
      />

      <div className="metric-grid">
        <MetricCard label="Precision" value={model.precision} baseline={baseline.precision} />
        <MetricCard label="Recall" value={model.recall} baseline={baseline.recall} />
        <MetricCard label="F1 score" value={model.f1} baseline={baseline.f1} />
      </div>

      <div className="model-grid">
        <ConfusionMatrix result={model} />

        <div className="model-side">
          <GlassCard as="section" padding="none" aria-label="Baseline compared with the model" className="overflow-hidden">
            <div className="table-scroll">
              <table className="data-table min-w-[440px]">
                <thead>
                  <tr>
                    <th scope="col">Approach</th>
                    <th scope="col">Precision</th>
                    <th scope="col">Recall</th>
                    <th scope="col">F1</th>
                    <th scope="col">False alarms</th>
                  </tr>
                </thead>
                <tbody>
                  <ResultRow
                    label="Baseline"
                    note={`≥ ${asFraction(metrics.baseline.threshold)} required skills`}
                    result={baseline}
                    isBestF1={baseline.f1 > model.f1}
                  />
                  <ResultRow label={modelName} result={model} isBestF1={model.f1 > baseline.f1} />
                </tbody>
              </table>
            </div>
          </GlassCard>

          <GlassCard as="section">
            <h2 className="card-title">What to know</h2>
            <div className="what-to-know">
              <p>The labels mostly follow required-skill coverage, so a simple rule is already strong. {comparisonSentence(baseline, model)}</p>
              <p>Recall is favoured: a missed candidate costs more than a quick extra look.</p>
              <p>
                Accuracy ({formatPercent((tp + tn) / total)}) is not the headline: saying "Needs Review" to everyone would still score{" "}
                {formatPercent(notMatches / total)}.
              </p>
              <p className="text-muted">Small synthetic data. Not validated for real hiring.</p>
            </div>
          </GlassCard>
        </div>
      </div>

      <MoreDetail metrics={metrics} />
    </div>
  );
}

function MetricCard({ label, value, baseline }: { label: string; value: number; baseline: number }) {
  const difference = value - baseline;
  const isSame = Math.abs(difference) < SAME_SCORE;
  const shownDifference = isSame ? "±0" : `${difference > 0 ? "+" : "−"}${Math.abs(difference).toFixed(3)}`;

  return (
    <GlassCard as="section" aria-label={label}>
      <h2 className="eyebrow">{label}</h2>
      <p className="metric-value">{score(value)}</p>
      <p className="text-muted">
        Baseline <span className="num">{score(baseline)}</span>{" "}
        <span className={`num ${difference < 0 && !isSame ? "text-warn" : "text-ok"}`}>{shownDifference}</span>
      </p>
    </GlassCard>
  );
}

function ResultRow({ label, note, result, isBestF1 }: { label: string; note?: string; result: ClassificationResult; isBestF1: boolean }) {
  return (
    <tr>
      <td>
        <span className="cell-title">{label}</span>
        {note && <span className="cell-sub">{note}</span>}
      </td>
      <td className="num">{score(result.precision)}</td>
      <td className="num">{score(result.recall)}</td>
      <td className={`num ${isBestF1 ? "text-ok" : ""}`}>{score(result.f1)}</td>
      <td className="num">{result.confusion_matrix.fp}</td>
    </tr>
  );
}

function MatrixCell({ value, label, technical, correct }: { value: number; label: string; technical: string; correct: boolean }) {
  return (
    <td>
      <div className={`matrix-cell ${correct ? "matrix-cell-ok" : "matrix-cell-bad"}`}>
        <p className={`matrix-value ${correct ? "text-ok" : "text-bad"}`}>{value}</p>
        <p className="mt-1 font-medium">{label}</p>
        <p className="text-muted">{technical}</p>
      </div>
    </td>
  );
}

function ConfusionMatrix({ result }: { result: ClassificationResult }) {
  const { tn, fp, fn, tp } = result.confusion_matrix;
  return (
    <GlassCard as="section" className="min-w-0">
      <h2 className="card-title">Confusion matrix</h2>
      <div className="matrix-scroll">
        <table className="matrix">
          <caption className="sr-only">The model's predictions compared with the real labels on the test set</caption>
          <thead>
            <tr>
              <td className="matrix-corner" />
              <th scope="col" className="eyebrow">
                Model: match
              </th>
              <th scope="col" className="eyebrow">
                Model: needs review
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" className="eyebrow">
                Real match
              </th>
              <MatrixCell value={tp} label="Correct catches" technical="True positives" correct />
              <MatrixCell value={fn} label="Missed" technical="False negatives" correct={false} />
            </tr>
            <tr>
              <th scope="row" className="eyebrow">
                Not a match
              </th>
              <MatrixCell value={fp} label="False alarms" technical="False positives" correct={false} />
              <MatrixCell value={tn} label="Correctly passed" technical="True negatives" correct />
            </tr>
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}

/** Everything the page showed before the redesign, kept one click away. */
function MoreDetail({ metrics }: { metrics: ModelMetrics }) {
  return (
    <GlassCard as="details" padding="none" className="more-detail">
      <summary>Cross-validation and training data</summary>
      <div className="space-y-4 px-[22px] pb-[22px]">
        <p className="text-muted">
          Version <span className="num">{metrics.model_version}</span>, trained {formatDateTime(metrics.trained_at)}. Decision threshold{" "}
          <span className="num">{metrics.decision_threshold}</span>. {metrics.cross_validation.method}.
        </p>
        <div className="table-scroll">
          <table className="data-table min-w-[560px]">
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col">Parameters</th>
                <th scope="col">Mean F1</th>
                <th scope="col">Std</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics.cross_validation.results).flatMap(([name, results]) =>
                results.map((result) => {
                  const parameters = Object.entries(result.params)
                    .map(([key, value]) => `${key}=${value}`)
                    .join(", ");
                  return (
                    <tr key={`${name}-${parameters}`}>
                      <td>{titleCase(name)}</td>
                      <td className="num">{parameters}</td>
                      <td className="num">{score(result.mean_f1)}</td>
                      <td className="num">{score(result.std_f1)}</td>
                    </tr>
                  );
                }),
              )}
            </tbody>
          </table>
        </div>
        <ul className="list-inside list-disc space-y-1 text-muted">
          <li>
            <span className="num">{metrics.dataset.train_applications}</span> training and <span className="num">{metrics.dataset.test_applications}</span> test
            applications, from <span className="num">{metrics.dataset.train_candidates}</span> and <span className="num">{metrics.dataset.test_candidates}</span>{" "}
            separate candidates.
          </li>
          <li>
            <span className="num">{formatPercent(metrics.dataset.train_positive_rate)}</span> of training labels are "Potential Match", so F1 is reported rather
            than accuracy.
          </li>
          <li>
            Training candidates with every required skill match <span className="num">{formatPercent(metrics.dataset.train_match_rate_with_all_required)}</span>{" "}
            of the time, and others <span className="num">{formatPercent(metrics.dataset.train_match_rate_without_all_required)}</span>.
          </li>
        </ul>
      </div>
    </GlassCard>
  );
}
