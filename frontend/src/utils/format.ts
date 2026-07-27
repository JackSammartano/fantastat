export function formatNumber(
  value: number | null | undefined,
  digits = 2
): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("it-IT", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "percent",
    maximumFractionDigits: 0
  }).format(value);
}

