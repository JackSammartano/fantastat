export interface RatedMatchday {
  matchday: number;
  vote: number | null;
}

export interface MatchdayTrend {
  sampleSize: number;
  formAverage: number | null;
  slope: number | null;
  direction: -1 | 0 | 1 | null;
}

export function calculateMatchdayTrend(rows: RatedMatchday[]): MatchdayTrend {
  const recent = rows
    .filter((row): row is { matchday: number; vote: number } => row.vote !== null)
    .sort((a, b) => a.matchday - b.matchday)
    .slice(-5);
  if (recent.length === 0) return { sampleSize: 0, formAverage: null, slope: null, direction: null };
  const formAverage = recent.reduce((sum, row) => sum + row.vote, 0) / recent.length;
  if (recent.length < 3) return { sampleSize: recent.length, formAverage, slope: null, direction: null };
  const center = (recent.length - 1) / 2;
  const meanVote = formAverage;
  let numerator = 0;
  let denominator = 0;
  recent.forEach((row, index) => {
    const distance = index - center;
    numerator += distance * (row.vote - meanVote);
    denominator += distance * distance;
  });
  const slope = denominator ? numerator / denominator : 0;
  const rounded = Number(slope.toFixed(2));
  const direction = rounded >= 0.1 ? 1 : rounded <= -0.1 ? -1 : 0;
  return { sampleSize: recent.length, formAverage, slope, direction };
}
