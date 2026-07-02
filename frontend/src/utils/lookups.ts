import { Guardian, Student } from "../types";

export function studentOptionLabel(student: Pick<Student, "id" | "full_name" | "class_name">) {
  return student.class_name ? `${student.full_name} - ${student.class_name}` : student.full_name;
}

export function guardianOptionLabel(guardian: Pick<Guardian, "id" | "full_name" | "kinship">) {
  return guardian.kinship ? `${guardian.full_name} - ${guardian.kinship}` : guardian.full_name;
}

export function joinRelatedNames<T extends { id: number }>(
  ids: number[],
  items: T[],
  getLabel: (item: T) => string,
  emptyText = "-",
) {
  const labelMap = new Map(items.map((item) => [item.id, getLabel(item)]));
  const labels = ids.map((id) => labelMap.get(id)).filter((value): value is string => Boolean(value));
  return labels.length > 0 ? labels.join(", ") : emptyText;
}
