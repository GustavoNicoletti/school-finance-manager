export type UserRole = "administrador" | "diretor" | "financeiro" | "secretaria" | "professor" | "responsavel";
export type PermissionKey =
  | "dashboard_view"
  | "students_view"
  | "students_manage"
  | "guardians_view"
  | "guardians_manage"
  | "receivables_view"
  | "receivables_manage"
  | "payables_view"
  | "payables_manage"
  | "delinquency_view"
  | "cash_flow_view"
  | "users_view"
  | "users_manage"
  | "users_delete"
  | "audit_view"
  | "role_permissions_manage";
export type StudentStatus = "ativo" | "inativo" | "transferido";
export type PaymentStatus = "pendente" | "pago" | "atrasado" | "cancelado";
export type ReceivableType = "mensalidade" | "taxa_extra" | "material" | "outro";

export interface User {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  guardian_id?: number | null;
  permissions: PermissionKey[];
  created_at: string;
  updated_at: string;
}

export interface PermissionDefinition {
  key: PermissionKey;
  label: string;
  description: string;
  group: string;
}

export interface RolePermissionProfile {
  role: UserRole;
  permissions: PermissionKey[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RolePermissionMatrix {
  profiles: RolePermissionProfile[];
  catalog: PermissionDefinition[];
}

export interface Student {
  id: number;
  full_name: string;
  birth_date?: string | null;
  class_name?: string | null;
  status: StudentStatus;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
  medical_information?: string | null;
  guardian_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface Guardian {
  id: number;
  full_name: string;
  cpf?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  kinship?: string | null;
  student_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface Receivable {
  id: number;
  student_id: number;
  description: string;
  amount: string;
  paid_amount: string;
  due_date: string;
  payment_date?: string | null;
  status: PaymentStatus;
  type: ReceivableType;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReceivableBatchCreatePayload {
  reference_month: string;
  due_date: string;
  amount: number;
  type: ReceivableType;
  description_prefix: string;
  class_name?: string | null;
  only_active_students: boolean;
  notes?: string | null;
}

export interface ReceivableBatchResult {
  reference_month: string;
  due_date: string;
  amount: string;
  type: ReceivableType;
  total_students: number;
  created_count: number;
  skipped_count: number;
  description: string;
  created_ids: number[];
  skipped_students: string[];
}

export interface Payable {
  id: number;
  description: string;
  category?: string | null;
  amount: string;
  due_date: string;
  payment_date?: string | null;
  status: PaymentStatus;
  supplier?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DelinquencyItem {
  student_id: number;
  student_name: string;
  class_name?: string | null;
  phone?: string | null;
  overdue_count: number;
  overdue_amount: string;
  oldest_due_date: string;
}

export interface CashFlowEntry {
  date: string;
  expected_revenue: string;
  received_revenue: string;
  paid_expenses: string;
  balance: string;
}

export interface CashFlowSummary {
  start_date: string;
  end_date: string;
  expected_revenue: string;
  received_revenue: string;
  paid_expenses: string;
  balance: string;
  entries: CashFlowEntry[];
}

export interface DashboardSummary {
  mes_referencia: string;
  periodo_inicio: string;
  periodo_fim: string;
  data_referencia: string;
  mes_comparacao: string;
  total_alunos_ativos: number;
  receita_prevista_mes: string;
  receita_recebida_mes: string;
  despesas_mes: string;
  despesas_pendentes_mes: string;
  saldo_mes: string;
  quantidade_inadimplentes: number;
  valor_total_inadimplente: string;
  custo_medio_por_aluno: string;
  custo_caixa_por_aluno: string;
  variacao_receita_prevista: string;
  variacao_receita_recebida: string;
  variacao_despesas: string;
  variacao_despesas_pendentes: string;
  variacao_saldo: string;
  variacao_quantidade_inadimplentes: number;
  variacao_valor_inadimplente: string;
  variacao_custo_medio_por_aluno: string;
  variacao_custo_caixa_por_aluno: string;
}

export interface AuditLog {
  id: number;
  user_id?: number | null;
  action: string;
  entity: string;
  entity_id?: number | null;
  previous_value?: Record<string, unknown> | null;
  new_value?: Record<string, unknown> | null;
  created_at: string;
}
