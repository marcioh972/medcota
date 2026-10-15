from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..core.deps import Comprador, CompradorOuGestor, DbSession, Gestor
from ..models import Pedido
from ..schemas.pedidos import PedidoItemOut, PedidoOut
from ..services import compras

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


def pedido_out(p: Pedido, ver_preco: bool) -> PedidoOut:
    """RN-04: sem a permissão ver_preco_custo, valores monetários vêm nulos."""
    return PedidoOut(
        id=p.id,
        criado_em=p.criado_em,
        status=p.status,
        total=p.total if ver_preco else None,
        itens=[
            PedidoItemOut(
                produto_id=i.produto_id,
                fornecedor_id=i.fornecedor_id,
                quantidade=i.quantidade,
                preco=i.preco if ver_preco else None,
                custo_final=i.custo_final if ver_preco else None,
            )
            for i in p.itens
        ],
    )


@router.post("", response_model=PedidoOut, status_code=201)
def fechar_compra(u: Comprador, db: DbSession):
    return pedido_out(compras.fechar_compra(db, u), u.ver_preco_custo)


@router.get("", response_model=list[PedidoOut])
def listar_pedidos(
    u: CompradorOuGestor,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    q = (
        select(Pedido)
        .where(Pedido.empresa_id == u.empresa_id)
        .options(selectinload(Pedido.itens))
        .order_by(Pedido.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return [pedido_out(p, u.ver_preco_custo) for p in db.scalars(q)]


@router.post("/{pedido_id}/aprovar", response_model=PedidoOut)
def aprovar_pedido(pedido_id: int, aprovado: bool, u: Gestor, db: DbSession):
    return pedido_out(compras.aprovar_pedido(db, u, pedido_id, aprovado), u.ver_preco_custo)
