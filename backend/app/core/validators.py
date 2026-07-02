import re


def validate_password_strength(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("A senha deve ter no máximo 72 bytes.")
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("A senha deve conter ao menos uma letra maiúscula.")
    if not re.search(r"[a-z]", password):
        raise ValueError("A senha deve conter ao menos uma letra minúscula.")
    if not re.search(r"\d", password):
        raise ValueError("A senha deve conter ao menos um número.")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("A senha deve conter ao menos um caractere especial.")
    return password


def normalize_cpf(cpf: str | None) -> str | None:
    if cpf is None:
        return None
    digits = re.sub(r"\D", "", cpf)
    return digits or None


def validate_cpf(cpf: str | None) -> str | None:
    digits = normalize_cpf(cpf)
    if digits is None:
        return None
    if len(digits) != 11 or len(set(digits)) == 1:
        raise ValueError("CPF inválido.")

    def calculate_digit(partial: str, factor: int) -> str:
        total = sum(int(digit) * weight for digit, weight in zip(partial, range(factor, 1, -1), strict=False))
        remainder = (total * 10) % 11
        return "0" if remainder == 10 else str(remainder)

    first_digit = calculate_digit(digits[:9], 10)
    second_digit = calculate_digit(digits[:10], 11)
    if digits[-2:] != first_digit + second_digit:
        raise ValueError("CPF inválido.")
    return digits
