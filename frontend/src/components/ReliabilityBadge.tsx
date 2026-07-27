import type { ReliabilityBand } from "../models/api";

const LABELS: Record<ReliabilityBand, string> = {
  low: "Bassa",
  medium: "Media",
  high: "Alta"
};

export function ReliabilityBadge({
  band,
  score
}: {
  band: ReliabilityBand;
  score: number;
}) {
  return (
    <span className={`reliability reliability--${band}`}>
      <span className="reliability__dot" />
      {LABELS[band]} · {Math.round(score)}
    </span>
  );
}

