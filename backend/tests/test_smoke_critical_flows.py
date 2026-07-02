from datetime import date
from decimal import Decimal
from app.models.user import Role

from .conftest import auth_headers, create_user


def test_smoke_admin_finance_end_to_end_flow(client, db):
    create_user(db, email="admin@example.com", role=Role.ADMINISTRADOR)
    create_user(db, email="finance@example.com", role=Role.FINANCEIRO)

    admin_login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe@123456"})
    assert admin_login.status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    guardian_response = client.post(
        "/api/guardians",
        json={
            "full_name": "Marina Rocha",
            "cpf": "529.982.247-25",
            "phone": "11999990001",
            "email": "marina.rocha@example.com",
            "address": "Rua das Acacias, 100",
            "kinship": "Mae",
            "student_ids": [],
        },
        headers=admin_headers,
    )
    assert guardian_response.status_code == 201
    guardian_id = guardian_response.json()["id"]

    student_response = client.post(
        "/api/students",
        json={
            "full_name": "Lucas Rocha",
            "birth_date": "2016-03-10",
            "class_name": "2 Ano",
            "status": "ativo",
            "phone": "11999990002",
            "address": "Rua das Acacias, 100",
            "notes": "Aluno da bateria smoke",
            "medical_information": "Sem restricoes",
            "guardian_ids": [guardian_id],
        },
        headers=admin_headers,
    )
    assert student_response.status_code == 201
    student_id = student_response.json()["id"]
    assert student_response.json()["guardian_ids"] == [guardian_id]

    second_guardian = client.post(
        "/api/guardians",
        json={
            "full_name": "Carlos Lima",
            "cpf": "111.444.777-35",
            "phone": "11999990003",
            "email": "carlos.lima@example.com",
            "address": "Rua das Palmeiras, 200",
            "kinship": "Pai",
            "student_ids": [],
        },
        headers=admin_headers,
    )
    assert second_guardian.status_code == 201
    second_guardian_id = second_guardian.json()["id"]

    second_student = client.post(
        "/api/students",
        json={
            "full_name": "Ana Lima",
            "birth_date": "2015-07-22",
            "class_name": "2 Ano",
            "status": "ativo",
            "phone": "11999990004",
            "address": "Rua das Palmeiras, 200",
            "notes": "Aluno controle smoke",
            "medical_information": None,
            "guardian_ids": [second_guardian_id],
        },
        headers=admin_headers,
    )
    assert second_student.status_code == 201

    finance_headers = auth_headers(client, "finance@example.com")

    payable_response = client.post(
        "/api/finance/payables",
        json={
            "description": "Internet junho",
            "category": "utilidades",
            "amount": "350.00",
            "due_date": "2026-06-10",
            "status": "pendente",
            "supplier": "Operadora Fiber",
            "notes": "Despesa smoke",
        },
        headers=finance_headers,
    )
    assert payable_response.status_code == 201
    payable_id = payable_response.json()["id"]

    payable_paid = client.post(
        f"/api/finance/payables/{payable_id}/mark-paid",
        json={"payment_date": "2026-06-10", "notes": "Pago no smoke"},
        headers=finance_headers,
    )
    assert payable_paid.status_code == 200
    assert payable_paid.json()["status"] == "pago"

    batch_payload = {
        "reference_month": "2026-06-01",
        "due_date": "2026-06-05",
        "amount": "900.00",
        "type": "mensalidade",
        "description_prefix": "Mensalidade",
        "class_name": "2 Ano",
        "only_active_students": True,
        "notes": "Gerado no smoke",
    }
    batch_response = client.post("/api/finance/receivables/generate-batch", json=batch_payload, headers=finance_headers)
    assert batch_response.status_code == 201
    assert batch_response.json()["created_count"] == 2

    receivables_response = client.get(
        "/api/finance/receivables",
        params={"student_id": student_id, "type": "mensalidade"},
        headers=finance_headers,
    )
    assert receivables_response.status_code == 200
    receivables = receivables_response.json()
    assert len(receivables) == 1
    receivable_id = receivables[0]["id"]
    assert Decimal(receivables[0]["amount"]) == Decimal("900.00")

    paid_receivable = client.post(
        f"/api/finance/receivables/{receivable_id}/mark-paid",
        json={"paid_amount": "900.00", "payment_date": "2026-06-06", "notes": "Baixa smoke"},
        headers=finance_headers,
    )
    assert paid_receivable.status_code == 200
    assert paid_receivable.json()["status"] == "pago"
    assert Decimal(paid_receivable.json()["paid_amount"]) == Decimal("900.00")

    dashboard_response = client.get(
        "/api/dashboard",
        params={"reference_date": "2026-06-30"},
        headers=finance_headers,
    )
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["total_alunos_ativos"] == 2
    assert dashboard["receita_prevista_mes"] == "1800.00"
    assert dashboard["receita_recebida_mes"] == "900.00"
    assert dashboard["despesas_mes"] == "350.00"
    assert dashboard["saldo_mes"] == "550.00"
    assert dashboard["custo_medio_por_aluno"] == "175.00"
    assert dashboard["custo_caixa_por_aluno"] == "175.00"

