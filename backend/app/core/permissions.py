from enum import Enum

from app.models.user import Role


class Permission(str, Enum):
    DASHBOARD_VIEW = "dashboard_view"
    STUDENTS_VIEW = "students_view"
    STUDENTS_MANAGE = "students_manage"
    GUARDIANS_VIEW = "guardians_view"
    GUARDIANS_MANAGE = "guardians_manage"
    RECEIVABLES_VIEW = "receivables_view"
    RECEIVABLES_MANAGE = "receivables_manage"
    PAYABLES_VIEW = "payables_view"
    PAYABLES_MANAGE = "payables_manage"
    DELINQUENCY_VIEW = "delinquency_view"
    CASH_FLOW_VIEW = "cash_flow_view"
    USERS_VIEW = "users_view"
    USERS_MANAGE = "users_manage"
    USERS_DELETE = "users_delete"
    AUDIT_VIEW = "audit_view"
    ROLE_PERMISSIONS_MANAGE = "role_permissions_manage"


PERMISSION_CATALOG = [
    {
        "group": "Geral",
        "items": [
            {
                "key": Permission.DASHBOARD_VIEW.value,
                "label": "Dashboard financeiro",
                "description": "Pode visualizar o dashboard financeiro comparativo.",
            },
        ],
    },
    {
        "group": "Academico",
        "items": [
            {
                "key": Permission.STUDENTS_VIEW.value,
                "label": "Ver alunos",
                "description": "Pode visualizar alunos, listas e detalhes.",
            },
            {
                "key": Permission.STUDENTS_MANAGE.value,
                "label": "Gerenciar alunos",
                "description": "Pode criar, editar e excluir alunos.",
            },
            {
                "key": Permission.GUARDIANS_VIEW.value,
                "label": "Ver responsaveis",
                "description": "Pode visualizar responsaveis e seus vinculos.",
            },
            {
                "key": Permission.GUARDIANS_MANAGE.value,
                "label": "Gerenciar responsaveis",
                "description": "Pode criar, editar e excluir responsaveis.",
            },
        ],
    },
    {
        "group": "Financeiro",
        "items": [
            {
                "key": Permission.RECEIVABLES_VIEW.value,
                "label": "Ver contas a receber",
                "description": "Pode visualizar contas a receber e exportacoes.",
            },
            {
                "key": Permission.RECEIVABLES_MANAGE.value,
                "label": "Gerenciar contas a receber",
                "description": "Pode criar, editar, excluir, baixar e gerar cobrancas em lote.",
            },
            {
                "key": Permission.PAYABLES_VIEW.value,
                "label": "Ver contas a pagar",
                "description": "Pode visualizar contas a pagar e exportacoes.",
            },
            {
                "key": Permission.PAYABLES_MANAGE.value,
                "label": "Gerenciar contas a pagar",
                "description": "Pode criar, editar, excluir e baixar despesas.",
            },
            {
                "key": Permission.DELINQUENCY_VIEW.value,
                "label": "Ver inadimplencia",
                "description": "Pode consultar e exportar relatorios de inadimplencia.",
            },
            {
                "key": Permission.CASH_FLOW_VIEW.value,
                "label": "Ver fluxo de caixa",
                "description": "Pode consultar e exportar o fluxo de caixa.",
            },
        ],
    },
    {
        "group": "Administracao",
        "items": [
            {
                "key": Permission.USERS_VIEW.value,
                "label": "Ver usuarios",
                "description": "Pode visualizar a listagem de usuarios.",
            },
            {
                "key": Permission.USERS_MANAGE.value,
                "label": "Gerenciar usuarios",
                "description": "Pode criar e editar usuarios.",
            },
            {
                "key": Permission.USERS_DELETE.value,
                "label": "Excluir usuarios",
                "description": "Pode excluir usuarios do sistema.",
            },
            {
                "key": Permission.AUDIT_VIEW.value,
                "label": "Ver auditoria",
                "description": "Pode consultar trilhas de auditoria.",
            },
            {
                "key": Permission.ROLE_PERMISSIONS_MANAGE.value,
                "label": "Gerenciar permissoes",
                "description": "Pode editar o que cada perfil pode ver e fazer.",
            },
        ],
    },
]


ALL_PERMISSION_KEYS = {item["key"] for group in PERMISSION_CATALOG for item in group["items"]}

DEFAULT_ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMINISTRADOR: set(ALL_PERMISSION_KEYS),
    Role.DIRETOR: {
        Permission.DASHBOARD_VIEW.value,
        Permission.STUDENTS_VIEW.value,
        Permission.STUDENTS_MANAGE.value,
        Permission.GUARDIANS_VIEW.value,
        Permission.GUARDIANS_MANAGE.value,
        Permission.RECEIVABLES_VIEW.value,
        Permission.RECEIVABLES_MANAGE.value,
        Permission.PAYABLES_VIEW.value,
        Permission.PAYABLES_MANAGE.value,
        Permission.DELINQUENCY_VIEW.value,
        Permission.CASH_FLOW_VIEW.value,
        Permission.USERS_VIEW.value,
        Permission.USERS_MANAGE.value,
        Permission.AUDIT_VIEW.value,
        Permission.ROLE_PERMISSIONS_MANAGE.value,
    },
    Role.FINANCEIRO: {
        Permission.DASHBOARD_VIEW.value,
        Permission.RECEIVABLES_VIEW.value,
        Permission.RECEIVABLES_MANAGE.value,
        Permission.PAYABLES_VIEW.value,
        Permission.PAYABLES_MANAGE.value,
        Permission.DELINQUENCY_VIEW.value,
        Permission.CASH_FLOW_VIEW.value,
    },
    Role.SECRETARIA: {
        Permission.STUDENTS_VIEW.value,
        Permission.STUDENTS_MANAGE.value,
        Permission.GUARDIANS_VIEW.value,
        Permission.GUARDIANS_MANAGE.value,
    },
    Role.PROFESSOR: {
        Permission.STUDENTS_VIEW.value,
        Permission.GUARDIANS_VIEW.value,
    },
    Role.RESPONSAVEL: set(),
}
