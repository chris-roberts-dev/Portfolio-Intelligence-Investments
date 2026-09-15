export function formatCurrency(
  value: string | null,
  currency: string,
): string {
  if (value === null) {
    return "Not available";
  }

  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numericValue);
}

export function formatPercent(
  value: number | null,
  fractionDigits = 2,
): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    signDisplay: "exceptZero",
  }).format(value);
}

export function formatDecimalPercent(value: string | null): string {
  if (value === null) {
    return "Not available";
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue)
    ? formatPercent(numericValue, 1)
    : "Not available";
}

export function formatDate(value: string): string {
  const date = new Date(`${value}T12:00:00`);
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function formatDateTime(value: string | null): string {
  if (value === null) {
    return "Not available";
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(value));
}

export function humanizeCode(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  const words = value.toLowerCase().replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
