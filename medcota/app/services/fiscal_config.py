"""Parâmetros da conferência fiscal por empresa (alíquota interna, tolerância, municípios sem frete)."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.timeutils import agora_utc
from ..models import ConfiguracaoFiscal, Usuario
from ..schemas.recebimento import ConfiguracaoFiscalIn, ConfiguracaoFiscalOut
from . import auditoria
from .fiscal.tipos import ConfigCtx

PADRAO_MUNICIPIOS = "2704302"  # Maceió/AL


def _linha(db: Session, empresa_id: int) -> ConfiguracaoFiscal | None:
    return db.scalar(select(ConfiguracaoFiscal).where(ConfiguracaoFiscal.empresa_id == empresa_id))


def _municipios(texto: str) -> list[str]:
    return [m for m in (p.strip() for p in texto.split(",")) if m]


def contexto(db: Session, empresa_id: int) -> ConfigCtx:
    """Configuração para o motor de regras; sem registro, vale o padrão."""
    c = _linha(db, empresa_id)
    if c is None:
        return ConfigCtx()
    return ConfigCtx(
        aliquota_interna_icms=c.aliquota_interna_icms,
        tolerancia_preco_pct=Decimal(c.tolerancia_preco_pct),
        frete_zero_municipios=frozenset(_municipios(c.frete_zero_municipios)),
        exigir_protocolo=c.exigir_protocolo,
    )


def obter(db: Session, empresa_id: int) -> ConfiguracaoFiscalOut:
    c = _linha(db, empresa_id)
    if c is None:
        return ConfiguracaoFiscalOut()
    return ConfiguracaoFiscalOut(
        aliquota_interna_icms=c.aliquota_interna_icms,
        tolerancia_preco_pct=c.tolerancia_preco_pct,
        frete_zero_municipios=_municipios(c.frete_zero_municipios),
        exigir_protocolo=c.exigir_protocolo,
        atualizada_em=c.atualizada_em,
    )


def atualizar(db: Session, gestor: Usuario, dados: ConfiguracaoFiscalIn) -> ConfiguracaoFiscalOut:
    c = _linha(db, gestor.empresa_id)
    if c is None:
        c = ConfiguracaoFiscal(empresa_id=gestor.empresa_id)
        db.add(c)
    c.aliquota_interna_icms = dados.aliquota_interna_icms
    c.tolerancia_preco_pct = dados.tolerancia_preco_pct
    c.frete_zero_municipios = ",".join(dict.fromkeys(dados.frete_zero_municipios))
    c.exigir_protocolo = dados.exigir_protocolo
    c.atualizada_em = agora_utc()
    c.atualizada_por = gestor.id
    auditoria.registrar(
        db,
        gestor.empresa_id,
        gestor.id,
        "atualizou_config_fiscal",
        "configuracao_fiscal",
        c.id or "",
        f"aliquota_interna={dados.aliquota_interna_icms}, tolerancia={dados.tolerancia_preco_pct}%",
    )
    db.commit()
    return obter(db, gestor.empresa_id)
