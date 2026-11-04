import type { Prediction } from "../../api/types";
import { formatPercent } from "../../lib/format";

const UNAVAILABLE_TOOLTIP = "No prediction is available.";

interface PredictionBadgeProps {
  prediction: Prediction | null;
  message?: string | null;
  /** The detail page shows the percentage separately, in large type. */
  hidePercent?: boolean;
}

export function PredictionBadge({ prediction, message, hidePercent }: PredictionBadgeProps) {
  if (!prediction) {
    return (
      <span title={message ?? UNAVAILABLE_TOOLTIP} className="pill badge-none">
        <span aria-hidden="true" className="pill-dot" />
        Unavailable
      </span>
    );
  }

  const isMatch = prediction.label === "Potential Match";
  const percent = formatPercent(prediction.probability);
  return (
    <span title={`Probability of a match: ${percent}`} className={`pill ${isMatch ? "badge-ok" : "badge-warn"}`}>
      <span aria-hidden="true" className="pill-dot" />
      {prediction.label}
      {!hidePercent && <span className="num">{percent}</span>}
    </span>
  );
}
