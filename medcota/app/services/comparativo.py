"""RN-03: menor custo final = preço - desconto financeiro + rateio de frete."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..core.config import settings
from ..core.timeutils import hoje, inicio_do_dia_utc
from ..enums import Pagamento
from ..models import Cotacao, CotacaoItem, Falta, PrecoHistorico
from .faltas import STATUS_ABERTOS

DESCONTO_FINANCEIRO: dict[Pagamento, Decimal] = {
    Pagamento.a_vista: Decimal("0.05"),
    Pagamento.d15: Decimal("0.03"),
    Pagamento.d30: Decimal("0.015"),
    Pagamento.d45: Decimal("0"),
}
MARGEM_ALERTA_PRECO = Decimal("1.05")  # RF-20: >5% acima da média histórica


def _centavos(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def custo_final(preco: Decimal, qtd: int, pagamento: Pagamento, n_itens_cotacao: int) -> Decimal:
    frete_rateio = settings.frete_padrao / max(1, n_itens_cotacao)
    return _centavos(preco * qtd * (1 - DESCONTO_FINANCEIRO[pagamento]) + frete_rateio)


@dataclass(frozen=True)
class OfertaCalculada:
    fornecedor_id: int
    fornecedor: str
    preco: Decimal
    quantidade: int
    pagamento: Pagamento
    prazo_dias: int
    custo_final: Decimal
    acima_da_media: bool
    vencedor: bool


@dataclass(frozen=True)
class ItemComparado:
    produto_id: int
    produto: str
    demanda: int
    media_historica: Decimal | None
    ofertas: list[OfertaCalculada]

    @property
    def sem_oferta_valida(self) -> bool:
        return not any(o.vencedor for o in self.ofertas)


def calcular_comparativo(db: Session, empresa_id: int) -> list[ItemComparado]:
    """Compara, por produto com demanda aberta hoje, as respostas das cotações de hoje."""
    demandas = {
        pid: int(qtd)
        for pid, qtd in db.execute(
            select(Falta.produto_id, func.sum(Falta.quantidade))
            .where(
                Falta.empresa_id == empresa_id,
                Falta.data == hoje(),
                Falta.status.in_(STATUS_ABERTOS),
            )
            .group_by(Falta.produto_id)
        )
    }
    if not demandas:
        return []

    medias = {
        pid: Decimal(str(m))
        for pid, m in db.execute(
            select(PrecoHistorico.produto_id, func.avg(PrecoHistorico.preco))
            .where(PrecoHistorico.empresa_id == empresa_id)
            .group_by(PrecoHistorico.produto_id)
        )
        if m is not None
    }

    cotacoes = db.scalars(
        select(Cotacao)
        .where(Cotacao.empresa_id == empresa_id, Cotacao.criada_em >= inicio_do_dia_utc())
        .options(
            selectinload(Cotacao.fornecedor),
            selectinload(Cotacao.itens).selectinload(CotacaoItem.resposta),
            selectinload(Cotacao.itens).selectinload(CotacaoItem.produto),
        )
    )

    respondidos: dict[int, list[tuple[Cotacao, CotacaoItem]]] = defaultdict(list)
    for c in cotacoes:
        for item in c.itens:
            if item.resposta and item.produto_id in demandas:
                respondidos[item.produto_id].append((c, item))

    resultado: list[ItemComparado] = []
    for pid, pares in respondidos.items():
        demanda = demandas[pid]
        media = medias.get(pid)
        brutas = []
        for c, item in pares:
            r = item.resposta
            brutas.append((c, r, custo_final(r.preco, demanda, r.pagamento, len(c.itens))))
        # só concorre quem entrega a quantidade necessária; desempate: menor prazo
        validas = [b for b in brutas if b[1].quantidade >= demanda]
        melhor = min(validas, key=lambda b: (b[2], b[1].prazo_dias)) if validas else None
        ofertas = [
            OfertaCalculada(
                fornecedor_id=c.fornecedor_id,
                fornecedor=c.fornecedor.nome,
                preco=r.preco,
                quantidade=r.quantidade,
                pagamento=r.pagamento,
                prazo_dias=r.prazo_dias,
                custo_final=custo,
                vencedor=(melhor is not None and r is melhor[1]),
                acima_da_media=bool(media and r.preco > media * MARGEM_ALERTA_PRECO),
            )
            for c, r, custo in brutas
        ]
        resultado.append(
            ItemComparado(
                produto_id=pid,
                produto=pares[0][1].produto.nome,
                demanda=demanda,
                media_historica=media,
                ofertas=ofertas,
            )
        )
    return sorted(resultado, key=lambda i: -i.demanda)
