"""Chave de acesso da NF-e (44 posições): estrutura e dígito verificador (módulo 11).

Posições: cUF(2) AAMM(4) CNPJ(14) modelo(2) série(3) número(9) tpEmis(1) cNF(8) DV(1).
O CNPJ pode ser alfanumérico (a partir de jul/2026): cada caractere vale o código ASCII menos 48.
"""

import re
from dataclasses import dataclass

_FORMATO = re.compile(r"^\d{6}[0-9A-Z]{14}\d{24}$")

UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}  # fmt: skip


def digito_verificador(base43: str) -> int:
    """DV módulo 11 com pesos 2..9 da direita para a esquerda."""
    soma = 0
    peso = 2
    for c in reversed(base43):
        soma += (ord(c) - 48) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = soma % 11
    return 0 if resto in (0, 1) else 11 - resto


@dataclass(frozen=True)
class PartesChave:
    uf_codigo: str
    ano_mes: str
    cnpj: str
    modelo: str
    serie: str
    numero: str


def formato_valido(chave: str) -> bool:
    return bool(_FORMATO.match(chave))


def dv_valido(chave: str) -> bool:
    return formato_valido(chave) and digito_verificador(chave[:43]) == int(chave[43])


def partes(chave: str) -> PartesChave:
    return PartesChave(
        uf_codigo=chave[0:2],
        ano_mes=chave[2:6],
        cnpj=chave[6:20],
        modelo=chave[20:22],
        serie=chave[22:25],
        numero=chave[25:34],
    )
