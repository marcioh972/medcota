"""Cadastros públicos (sem login): empresa (gestor) e funcionários (com código de validação)."""

from fastapi import APIRouter, Request

from ..core.config import settings
from ..core.deps import DbSession
from ..core.ratelimit import limiter
from ..schemas.auth import LoginOut
from ..schemas.empresas import CadastroEmpresaIn, CadastroFuncionarioIn
from ..services import empresas
from ..services.auth import emitir_login

router = APIRouter(prefix="/cadastro", tags=["cadastro"])


@router.post("/empresa", response_model=LoginOut, status_code=201)
@limiter.limit(settings.rate_limit_cadastro)
def cadastrar_empresa(request: Request, dados: CadastroEmpresaIn, db: DbSession):
    """Cria a empresa e o gestor; já devolve a sessão (login automático)."""
    return emitir_login(empresas.cadastrar_empresa(db, dados))


@router.post("/funcionario", response_model=LoginOut, status_code=201)
@limiter.limit(settings.rate_limit_cadastro)
def cadastrar_funcionario(request: Request, dados: CadastroFuncionarioIn, db: DbSession):
    """Cadastro de comprador/vendedor com o código de validação da empresa."""
    return emitir_login(empresas.cadastrar_funcionario(db, dados))
