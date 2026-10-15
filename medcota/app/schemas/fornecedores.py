from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field

from ..enums import Escopo
from .produtos import _vazio_vira_none
from .types import Cnpj, Texto


class FornecedorIn(BaseModel):
    nome: Annotated[Texto, Field(min_length=2, max_length=150)]
    escopo: Escopo = Escopo.nacional
    email: Annotated[EmailStr | None, BeforeValidator(_vazio_vira_none)] = None
    # CNPJ do fornecedor: permite conferir o emitente das notas fiscais
    cnpj: Annotated[Cnpj | None, BeforeValidator(_vazio_vira_none)] = None
    # Atacadista credenciado no Decreto AL 72.101/2020 (informado pela empresa)
    credenciado_72101: bool = False


class FornecedorPatch(BaseModel):
    """Atualização parcial: só os campos enviados mudam."""

    email: Annotated[EmailStr | None, BeforeValidator(_vazio_vira_none)] = None
    cnpj: Annotated[Cnpj | None, BeforeValidator(_vazio_vira_none)] = None
    credenciado_72101: bool | None = None


class FornecedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    escopo: Escopo
    email: str
    cnpj: str | None
    credenciado_72101: bool
