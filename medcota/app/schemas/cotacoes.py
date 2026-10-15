from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from ..enums import Pagamento


class CotacaoOut(BaseModel):
    id: int
    fornecedor: str
    escopo: str
    token: str
    url: str
    expira_em: datetime
    itens: int
    respostas: int
    rodada: int
    aberturas: int


class ItemCotacaoPublico(BaseModel):
    item_id: int
    produto: str
    ean: str | None
    demanda: int


class CotacaoPublicaOut(BaseModel):
    fornecedor: str
    expira_em: datetime
    rodada: int
    itens: list[ItemCotacaoPublico]


class RespostaIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    item_id: int
    preco: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    quantidade: int = Field(gt=0, le=1_000_000)
    prazo_dias: int = Field(gt=0, le=365)
    pagamento: Pagamento = Pagamento.a_vista
    lote: str = Field("", max_length=40)
    validade: datetime | None = None


class OfertaOut(BaseModel):
    fornecedor: str
    # None quando o usuário não tem a permissão ver_preco_custo (RN-04)
    preco: Decimal | None
    quantidade: int
    pagamento: Pagamento
    prazo_dias: int
    custo_final: Decimal | None
    acima_da_media: bool
    vencedor: bool


class ComparativoItem(BaseModel):
    produto_id: int
    produto: str
    demanda: int
    media_historica: Decimal | None
    ofertas: list[OfertaOut]
    sem_oferta_valida: bool
