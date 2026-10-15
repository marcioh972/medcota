from fastapi import APIRouter

from ..core.deps import CompradorOuGestor, DbSession
from ..schemas.fornecedores import FornecedorIn, FornecedorOut, FornecedorPatch
from ..services import catalogo

router = APIRouter(prefix="/fornecedores", tags=["catálogo"])


@router.get("", response_model=list[FornecedorOut])
def listar_fornecedores(u: CompradorOuGestor, db: DbSession):
    return catalogo.listar_fornecedores(db, u.empresa_id)


@router.post("", response_model=FornecedorOut, status_code=201)
def criar_fornecedor(dados: FornecedorIn, u: CompradorOuGestor, db: DbSession):
    return catalogo.criar_fornecedor(db, u, dados)


@router.patch("/{fornecedor_id}", response_model=FornecedorOut)
def atualizar_fornecedor(fornecedor_id: int, dados: FornecedorPatch, u: CompradorOuGestor, db: DbSession):
    return catalogo.atualizar_fornecedor(db, u, fornecedor_id, dados)
