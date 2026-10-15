from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from ..enums import ClasseProduto, Escopo
from .types import Texto


def _vazio_vira_none(v):
    return None if isinstance(v, str) and not v.strip() else v


class ProdutoIn(BaseModel):
    nome: Annotated[Texto, Field(min_length=2, max_length=200)]
    principio_ativo: Annotated[Texto, Field(max_length=200)] = ""
    ean: Annotated[str | None, BeforeValidator(_vazio_vira_none), Field(pattern=r"^\d{8,13}$")] = None
    classe: ClasseProduto = ClasseProduto.farma
    origem: Escopo = Escopo.local
    controlado: bool = False


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    principio_ativo: str
    ean: str | None
    classe: ClasseProduto
    origem: Escopo
    controlado: bool
