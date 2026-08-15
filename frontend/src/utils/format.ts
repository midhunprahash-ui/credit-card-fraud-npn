export function formatNumber(value: number, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits }).format(
    value,
  );
}

export function formatPercent(value: number, digits = 1): string {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatLatency(value: number): string {
  return value >= 1_000
    ? `${(value / 1_000).toFixed(2)} s`
    : `${value.toFixed(1)} ms`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function riskBand(score: number): "low" | "review" | "high" {
  if (score >= 0.85) return "high";
  if (score >= 0.6) return "review";
  return "low";
}

export function downloadText(
  filename: string,
  content: string,
  type = "text/csv",
): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function recordsToCsv(records: Array<Record<string, unknown>>): string {
  if (!records.length) return "";
  const headers = Array.from(
    new Set(records.flatMap((row) => Object.keys(row))),
  );
  const encode = (value: unknown) => {
    const text = value == null ? "" : String(value);
    return `"${text.replaceAll('"', '""')}"`;
  };
  return [
    headers.map(encode).join(","),
    ...records.map((row) =>
      headers.map((header) => encode(row[header])).join(","),
    ),
  ].join("\n");
}
