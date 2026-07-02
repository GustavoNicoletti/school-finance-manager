export interface DateRange {
  from: string;
  to: string;
}

export function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayIso() {
  return toDateInputValue(new Date());
}

export function addDaysIso(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return toDateInputValue(date);
}

export function monthRange(monthOffset = 0): DateRange {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
  const end = new Date(now.getFullYear(), now.getMonth() + monthOffset + 1, 0);
  return {
    from: toDateInputValue(start),
    to: toDateInputValue(end),
  };
}

export function currentMonthRange() {
  return monthRange(0);
}

export function previousMonthRange() {
  return monthRange(-1);
}

export function nextMonthRange() {
  return monthRange(1);
}
