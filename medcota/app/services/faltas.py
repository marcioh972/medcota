import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..core.config import settings
from ..core.errors import erro
from ..core.timeutils import agora_local, hoje
from ..enums import StatusFalta, Urgencia
from ..models import Falta, Produto, Usuario
from ..schemas.faltas import FaltaIn
from . import auditoria

logger = logging.getLogger(__name__)

STATUS_ABERTOS = (StatusFalta.pendente, StatusFalta.cotado)
_PESO_URGENCIA = {Urgencia.baixa: 0, Urgencia.media: 1, Urgencia.alta: 2}


def faltas_abertas_hoje(
    db: Session, empresa_id: int, produto_id: int | None = None, bloquear: bool = False
) -> list[Falta]:
    """Faltas de hoje da empresa ainda sem compra definida. `bloquear` => SELECT ... FOR UPDATE
    (efetivo no PostgreSQL; ignorado pelo SQLite)."""
    q = select(Falta).where(Falta.empresa_id == empresa_id, Falta.data == hoje(), Falta.status.in_(STATUS_ABERTOS))
    if produto_id is not None:
        q = q.where(Falta.produto_id == produto_id)
    if bloquear:
        q = q.with_for_update()
    return list(db.scalars(q))


def listar_hoje_do_vendedor(db: Session, vendedor: Usuario) -> list[Falta]:
    q = (
        select(Falta)
        .where(Falta.empresa_id == vendedor.empresa_id, Falta.vendedor_id == vendedor.id, Falta.data == hoje())
        .options(joinedload(Falta.produto))
        .order_by(Falta.id)
    )
    return list(db.scalars(q))


def lancar_falta(db: Session, vendedor: Usuario, dados: FaltaIn, somar_duplicata: bool) -> Falta:
    if agora_local().time() >= settings.horario_corte:  # RF-09
        raise erro(
            422,
            "lista_fechada",
            f"Lista do dia fechada (corte {settings.horario_corte:%H:%M}). Tente amanhã.",
        )
    produto = db.scalar(
        select(Produto).where(Produto.id == dados.produto_id, Produto.empresa_id == vendedor.empresa_id)
    )
    if produto is None:  # inexistente OU de outra empresa: mesma resposta
        raise erro(404, "produto_nao_encontrado", "Produto não encontrado")

    dia = hoje()
    existentes = list(
        db.scalars(
            select(Falta).where(
                Falta.empresa_id == vendedor.empresa_id,
                Falta.produto_id == dados.produto_id,
                Falta.data == dia,
            )
        )
    )
    if existentes and not somar_duplicata:
        acumulado = sum(f.quantidade for f in existentes)
        raise erro(
            409,
            "duplicata",
            f"Item já lançado hoje (demanda acumulada {acumulado} un).",
            somar_quantidade=True,
        )

    propria = next((f for f in existentes if f.vendedor_id == vendedor.id and f.cliente == dados.cliente), None)
    if propria:  # RF-08: soma na própria linha (mesmo vendedor + cliente + produto)
        propria.quantidade += dados.quantidade
        falta = propria
        auditoria.registrar(db, vendedor.empresa_id, vendedor.id, "somou_quantidade", "falta", falta.id)
    else:
        falta = Falta(
            empresa_id=vendedor.empresa_id,
            produto_id=dados.produto_id,
            vendedor_id=vendedor.id,
            data=dia,
            cliente=dados.cliente,
            quantidade=dados.quantidade,
            urgencia=dados.urgencia,
            observacao=dados.observacao,
            aceita_alternativa=dados.aceita_alternativa,
        )
        db.add(falta)
        db.flush()
        auditoria.registrar(
            db,
            vendedor.empresa_id,
            vendedor.id,
            "lancou_falta",
            "falta",
            falta.id,
            f"{dados.quantidade} un · {dados.cliente}",
        )
    try:
        db.commit()
    except IntegrityError:  # corrida entre duas requisições idênticas
        db.rollback()
        raise erro(409, "duplicata", "Item já lançado hoje para este cliente.") from None
    return falta


@dataclass
class Consolidado:
    produto: Produto
    demanda: int = 0
    solicitantes: set[str] = field(default_factory=set)
    clientes: set[str] = field(default_factory=set)
    urgencia: Urgencia = Urgencia.baixa


def consolidar_hoje(db: Session, empresa_id: int) -> list[Consolidado]:
    """RF-13/14: demanda de hoje agrupada por produto (uma consulta, sem N+1)."""
    q = (
        select(Falta)
        .where(Falta.empresa_id == empresa_id, Falta.data == hoje())
        .options(joinedload(Falta.produto), joinedload(Falta.vendedor))
    )
    grupos: dict[int, Consolidado] = {}
    for f in db.scalars(q):
        g = grupos.setdefault(f.produto_id, Consolidado(produto=f.produto))
        g.demanda += f.quantidade
        g.solicitantes.add(f.vendedor.nome)
        g.clientes.add(f.cliente)
        if _PESO_URGENCIA[f.urgencia] > _PESO_URGENCIA[g.urgencia]:
            g.urgencia = f.urgencia
    return sorted(grupos.values(), key=lambda g: -g.demanda)
