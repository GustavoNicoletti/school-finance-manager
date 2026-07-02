export function formatCurrency(value: string | number | null | undefined) {
  const numberValue = Number(value ?? 0);
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(numberValue);
}

export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(value));
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatMonthYear(value: string | null | undefined) {
  if (!value) {
    return "";
  }

  const baseDate = value.length === 7 ? new Date(`${value}-01T00:00:00`) : new Date(value);
  return new Intl.DateTimeFormat("pt-BR", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(baseDate);
}

export function formatSignedCurrency(value: string | number | null | undefined) {
  const numberValue = Number(value ?? 0);
  if (numberValue === 0) {
    return formatCurrency(0);
  }
  return `${numberValue > 0 ? "+" : "-"}${formatCurrency(Math.abs(numberValue))}`;
}

export function formatSignedNumber(value: string | number | null | undefined) {
  const numberValue = Number(value ?? 0);
  if (numberValue > 0) {
    return `+${numberValue}`;
  }
  return String(numberValue);
}

export function parseIds(value: string) {
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isInteger(item) && item > 0);
}
