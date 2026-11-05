import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ModelMetrics, PrecisionRecallPoint } from "../api/types";
import { formatFeatureName } from "../lib/format";
import { GlassCard } from "./ui/GlassCard";

// Chart colours can't come from Tailwind classes, because recharts draws to SVG attributes.
// The deeper end of the primary button gradient, which clears the chart colour checks.
const SERIES = "#6c8bff";
const OPERATING_POINT = "var(--ink)";
const GRID = "rgba(255, 255, 255, 0.1)";
const AXIS_TEXT = { fill: "var(--muted)", fontSize: 12 };
const NUMBER_TEXT = { ...AXIS_TEXT, fontFamily: "var(--font-mono)" };
const axisLabel = (value: string, position: "insideBottom" | "insideLeft") => ({
  value,
  position,
  fill: "var(--muted)",
  fontSize: 12,
  ...(position === "insideLeft" ? { angle: -90, style: { textAnchor: "middle" as const } } : { offset: -2 }),
});

function ChartCard({ title, label, note, children }: { title: string; label: string; note: ReactNode; children: ReactNode }) {
  return (
    <GlassCard as="section" className="min-w-0">
      <h2 className="card-title">{title}</h2>
      <div role="img" aria-label={label} className="chart-box">
        {children}
      </div>
      <p className="mt-2 text-[13px] text-muted">{note}</p>
    </GlassCard>
  );
}

function CurveTooltip({ active, payload }: { active?: boolean; payload?: { payload: PrecisionRecallPoint }[] }) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="chart-tooltip">
      {point.threshold !== null && (
        <p>
          Threshold <span className="num">{point.threshold.toFixed(2)}</span>
        </p>
      )}
      <p>
        Precision <span className="num">{point.precision.toFixed(3)}</span>
      </p>
      <p>
        Recall <span className="num">{point.recall.toFixed(3)}</span>
      </p>
    </div>
  );
}

function ImportanceTooltip({ active, payload }: { active?: boolean; payload?: { payload: { label: string; mean: number; std: number } }[] }) {
  const item = payload?.[0]?.payload;
  if (!active || !item) return null;
  return (
    <div className="chart-tooltip">
      <p className="font-medium">{item.label}</p>
      <p>
        F1 drop{" "}
        <span className="num">
          {item.mean.toFixed(3)} &plusmn; {item.std.toFixed(3)}
        </span>
      </p>
    </div>
  );
}

function PrecisionRecallChart({ metrics }: { metrics: ModelMetrics }) {
  const { points, average_precision: averagePrecision } = metrics.precision_recall_curve;
  const { precision, recall } = metrics.test.model;
  const threshold = metrics.decision_threshold;
  // recharts joins points in array order, so they run from the lowest recall to the highest.
  const ordered = [...points].sort((a, b) => a.recall - b.recall || b.precision - a.precision);

  return (
    <ChartCard
      title="Precision-recall curve"
      label={`Precision-recall curve on the test set. The operating point at threshold ${threshold} has precision ${precision.toFixed(3)} and recall ${recall.toFixed(3)}.`}
      note={
        <>
          Test set, from the single final evaluation. Average precision{" "}
          <span className="num">{averagePrecision.toFixed(3)}</span>. The dot is the threshold in use,{" "}
          <span className="num">{threshold}</span>.
        </>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={ordered} margin={{ top: 8, right: 16, bottom: 14, left: 2 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            type="number"
            dataKey="recall"
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tick={NUMBER_TEXT}
            stroke={GRID}
            tickLine={false}
            label={axisLabel("Recall", "insideBottom")}
          />
          <YAxis
            type="number"
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tick={NUMBER_TEXT}
            stroke={GRID}
            tickLine={false}
            width={48}
            label={axisLabel("Precision", "insideLeft")}
          />
          <Tooltip content={<CurveTooltip />} cursor={{ stroke: "var(--line-strong)" }} />
          <Line dataKey="precision" type="stepAfter" stroke={SERIES} strokeWidth={2} dot={false} isAnimationActive={false} />
          <ReferenceDot
            x={recall}
            y={precision}
            r={6}
            fill={OPERATING_POINT}
            stroke="#161b2e"
            strokeWidth={2}
            label={{ value: `Threshold ${threshold}`, position: "left", fill: "var(--ink)", fontSize: 12, offset: 12, dy: 20 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function ImportanceChart({ metrics }: { metrics: ModelMetrics }) {
  const features = metrics.feature_importance.features.map((item) => ({ ...item, label: formatFeatureName(item.feature) }));
  const top = features[0];

  return (
    <ChartCard
      title="Feature importance"
      label={`Feature importance by permutation on held-out training folds. The most important feature is ${top.label}, with an F1 drop of ${top.mean.toFixed(3)}. A table of every value is in the section below.`}
      note="How far F1 falls when one feature is shuffled, on held-out training folds. Features that overlap can hide each other's effect."
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={features} layout="vertical" margin={{ top: 0, right: 16, bottom: 14, left: 0 }} barCategoryGap={6}>
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis type="number" tick={NUMBER_TEXT} stroke={GRID} tickLine={false} tickFormatter={(value: number) => value.toFixed(2)} label={axisLabel("Drop in F1", "insideBottom")} />
          <YAxis type="category" dataKey="label" width={168} interval={0} tick={AXIS_TEXT} stroke={GRID} tickLine={false} />
          <ReferenceLine x={0} stroke="var(--line-strong)" />
          <Tooltip content={<ImportanceTooltip />} cursor={{ fill: "rgba(255, 255, 255, 0.06)" }} />
          <Bar dataKey="mean" fill={SERIES} maxBarSize={18} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default function ModelCharts({ metrics }: { metrics: ModelMetrics }) {
  return (
    <div className="charts-grid">
      <PrecisionRecallChart metrics={metrics} />
      <ImportanceChart metrics={metrics} />
    </div>
  );
}
