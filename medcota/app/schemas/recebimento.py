"""Contratos do módulo de recebimento e conferência fiscal de NF-e."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, field_validator

from ..enums import (
    DecisaoNFe,
    OrigemPedido,
    ResultadoNFe,
    Severidade,
    StatusPedido,
    StatusRecebimento,
)
from .produtos import _vazio_vira_none
from .types import Texto


# ---------------------------------------------------------------- pedido registrado na tela
class PedidoManualItemIn(BaseModel):
    produto_id: int
    quantidade: int = Field(gt=0, le=1_000_000)
    preco: Decimal = Field(gt=0, max_digits=12, decimal_places=4)  # preço unitário combinado


class PedidoManualIn(BaseModel):
    fornecedor_id: int
    itens: list[PedidoManualItemIn] = Field(min_length=1, max_length=200)
    frete_previsto: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    numero_externo: Annotated[Texto | None, BeforeValidator(_vazio_vira_none), Field(max_length=40)] = None
    observacao: Annotated[Texto, Field(max_length=500)] = ""

    @field_validator("itens")
    @classmethod
    def _sem_produto_repetido(cls, itens: list[PedidoManualItemIn]) -> list[PedidoManualItemIn]:
        ids = [i.produto_id for i in itens]
        if len(ids) != len(set(ids)):
            raise ValueError("Há produtos repetidos no pedido: some as quantidades em uma única linha.")
        return itens


# ---------------------------------------------------------------- saídas
class ApontamentoOut(BaseModel):
    severidade: Severidade
    codigo: str
    mensagem: str
    item_numero: int | None
    campo: str | None
    esperado: str | None
    encontrado: str | None
    base_legal: str | None


class NFeResumoOut(BaseModel):
    id: int
    pedido_id: int | None
    chave_acesso: str
    numero: str | None
    serie: str | None
    emitente_nome: str | None
    emitente_cnpj: str | None
    data_emissao: datetime | None
    valor_total: Decimal | None
    valor_frete: Decimal | None
    resultado: ResultadoNFe
    decisao: DecisaoNFe
    importada_em: datetime
    erros: int
    alertas: int
    infos: int


class NFeDetalheOut(NFeResumoOut):
    fornecedor_id: int | None
    protocolo_status: str | None
    justificativa: str
    decisao_em: datetime | None
    versao_regras: str | None
    apontamentos: list[ApontamentoOut]


class PedidoRecebimentoItemOut(BaseModel):
    produto_id: int
    produto: str
    ean: str | None
    fornecedor_id: int
    quantidade: int
    preco: Decimal


class FornecedorResumoOut(BaseModel):
    id: int
    nome: str
    cnpj: str | None
    credenciado_72101: bool


class PedidoRecebimentoOut(BaseModel):
    id: int
    criado_em: datetime
    origem: OrigemPedido
    status: StatusPedido
    recebimento: StatusRecebimento
    total: Decimal
    frete_previsto: Decimal
    numero_externo: str | None
    observacao: str
    fornecedores: list[FornecedorResumoOut]
    itens: list[PedidoRecebimentoItemOut]
    nfes: list[NFeResumoOut]


class DecisaoIn(BaseModel):
    decisao: DecisaoNFe
    justificativa: Annotated[Texto, Field(max_length=500)] = ""

    @field_validator("decisao")
    @classmethod
    def _nao_pendente(cls, v: DecisaoNFe) -> DecisaoNFe:
        if v == DecisaoNFe.pendente:
            raise ValueError("Escolha aceitar ou recusar.")
        return v


# ---------------------------------------------------------------- configuração fiscal
class ConfiguracaoFiscalIn(BaseModel):
    aliquota_interna_icms: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    tolerancia_preco_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100, max_digits=5, decimal_places=2)
    frete_zero_municipios: list[Annotated[str, Field(pattern=r"^\d{7}$")]] = Field(
        default_factory=lambda: ["2704302"], max_length=50
    )
    exigir_protocolo: bool = True


class ConfiguracaoFiscalOut(ConfiguracaoFiscalIn):
    atualizada_em: datetime | None = None
