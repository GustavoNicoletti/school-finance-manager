import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBaseUrl = process.env.E2E_API_URL ?? "http://127.0.0.1:8000/api";
const adminEmail = process.env.E2E_ADMIN_EMAIL ?? "admin@example.com";
const adminPassword = process.env.E2E_ADMIN_PASSWORD ?? "ChangeMe@123456";

async function loginViaUi(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
}

async function loginViaApi(request: APIRequestContext) {
  const response = await request.post(`${apiBaseUrl}/auth/login`, {
    data: { email: adminEmail, password: adminPassword },
  });
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { access_token: string };
  return { Authorization: `Bearer ${body.access_token}` };
}

async function createGuardian(
  request: APIRequestContext,
  headers: Record<string, string>,
  suffix: string,
  overrides?: Partial<Record<string, unknown>>,
) {
  const response = await request.post(`${apiBaseUrl}/guardians`, {
    headers,
    data: {
      full_name: `Responsavel Smoke ${suffix}`,
      cpf: null,
      phone: "11999990001",
      email: `responsavel.smoke.${suffix}@example.com`,
      address: "Rua Smoke, 100",
      kinship: "Mae",
      student_ids: [],
      ...overrides,
    },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as { id: number; full_name: string };
}

async function createStudent(
  request: APIRequestContext,
  headers: Record<string, string>,
  suffix: string,
  guardianId: number,
  overrides?: Partial<Record<string, unknown>>,
) {
  const response = await request.post(`${apiBaseUrl}/students`, {
    headers,
    data: {
      full_name: `Aluno Smoke ${suffix}`,
      birth_date: "2016-03-10",
      class_name: "2 Ano",
      status: "ativo",
      phone: "11999990002",
      address: "Rua Smoke, 100",
      notes: "Criado pelo smoke de frontend",
      medical_information: "Sem restricoes",
      guardian_ids: [guardianId],
      ...overrides,
    },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as { id: number; full_name: string };
}

async function createReceivable(
  request: APIRequestContext,
  headers: Record<string, string>,
  studentId: number,
  suffix: string,
  overrides?: Partial<Record<string, unknown>>,
) {
  const response = await request.post(`${apiBaseUrl}/finance/receivables`, {
    headers,
    data: {
      student_id: studentId,
      description: `Mensalidade Smoke ${suffix}`,
      amount: 900,
      paid_amount: 0,
      due_date: "2026-06-05",
      payment_date: null,
      status: "pendente",
      type: "mensalidade",
      notes: "Recebimento criado pelo smoke",
      ...overrides,
    },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as { id: number; description: string };
}

test.describe("Smoke frontend", () => {
  test("admin faz login, navega e registra recebimento", async ({ page, request }) => {
    const suffix = `${Date.now()}`;
    const authHeaders = await loginViaApi(request);
    const guardian = await createGuardian(request, authHeaders, `${suffix}-a`);
    const student = await createStudent(request, authHeaders, `${suffix}-a`, guardian.id);
    const receivable = await createReceivable(request, authHeaders, student.id, `${suffix}-a`);

    await loginViaUi(page, adminEmail, adminPassword);

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("heading", { name: "Dashboard financeiro" })).toBeVisible();
    await expect(page.getByText("API online")).toBeVisible();
    await expect(page.getByText("Banco online")).toBeVisible();

    await page.goto("/students");
    await expect(page.getByRole("heading", { name: "Alunos" })).toBeVisible();
    await page.getByLabel("Buscar aluno ou responsavel").fill(student.full_name);
    await page.getByRole("button", { name: "Filtrar" }).click();
    await expect(page.getByRole("cell", { name: student.full_name }).first()).toBeVisible();
    await expect(page.getByRole("cell", { name: guardian.full_name }).first()).toBeVisible();

    await page.goto("/receivables");
    await expect(page.getByRole("heading", { name: "Contas a receber" })).toBeVisible();
    await page.getByLabel("Buscar").fill(receivable.description);
    await page.getByRole("button", { name: "Filtrar" }).click();
    await expect(page.getByRole("cell", { name: receivable.description }).first()).toBeVisible();

    const targetRow = page.getByRole("row", { name: new RegExp(receivable.description) });
    await targetRow.getByLabel("Registrar recebimento").click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: "Confirmar" }).click();
    await expect(page.getByText("Recebimento registrado.")).toBeVisible();
    await expect(targetRow.getByText("pago")).toBeVisible();
  });
});

