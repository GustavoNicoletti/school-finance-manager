import { Chip, ChipProps } from "@mui/material";

type StatusColor = ChipProps["color"];

const statusLabels: Record<string, string> = {
  ativo: "Ativo",
  inativo: "Inativo",
  transferido: "Transferido",
  pendente: "Pendente",
  pago: "Pago",
  atrasado: "Atrasado",
  cancelado: "Cancelado",
  administrador: "Administrador",
  diretor: "Diretor",
  financeiro: "Financeiro",
  secretaria: "Secretaria",
  professor: "Professor",
  responsavel: "Responsavel",
  mensalidade: "Mensalidade",
  taxa_extra: "Taxa extra",
  material: "Material",
  outro: "Outro",
};

const statusColors: Record<string, StatusColor> = {
  ativo: "success",
  inativo: "default",
  transferido: "warning",
  pendente: "warning",
  pago: "success",
  atrasado: "error",
  cancelado: "default",
  administrador: "primary",
  diretor: "primary",
  financeiro: "secondary",
  secretaria: "info",
  professor: "info",
  responsavel: "default",
  mensalidade: "primary",
  taxa_extra: "secondary",
  material: "info",
  outro: "default",
};

interface StatusChipProps {
  value: string | boolean;
}

export function StatusChip({ value }: StatusChipProps) {
  if (typeof value === "boolean") {
    return <Chip size="small" label={value ? "Ativo" : "Inativo"} color={value ? "success" : "default"} variant="outlined" />;
  }

  return <Chip size="small" label={statusLabels[value] ?? value} color={statusColors[value] ?? "default"} variant="outlined" />;
}
