from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.timeutils import hoje
from ..enums import StatusFalta, StatusPedido
from ..models import Falta, Pedido, PedidoItem, PrecoHistorico


@dataclass
class Indicadores:
    economia_gerada: Decimal
    taxa_atendimento: float
    itens_em_falta: int
    pedidos: int


def indicadores(db: Session, empresa_id: int) -> Indicadores:
    status_hoje = list(db.scalars(select(Falta.status).where(Falta.empresa_id == empresa_id, Falta.data == hoje())))
    atendidos = sum(1 for s in status_hoje if s == StatusFalta.comprado)

    # média histórica UMA vez por produto (evita multiplicar linhas no join)
    media_sq = (
        select(PrecoHistorico.produto_id.label("pid"), func.avg(PrecoHistorico.preco).label("media"))
        .where(PrecoHistorico.empresa_id == empresa_id)
        .group_by(PrecoHistorico.produto_id)
        .subquery()
    )
    economia = (
        db.scalar(
            select(func.coalesce(func.sum(PedidoItem.quantidade * media_sq.c.media - PedidoItem.custo_final), 0))
            .select_from(PedidoItem)
            .join(media_sq, media_sq.c.pid == PedidoItem.produto_id)
            .join(Pedido, Pedido.id == PedidoItem.pedido_id)
            .where(Pedido.empresa_id == empresa_id, Pedido.status != StatusPedido.reprovado)
        )
        or 0
    )

    return Indicadores(
        economia_gerada=Decimal(str(economia)).quantize(Decimal("0.01")),
        taxa_atendimento=round(atendidos / len(status_hoje) * 100, 1) if status_hoje else 0.0,
        itens_em_falta=len(status_hoje),
        pedidos=db.scalar(select(func.count(Pedido.id)).where(Pedido.empresa_id == empresa_id)) or 0,
    )
