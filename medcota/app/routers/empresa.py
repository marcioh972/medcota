"""Área do gestor: dados da empresa, código de validação e equipe."""

from fastapi import APIRouter

from ..core.deps import DbSession, Gestor
from ..schemas.empresas import EmpresaOut, UsuarioOut, UsuarioPatch
from ..services import empresas, equipe

router = APIRouter(prefix="/empresa", tags=["empresa (gestor)"])


@router.get("", response_model=EmpresaOut)
def minha_empresa(u: Gestor, db: DbSession):
    return empresas.empresa_out(empresas.obter_empresa(db, u))


@router.post("/codigo", response_model=EmpresaOut)
def gerar_codigo(u: Gestor, db: DbSession):
    """Gera (ou renova) o código de validação. O código anterior deixa de valer."""
    return empresas.empresa_out(empresas.gerar_codigo(db, u))


@router.delete("/codigo", response_model=EmpresaOut)
def revogar_codigo(u: Gestor, db: DbSession):
    """Revoga o código: ninguém consegue se cadastrar até que um novo seja gerado."""
    return empresas.empresa_out(empresas.revogar_codigo(db, u))


@router.get("/equipe", response_model=list[UsuarioOut])
def listar_equipe(u: Gestor, db: DbSession):
    return equipe.listar_equipe(db, u.empresa_id)


@router.patch("/equipe/{usuario_id}", response_model=UsuarioOut)
def atualizar_usuario(usuario_id: int, dados: UsuarioPatch, u: Gestor, db: DbSession):
    return equipe.atualizar_usuario(db, u, usuario_id, dados)
