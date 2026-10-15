"""Validação de CNPJ — numérico e alfanumérico (formato vigente a partir de jul/2026).

Os 12 primeiros caracteres podem ser dígitos ou letras maiúsculas; os 2 últimos são sempre dígitos
verificadores (módulo 11). O valor de cada caractere é o código ASCII menos 48 ("0"=0 ... "A"=17).
"""

import re

_PESOS_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_DV2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_FORMATO = re.compile(r"^[0-9A-Z]{12}[0-9]{2}$")


def normalizar_cnpj(valor: str) -> str:
    """Remove máscara/espaços e põe em maiúsculas: '12.abc.345/01de-35' -> '12ABC34501DE35'."""
    return re.sub(r"[.\-/\s]", "", valor).upper()


def _digito(base: str, pesos: tuple[int, ...]) -> int:
    resto = sum((ord(c) - 48) * p for c, p in zip(base, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_valido(cnpj_normalizado: str) -> bool:
    """Valida um CNPJ JÁ normalizado (14 caracteres, sem máscara)."""
    n = cnpj_normalizado
    if not _FORMATO.match(n) or len(set(n)) == 1:  # rejeita 00000000000000, 11111111111111...
        return False
    dv1 = _digito(n[:12], _PESOS_DV1)
    dv2 = _digito(n[:12] + str(dv1), _PESOS_DV2)
    return n[12:] == f"{dv1}{dv2}"


def validar_cnpj(valor: str) -> str:
    """Para validadores Pydantic: devolve o CNPJ normalizado ou levanta ValueError."""
    n = normalizar_cnpj(valor)
    if not cnpj_valido(n):
        raise ValueError("CNPJ inválido")
    return n
