"""Política de senha: mínimo de 8 caracteres, com maiúscula, minúscula e número."""

import secrets
import string

MIN_CARACTERES = 8
MAX_BYTES = 72  # limite do bcrypt


def problemas_senha(senha: str) -> list[str]:
    """Lista, em português, o que falta para a senha ser aceita (vazia = senha válida)."""
    faltas: list[str] = []
    if len(senha) < MIN_CARACTERES:
        faltas.append(f"pelo menos {MIN_CARACTERES} caracteres")
    if len(senha.encode("utf-8")) > MAX_BYTES:
        faltas.append(f"no máximo {MAX_BYTES} bytes")
    if not any(c.isupper() for c in senha):
        faltas.append("uma letra maiúscula")
    if not any(c.islower() for c in senha):
        faltas.append("uma letra minúscula")
    if not any(c.isascii() and c.isdigit() for c in senha):
        faltas.append("um número")
    return faltas


def validar_senha(senha: str) -> str:
    """Para uso em validadores Pydantic: devolve a senha ou levanta ValueError."""
    faltas = problemas_senha(senha)
    if faltas:
        raise ValueError("A senha precisa ter " + ", ".join(faltas))
    return senha


def gerar_senha_valida(tamanho: int = 12) -> str:
    """Senha aleatória que cumpre a política (usada pelo seed de desenvolvimento)."""
    obrigatorios = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    resto = [secrets.choice(string.ascii_letters + string.digits) for _ in range(tamanho - 3)]
    chars = obrigatorios + resto
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
