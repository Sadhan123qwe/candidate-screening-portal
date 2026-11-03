import type { Prediction } from "../api/types";
import { formatPercent } from "../lib/format";

const UNAVAILABLE_TOOLTIP = "No prediction is available.";

interface PredictionBadgeProps {
  prediction: Prediction | null;
  message?: string | null;
}

export function PredictionBadge({ prediction, message }: PredictionBadgeProps) {
  if (!prediction) {
    return (
      <span title={message ?? UNAVAILABLE_TOOLTIP} className="inline-block rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
        Unavailable
      </span>
    );
  }

  const isMatch = prediction.label === "Potential Match";
  const colors = isMatch ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800";
  return (
    <span
      title={`Probability of a match: ${formatPercent(prediction.probability)}`}
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${colors}`}
    >
      {prediction.label}
    </span>
  );
}
