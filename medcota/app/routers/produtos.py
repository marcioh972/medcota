from typing import Annotated

from fastapi import APIRouter, Query

from ..core.deps import CompradorOuGestor, DbSession, UsuarioLogado
from ..schemas.produtos import ProdutoIn, ProdutoOut
from ..services import catalogo

router = APIRouter(prefix="/produtos", tags=["catálogo"])


@router.get("", response_model=list[ProdutoOut])
def buscar_produtos(
    u: UsuarioLogado,
    db: DbSession,
    q: Annotated[str, Query(max_length=100, description="Nome, princípio ativo ou EAN")] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    """RF-05: busca para o lançamento de faltas (autocomplete). Só produtos da empresa do usuário."""
    return catalogo.buscar_produtos(db, u.empresa_id, q, limit)


@router.post("", response_model=ProdutoOut, status_code=201)
def criar_produto(dados: ProdutoIn, u: CompradorOuGestor, db: DbSession):
    return catalogo.criar_produto(db, u, dados)
