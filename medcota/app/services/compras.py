import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.errors import erro
from ..core.timeutils import agora_utc
from ..enums import StatusFalta, StatusPedido
from ..models import Falta, Pedido, PedidoItem, Usuario
from . import auditoria
from .comparativo import calcular_comparativo
from .faltas import faltas_abertas_hoje

logger = logging.getLogger(__name__)


def fechar_compra(db: Session, comprador: Usuario) -> Pedido:
    """Fecha a compra com os vencedores do comparativo (RN-03)."""
    empresa_id = comprador.empresa_id
    # Trava as faltas abertas: uma segunda requisição simultânea espera e depois
    # não encontra mais nada em aberto (PostgreSQL; no SQLite o lock é ignorado).
    faltas = faltas_abertas_hoje(db, empresa_id, bloquear=True)
    comparativo = calcular_comparativo(db, empresa_id)
    if not comparativo:
        raise erro(422, "sem_itens", "Não há itens cotados pendentes de compra")

    por_produto: dict[int, list[Falta]] = defaultdict(list)
    for f in faltas:
        por_produto[f.produto_id].append(f)

    itens: list[PedidoItem] = []
    compradas: list[tuple[Falta, int]] = []  # (falta, prazo_dias do vencedor)
    total = Decimal("0")
    for item in comparativo:
        vencedor = next((o for o in item.ofertas if o.vencedor), None)
        if vencedor is None:
            for f in por_produto[item.produto_id]:
                f.status = StatusFalta.sem_oferta
            continue
        itens.append(
            PedidoItem(
                produto_id=item.produto_id,
                fornecedor_id=vencedor.fornecedor_id,
                quantidade=item.demanda,
                preco=vencedor.preco,
                custo_final=vencedor.custo_final,
            )
        )
        total += vencedor.custo_final
        compradas.extend((f, vencedor.prazo_dias) for f in por_produto[item.produto_id])

    if not itens:
        db.commit()  # persiste as faltas marcadas como sem_oferta
        raise erro(
            422,
            "sem_oferta_valida",
            "Nenhuma oferta válida (quantidade insuficiente). Faltas marcadas como sem_oferta.",
        )

    pedido = Pedido(
        empresa_id=empresa_id,
        criado_por=comprador.id,
        total=total,
        itens=itens,
        status=(
            StatusPedido.aguardando_aprovacao if total > settings.alcada_aprovacao else StatusPedido.aprovado
        ),  # RN-06
    )
    db.add(pedido)
    db.flush()
    for f, prazo in compradas:
        f.status = StatusFalta.comprado  # RF-28
        f.pedido_id = pedido.id
        f.previsao = agora_utc() + timedelta(days=prazo)
    auditoria.registrar(
        db,
        empresa_id,
        comprador.id,
        "fechou_compra",
        "pedido",
        pedido.id,
        f"total {total} · {pedido.status.value}",
    )
    db.commit()
    logger.info(
        "pedido fechado id=%s empresa_id=%s total=%s status=%s",
        pedido.id,
        empresa_id,
        total,
        pedido.status.value,
    )
    return pedido


def aprovar_pedido(db: Session, gestor: Usuario, pedido_id: int, aprovado: bool) -> Pedido:
    p = db.scalar(
        select(Pedido).where(Pedido.id == pedido_id, Pedido.empresa_id == gestor.empresa_id).with_for_update()
    )
    if not p:  # inexistente OU de outra empresa: mesma resposta
        raise erro(404, "pedido_nao_encontrado", "Pedido não encontrado")
    if p.status != StatusPedido.aguardando_aprovacao:
        raise erro(
            409,
            "pedido_fora_de_alcada",
            f"Pedido não está aguardando aprovação (status atual: {p.status.value})",
        )
    p.status = StatusPedido.aprovado if aprovado else StatusPedido.reprovado
    p.aprovado_por, p.aprovado_em = gestor.id, agora_utc()
    if not aprovado:
        for f in db.scalars(select(Falta).where(Falta.empresa_id == gestor.empresa_id, Falta.pedido_id == p.id)):
            f.status = StatusFalta.sem_oferta
    auditoria.registrar(
        db, gestor.empresa_id, gestor.id, "aprovou_pedido" if aprovado else "reprovou_pedido", "pedido", p.id
    )
    db.commit()
    return p
