from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.finance import Payable, PaymentStatus, Receivable, ReceivableType
from app.models.guardian import Guardian
from app.models.student import Student, StudentStatus
from app.models.user import Role, User


DEMO_PASSWORD = "ChangeMe@123456"


def get_or_create_user(db: Session, *, full_name: str, email: str, role: Role, guardian: Guardian | None = None) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if user:
        user.full_name = full_name
        user.role = role
        user.is_active = True
        user.guardian = guardian
        return user

    user = User(
        full_name=full_name,
        email=email.lower(),
        role=role,
        is_active=True,
        guardian=guardian,
        hashed_password=get_password_hash(DEMO_PASSWORD),
    )
    db.add(user)
    db.flush()
    return user


def get_or_create_guardian(
    db: Session,
    *,
    full_name: str,
    cpf: str | None,
    phone: str | None,
    email: str | None,
    address: str | None,
    kinship: str | None,
) -> Guardian:
    guardian = db.query(Guardian).filter(Guardian.full_name == full_name).first()
    if guardian:
        return guardian

    guardian = Guardian(
        full_name=full_name,
        cpf=cpf,
        phone=phone,
        email=email,
        address=address,
        kinship=kinship,
    )
    db.add(guardian)
    db.flush()
    return guardian


def get_or_create_student(
    db: Session,
    *,
    full_name: str,
    birth_date: date | None,
    class_name: str | None,
    status: StudentStatus,
    phone: str | None,
    address: str | None,
    notes: str | None,
    medical_information: str | None,
    guardians: list[Guardian],
) -> Student:
    student = db.query(Student).filter(Student.full_name == full_name).first()
    if student:
        return student

    student = Student(
        full_name=full_name,
        birth_date=birth_date,
        class_name=class_name,
        status=status,
        phone=phone,
        address=address,
        notes=notes,
        medical_information=medical_information,
    )
    student.guardians = guardians
    db.add(student)
    db.flush()
    return student


def get_or_create_receivable(
    db: Session,
    *,
    student: Student,
    description: str,
    amount: Decimal,
    paid_amount: Decimal,
    due_date: date,
    payment_date: date | None,
    status: PaymentStatus,
    receivable_type: ReceivableType,
    notes: str | None,
) -> Receivable:
    receivable = (
        db.query(Receivable)
        .filter(
            Receivable.student_id == student.id,
            Receivable.description == description,
            Receivable.due_date == due_date,
        )
        .first()
    )
    if receivable:
        return receivable

    receivable = Receivable(
        student_id=student.id,
        description=description,
        amount=amount,
        paid_amount=paid_amount,
        due_date=due_date,
        payment_date=payment_date,
        status=status,
        type=receivable_type,
        notes=notes,
    )
    db.add(receivable)
    db.flush()
    return receivable


def get_or_create_payable(
    db: Session,
    *,
    description: str,
    category: str | None,
    amount: Decimal,
    due_date: date,
    payment_date: date | None,
    status: PaymentStatus,
    supplier: str | None,
    notes: str | None,
) -> Payable:
    payable = db.query(Payable).filter(Payable.description == description, Payable.due_date == due_date).first()
    if payable:
        return payable

    payable = Payable(
        description=description,
        category=category,
        amount=amount,
        due_date=due_date,
        payment_date=payment_date,
        status=status,
        supplier=supplier,
        notes=notes,
    )
    db.add(payable)
    db.flush()
    return payable


def seed_demo(db: Session) -> None:
    today = date.today()
    month_start = today.replace(day=1)
    previous_month_date = month_start - timedelta(days=1)
    previous_month_start = previous_month_date.replace(day=1)

    ana = get_or_create_guardian(
        db,
        full_name="Ana Paula Souza",
        cpf="52998224725",
        phone="(11) 99876-1101",
        email="ana.paula@example.com",
        address="Rua das Acacias, 120",
        kinship="Mae",
    )
    carlos = get_or_create_guardian(
        db,
        full_name="Carlos Henrique Souza",
        cpf="11144477735",
        phone="(11) 99777-2202",
        email="carlos.souza@example.com",
        address="Rua das Acacias, 120",
        kinship="Pai",
    )
    juliana = get_or_create_guardian(
        db,
        full_name="Juliana Martins",
        cpf="16899535009",
        phone="(11) 98888-3303",
        email="juliana.martins@example.com",
        address="Av. Central, 455",
        kinship="Mae",
    )
    roberto = get_or_create_guardian(
        db,
        full_name="Roberto Martins",
        cpf="39053344705",
        phone="(11) 96666-4404",
        email="roberto.martins@example.com",
        address="Av. Central, 455",
        kinship="Pai",
    )
    fernanda = get_or_create_guardian(
        db,
        full_name="Fernanda Alves",
        cpf="12345678909",
        phone="(11) 95555-5505",
        email="fernanda.alves@example.com",
        address="Rua do Colegio, 88",
        kinship="Mae",
    )

    isabela = get_or_create_student(
        db,
        full_name="Isabela Souza",
        birth_date=date(2016, 5, 12),
        class_name="1 Ano A",
        status=StudentStatus.ACTIVE,
        phone="(11) 99876-1101",
        address="Rua das Acacias, 120",
        notes="Boa adaptacao em sala.",
        medical_information="Alergia leve a poeira.",
        guardians=[ana, carlos],
    )
    lucas = get_or_create_student(
        db,
        full_name="Lucas Martins",
        birth_date=date(2014, 9, 3),
        class_name="3 Ano B",
        status=StudentStatus.ACTIVE,
        phone="(11) 98888-3303",
        address="Av. Central, 455",
        notes="Participa do reforco de matematica.",
        medical_information=None,
        guardians=[juliana, roberto],
    )
    beatriz = get_or_create_student(
        db,
        full_name="Beatriz Alves",
        birth_date=date(2017, 2, 21),
        class_name="Infantil 5",
        status=StudentStatus.ACTIVE,
        phone="(11) 95555-5505",
        address="Rua do Colegio, 88",
        notes="Entrada no turno da manha.",
        medical_information="Intolerancia a lactose.",
        guardians=[fernanda],
    )
    gabriel = get_or_create_student(
        db,
        full_name="Gabriel Souza",
        birth_date=date(2013, 11, 15),
        class_name="4 Ano A",
        status=StudentStatus.ACTIVE,
        phone="(11) 99777-2202",
        address="Rua das Acacias, 120",
        notes="Interesse por laboratorio de ciencias.",
        medical_information=None,
        guardians=[ana, carlos],
    )
    manuela = get_or_create_student(
        db,
        full_name="Manuela Costa",
        birth_date=date(2015, 8, 27),
        class_name="2 Ano A",
        status=StudentStatus.INACTIVE,
        phone="(11) 94444-6606",
        address="Rua das Flores, 301",
        notes="Matricula pausada por mudanca temporaria.",
        medical_information=None,
        guardians=[fernanda],
    )
    pedro = get_or_create_student(
        db,
        full_name="Pedro Martins",
        birth_date=date(2012, 1, 18),
        class_name="5 Ano B",
        status=StudentStatus.TRANSFERRED,
        phone="(11) 96666-4404",
        address="Av. Central, 455",
        notes="Transferencia concluida no inicio do semestre.",
        medical_information=None,
        guardians=[juliana, roberto],
    )

    demo_users = [
        ("Helena Duarte", "director@example.com", Role.DIRETOR, None),
        ("Marcos Lima", "finance@example.com", Role.FINANCEIRO, None),
        ("Camila Rocha", "secretary@example.com", Role.SECRETARIA, None),
        ("Rafael Gomes", "teacher@example.com", Role.PROFESSOR, None),
    ]
    for full_name, email, role, guardian in demo_users:
        get_or_create_user(db, full_name=full_name, email=email, role=role, guardian=guardian)

    tuition_amount = Decimal("850.00")
    material_amount = Decimal("180.00")

    get_or_create_receivable(
        db,
        student=isabela,
        description=f"Mensalidade {month_start.strftime('%m/%Y')}",
        amount=tuition_amount,
        paid_amount=tuition_amount,
        due_date=month_start + timedelta(days=5),
        payment_date=month_start + timedelta(days=4),
        status=PaymentStatus.PAID,
        receivable_type=ReceivableType.TUITION,
        notes="Pagamento confirmado via transferencia.",
    )
    get_or_create_receivable(
        db,
        student=lucas,
        description=f"Mensalidade {month_start.strftime('%m/%Y')}",
        amount=tuition_amount,
        paid_amount=Decimal("0.00"),
        due_date=month_start + timedelta(days=5),
        payment_date=None,
        status=PaymentStatus.OVERDUE,
        receivable_type=ReceivableType.TUITION,
        notes="Contato financeiro pendente.",
    )
    get_or_create_receivable(
        db,
        student=beatriz,
        description=f"Mensalidade {month_start.strftime('%m/%Y')}",
        amount=tuition_amount,
        paid_amount=Decimal("0.00"),
        due_date=month_start + timedelta(days=10),
        payment_date=None,
        status=PaymentStatus.PENDING,
        receivable_type=ReceivableType.TUITION,
        notes="Vencimento ainda dentro do prazo.",
    )
    get_or_create_receivable(
        db,
        student=gabriel,
        description=f"Mensalidade {month_start.strftime('%m/%Y')}",
        amount=tuition_amount,
        paid_amount=Decimal("400.00"),
        due_date=month_start + timedelta(days=5),
        payment_date=month_start + timedelta(days=8),
        status=PaymentStatus.OVERDUE,
        receivable_type=ReceivableType.TUITION,
        notes="Pagamento parcial registrado.",
    )
    get_or_create_receivable(
        db,
        student=isabela,
        description=f"Material didatico {month_start.strftime('%m/%Y')}",
        amount=material_amount,
        paid_amount=material_amount,
        due_date=month_start + timedelta(days=12),
        payment_date=month_start + timedelta(days=11),
        status=PaymentStatus.PAID,
        receivable_type=ReceivableType.MATERIAL,
        notes="Kit entregue.",
    )
    get_or_create_receivable(
        db,
        student=lucas,
        description=f"Mensalidade {previous_month_start.strftime('%m/%Y')}",
        amount=tuition_amount,
        paid_amount=Decimal("0.00"),
        due_date=previous_month_start + timedelta(days=5),
        payment_date=None,
        status=PaymentStatus.OVERDUE,
        receivable_type=ReceivableType.TUITION,
        notes="Em aberto desde o mes anterior.",
    )

    get_or_create_payable(
        db,
        description=f"Folha professores {month_start.strftime('%m/%Y')}",
        category="Folha",
        amount=Decimal("9200.00"),
        due_date=month_start + timedelta(days=5),
        payment_date=month_start + timedelta(days=5),
        status=PaymentStatus.PAID,
        supplier="Equipe docente",
        notes="Folha principal do mes.",
    )
    get_or_create_payable(
        db,
        description=f"Aluguel predio {month_start.strftime('%m/%Y')}",
        category="Estrutura",
        amount=Decimal("4200.00"),
        due_date=month_start + timedelta(days=8),
        payment_date=month_start + timedelta(days=8),
        status=PaymentStatus.PAID,
        supplier="Imobiliaria Centro",
        notes=None,
    )
    get_or_create_payable(
        db,
        description=f"Internet e telefonia {month_start.strftime('%m/%Y')}",
        category="Utilidades",
        amount=Decimal("420.00"),
        due_date=month_start + timedelta(days=12),
        payment_date=None,
        status=PaymentStatus.PENDING,
        supplier="Operadora Conecta",
        notes=None,
    )
    get_or_create_payable(
        db,
        description=f"Material de limpeza {month_start.strftime('%m/%Y')}",
        category="Suprimentos",
        amount=Decimal("310.00"),
        due_date=month_start + timedelta(days=4),
        payment_date=None,
        status=PaymentStatus.OVERDUE,
        supplier="Distribuidora Limpar",
        notes="Fornecedor cobrou reposicao semanal.",
    )

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed_demo(db)
        print("Dados demonstrativos prontos.")
        print(f"Senha padrao dos usuarios de demo: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

