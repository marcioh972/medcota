from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from ..enums import Perfil
from .types import Cnpj, Email, Nome, Senha, Texto


class CadastroEmpresaIn(BaseModel):
    """Cadastro da empresa: cria o tenant e o primeiro usuário, que é o gestor."""

    empresa_nome: Nome
    cnpj: Cnpj
    gestor_nome: Nome
    email: Email
    senha: Senha


class CadastroFuncionarioIn(BaseModel):
    """Cadastro de comprador/vendedor com o código de validação gerado pelo gestor."""

    codigo: Texto = Field(min_length=4, max_length=40)
    nome: Nome
    email: Email
    senha: Senha
    perfil: Literal["vendedor", "comprador"]  # gestor só nasce no cadastro da empresa


class EmpresaOut(BaseModel):
    id: int
    nome: str
    cnpj: str | None
    codigo_validacao: str | None  # formatado: ABCD-EFGH-JKLM
    codigo_expira_em: datetime | None
    codigo_ativo: bool  # existe e não expirou


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    perfil: Perfil
    ativo: bool
    ver_preco_custo: bool


class UsuarioPatch(BaseModel):
    ativo: bool | None = None
    ver_preco_custo: bool | None = None

    @model_validator(mode="after")
    def _ao_menos_um(self):
        if self.ativo is None and self.ver_preco_custo is None:
            raise ValueError("Informe ao menos um campo para alterar")
        return self
