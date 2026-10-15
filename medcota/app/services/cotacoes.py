import logging
import secrets
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..core.config import settings
from ..core.errors import erro
from ..core.timeutils import agora_utc, inicio_do_dia_utc
from ..enums import StatusFalta
from ..models import Cotacao, CotacaoItem, Fornecedor, PrecoHistorico, Produto, Resposta, Usuario
from ..schemas.cotacoes import RespostaIn
from . import auditoria
from .faltas import faltas_abertas_hoje

logger = logging.getLogger(__name__)

_CARGA = (
    selectinload(Cotacao.fornecedor),
    selectinload(Cotacao.itens).selectinload(CotacaoItem.resposta),
    selectinload(Cotacao.itens).selectinload(CotacaoItem.produto),
)


def gerar_cotacoes(db: Session, comprador: Usuario) -> list[Cotacao]:
    """RF-13..15 + RN-01 + RN-02: uma lista por fornecedor, escopo Local/Nacional separado."""
    empresa_id = comprador.empresa_id
    faltas = faltas_abertas_hoje(db, empresa_id)
    demanda: dict[int, int] = defaultdict(int)
    for f in faltas:
        demanda[f.produto_id] += f.quantidade
    if not demanda:
        raise erro(422, "sem_faltas", "Sem faltas abertas hoje")

    produtos = {
        p.id: p for p in db.scalars(select(Produto).where(Produto.empresa_id == empresa_id, Produto.id.in_(demanda)))
    }
    # evita gerar de novo o que já foi enviado hoje ao mesmo fornecedor
    ja_enviados = set(
        db.execute(
            select(Cotacao.fornecedor_id, CotacaoItem.produto_id)
            .join(CotacaoItem, CotacaoItem.cotacao_id == Cotacao.id)
            .where(Cotacao.empresa_id == empresa_id, Cotacao.criada_em >= inicio_do_dia_utc())
        ).all()
    )

    criadas: list[Cotacao] = []
    cotados: set[int] = set()
    for fornecedor in db.scalars(select(Fornecedor).where(Fornecedor.empresa_id == empresa_id)):
        itens = [
            CotacaoItem(produto_id=pid, quantidade=q)
            for pid, q in demanda.items()
            if produtos[pid].origem == fornecedor.escopo  # RN-02
            and (fornecedor.id, pid) not in ja_enviados
        ]
        if not itens:
            continue
        cotacao = Cotacao(
            empresa_id=empresa_id,
            fornecedor=fornecedor,
            token=secrets.token_urlsafe(24),
            expira_em=agora_utc() + timedelta(hours=settings.validade_cotacao_h),
            itens=itens,
        )
        db.add(cotacao)
        criadas.append(cotacao)
        cotados.update(i.produto_id for i in itens)

    if not criadas:
        raise erro(
            409,
            "cotacoes_ja_geradas",
            "Não há itens novos para cotar (ou nenhum fornecedor do escopo adequado).",
        )

    for f in faltas:
        if f.status == StatusFalta.pendente and f.produto_id in cotados:
            f.status = StatusFalta.cotado
    db.flush()
    for c in criadas:
        auditoria.registrar(
            db, empresa_id, comprador.id, "gerou_cotacao", "cotacao", c.id, f"fornecedor {c.fornecedor_id}"
        )
    db.commit()
    logger.info("cotacoes geradas qtd=%s empresa_id=%s", len(criadas), empresa_id)
    return criadas


def listar_cotacoes(db: Session, empresa_id: int, limit: int, offset: int) -> list[Cotacao]:
    q = (
        select(Cotacao)
        .where(Cotacao.empresa_id == empresa_id)
        .options(*_CARGA)
        .order_by(Cotacao.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(q))


def cotacao_por_token(db: Session, token: str) -> Cotacao:
    """Rota pública: o token (192 bits) identifica a cotação e, por ela, a empresa."""
    c = db.scalar(select(Cotacao).where(Cotacao.token == token).options(*_CARGA))
    if not c:
        raise erro(404, "link_invalido", "Link inválido")
    if c.expira_em < agora_utc():  # RN-01
        raise erro(410, "link_expirado", "Link expirado. Solicite novo envio ao comprador.")
    return c


def registrar_abertura(db: Session, cotacao: Cotacao) -> None:
    cotacao.aberturas += 1  # RF-17
    db.commit()


def registrar_respostas(db: Session, cotacao: Cotacao, respostas: list[RespostaIn]) -> None:
    itens = {i.id: i for i in cotacao.itens}
    for r in respostas:
        item = itens.get(r.item_id)
        if item is None:
            raise erro(422, "item_invalido", f"Item {r.item_id} não pertence a esta cotação")
        campos = r.model_dump(exclude={"item_id"})
        if item.resposta:  # sobrescreve na 2ª rodada (RF-19)
            for k, v in campos.items():
                setattr(item.resposta, k, v)
            item.resposta.respondida_em = agora_utc()
        else:
            item.resposta = Resposta(**campos)
        db.add(
            PrecoHistorico(
                empresa_id=cotacao.empresa_id,
                produto_id=item.produto_id,
                fornecedor_id=cotacao.fornecedor_id,
                preco=r.preco,
            )
        )  # RF-20
    db.commit()


def segunda_rodada(db: Session, comprador: Usuario, cotacao_id: int) -> Cotacao:
    c = db.scalar(
        select(Cotacao).where(Cotacao.id == cotacao_id, Cotacao.empresa_id == comprador.empresa_id).options(*_CARGA)
    )
    if not c:  # inexistente OU de outra empresa: mesma resposta
        raise erro(404, "cotacao_nao_encontrada", "Cotação não encontrada")
    c.rodada += 1  # RF-19
    c.expira_em = agora_utc() + timedelta(hours=settings.validade_cotacao_h)  # reabre o link
    auditoria.registrar(db, comprador.empresa_id, comprador.id, "abriu_2a_rodada", "cotacao", c.id)
    db.commit()
    return c
