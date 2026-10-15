from pydantic import BaseModel, ConfigDict, Field

from ..enums import StatusFalta, Urgencia


class FaltaIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    produto_id: int
    cliente: str = Field(min_length=2, max_length=150)
    quantidade: int = Field(gt=0, le=100_000)
    urgencia: Urgencia = Urgencia.media
    observacao: str = Field("", max_length=500)
    aceita_alternativa: bool = True


class FaltaOut(BaseModel):
    id: int
    produto: str
    ean: str | None
    cliente: str
    quantidade: int
    urgencia: Urgencia
    status: StatusFalta
    detalhe: str = ""


class ConsolidadoOut(BaseModel):
    produto_id: int
    produto: str
    ean: str | None
    origem: str
    demanda: int
    solicitantes: list[str]
    clientes: int
    urgencia_maxima: Urgencia
