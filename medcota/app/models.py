"""MedCota — modelo de dados (SQLAlchemy 2.x tipado).

Cobertura por requisito:
- RF-01..04  auth, perfis, auditoria
- RF-05..12  faltas (lista diária do vendedor)
- RF-13..20  consolidação, cotação por token único, respostas, histórico de preços
- RF-24      alçada de aprovação
- RF-25..29  NFeEntrada (Fase 2, chave de acesso única p/ RN-05)

Dinheiro é sempre Numeric/Decimal (nunca float).

Multi-empresa (SaaS): `Empresa` é o tenant. Toda tabela com dados de negócio herda `TenantMixin`
(coluna `empresa_id` NOT NULL + índice) e TODA consulta precisa filtrar por ela. As tabelas-filhas
(`cotacao_itens`, `respostas`, `pedido_itens`) herdam o tenant do pai e só são acessadas através dele.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import false as sa_false
from sqlalchemy import true as sa_true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.database import Base
from .core.timeutils import agora_utc, hoje
from .enums import (
    ClasseProduto,
    DecisaoNFe,
    Escopo,
    OrigemPedido,
    Pagamento,
    Perfil,
    ResultadoNFe,
    Severidade,
    StatusFalta,
    StatusPedido,
    StatusRecebimento,
    Urgencia,
)

PRECO = Numeric(12, 4)  # preço unitário
VALOR = Numeric(14, 2)  # totais e custos


def enum_col(enum_cls):
    """Guarda o *valor* do enum em VARCHAR (sem tipo nativo => migrações simples)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=30,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )


class TenantMixin:
    """Marca a tabela como pertencente a uma empresa (tenant)."""

    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)


class Empresa(Base):
    """Tenant do SaaS. Criada no cadastro pelo gestor; funcionários entram com o código de validação."""

    __tablename__ = "empresas"
    __table_args__ = (
        UniqueConstraint("cnpj", name="uq_empresas_cnpj"),
        UniqueConstraint("codigo_validacao", name="uq_empresas_codigo_validacao"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    cnpj: Mapped[str | None] = mapped_column(String(14))  # normalizado; nulo só em dados legados
    # Código único por empresa (12 caracteres, sem 0/O/1/I). Nulo = ninguém consegue se cadastrar.
    codigo_validacao: Mapped[str | None] = mapped_column(String(16))
    codigo_expira_em: Mapped[datetime | None] = mapped_column(DateTime)
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)


class Usuario(TenantMixin, Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[Perfil] = mapped_column(enum_col(Perfil))
    ver_preco_custo: Mapped[bool] = mapped_column(default=False)  # RN-04: granular por usuário
    ativo: Mapped[bool] = mapped_column(default=True)
    falhas_login: Mapped[int] = mapped_column(default=0)  # RF-03
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime)

    empresa: Mapped[Empresa] = relationship()


class Produto(TenantMixin, Base):
    __tablename__ = "produtos"
    __table_args__ = (UniqueConstraint("empresa_id", "ean", name="uq_produto_ean_empresa"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    principio_ativo: Mapped[str] = mapped_column(String(200), default="")
    ean: Mapped[str | None] = mapped_column(String(13), index=True)
    classe: Mapped[ClasseProduto] = mapped_column(enum_col(ClasseProduto), default=ClasseProduto.farma)  # RF-06
    origem: Mapped[Escopo] = mapped_column(enum_col(Escopo), default=Escopo.local)  # RF-14/RN-02
    ncm: Mapped[str] = mapped_column(String(10), default="")
    cest: Mapped[str] = mapped_column(String(10), default="")
    controlado: Mapped[bool] = mapped_column(default=False)  # RN-08: Portaria 344/98
    estoque_atual: Mapped[int] = mapped_column(default=0)  # Fase 3/4


class Fornecedor(TenantMixin, Base):
    __tablename__ = "fornecedores"
    __table_args__ = (UniqueConstraint("empresa_id", "cnpj", name="uq_fornecedor_empresa_cnpj"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    escopo: Mapped[Escopo] = mapped_column(enum_col(Escopo), default=Escopo.nacional)  # RN-02
    email: Mapped[str] = mapped_column(String(120), default="")
    cnpj: Mapped[str | None] = mapped_column(String(14), index=True)  # normalizado; casa com o emitente da NF-e
    # Atacadista credenciado no tratamento do Decreto AL 72.101/2020 (informado pela empresa)
    credenciado_72101: Mapped[bool] = mapped_column(default=False, server_default=sa_false())
    avaliacao: Mapped[list["AvaliacaoFornecedor"]] = relationship(back_populates="fornecedor")


class Falta(TenantMixin, Base):
    __tablename__ = "faltas"
    __table_args__ = (
        UniqueConstraint("produto_id", "vendedor_id", "cliente", "data", name="uq_falta_dia"),
        CheckConstraint("quantidade > 0", name="ck_falta_quantidade_positiva"),
        Index("ix_falta_data_status", "data", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), index=True)
    vendedor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    cliente: Mapped[str] = mapped_column(String(150))
    quantidade: Mapped[int]
    urgencia: Mapped[Urgencia] = mapped_column(enum_col(Urgencia), default=Urgencia.media)
    observacao: Mapped[str] = mapped_column(Text, default="")
    aceita_alternativa: Mapped[bool] = mapped_column(default=True)
    data: Mapped[date] = mapped_column(Date, default=hoje)  # lista diária RF-09
    status: Mapped[StatusFalta] = mapped_column(enum_col(StatusFalta), default=StatusFalta.pendente)
    previsao: Mapped[datetime | None] = mapped_column(DateTime)
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"), index=True)

    produto: Mapped[Produto] = relationship()
    vendedor: Mapped[Usuario] = relationship()


class Cotacao(TenantMixin, Base):
    """Lista única gerada para UM fornecedor — link por token (RF-15 / RN-01)."""

    __tablename__ = "cotacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime)  # RN-01
    rodada: Mapped[int] = mapped_column(default=1)  # RF-19
    aberturas: Mapped[int] = mapped_column(default=0)  # RF-17
    lembretes: Mapped[int] = mapped_column(default=0)

    fornecedor: Mapped[Fornecedor] = relationship()
    itens: Mapped[list["CotacaoItem"]] = relationship(back_populates="cotacao", cascade="all, delete-orphan")


class CotacaoItem(Base):
    __tablename__ = "cotacao_itens"
    id: Mapped[int] = mapped_column(primary_key=True)
    cotacao_id: Mapped[int] = mapped_column(ForeignKey("cotacoes.id"), index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    quantidade: Mapped[int]  # demanda consolidada RF-13

    cotacao: Mapped[Cotacao] = relationship(back_populates="itens")
    produto: Mapped[Produto] = relationship()
    resposta: Mapped["Resposta | None"] = relationship(
        back_populates="item", uselist=False, cascade="all, delete-orphan"
    )


class Resposta(Base):
    __tablename__ = "respostas"
    __table_args__ = (
        CheckConstraint("preco > 0", name="ck_resposta_preco_positivo"),
        CheckConstraint("quantidade > 0", name="ck_resposta_quantidade_positiva"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("cotacao_itens.id"), unique=True)
    preco: Mapped[Decimal] = mapped_column(PRECO)
    quantidade: Mapped[int]
    prazo_dias: Mapped[int]
    pagamento: Mapped[Pagamento] = mapped_column(enum_col(Pagamento))
    lote: Mapped[str] = mapped_column(String(40), default="")
    validade: Mapped[datetime | None] = mapped_column(DateTime)
    respondida_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)

    item: Mapped[CotacaoItem] = relationship(back_populates="resposta")


class Pedido(TenantMixin, Base):
    __tablename__ = "pedidos"
    id: Mapped[int] = mapped_column(primary_key=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    criado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    total: Mapped[Decimal] = mapped_column(VALOR, default=Decimal("0"))
    status: Mapped[StatusPedido] = mapped_column(enum_col(StatusPedido), default=StatusPedido.aprovado)  # RN-06
    aprovado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    aprovado_em: Mapped[datetime | None] = mapped_column(DateTime)
    # Recebimento / conferência da NF-e
    origem: Mapped[OrigemPedido] = mapped_column(
        enum_col(OrigemPedido), default=OrigemPedido.cotacao, server_default="cotacao"
    )
    recebimento: Mapped[StatusRecebimento] = mapped_column(
        enum_col(StatusRecebimento), default=StatusRecebimento.aguardando_nfe, server_default="aguardando_nfe"
    )
    numero_externo: Mapped[str | None] = mapped_column(String(40))  # nº do pedido no fornecedor/ERP
    frete_previsto: Mapped[Decimal] = mapped_column(VALOR, default=Decimal("0"), server_default="0")
    observacao: Mapped[str] = mapped_column(Text, default="", server_default="")

    itens: Mapped[list["PedidoItem"]] = relationship(back_populates="pedido", cascade="all, delete-orphan")


class PedidoItem(Base):
    __tablename__ = "pedido_itens"
    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"))
    quantidade: Mapped[int]
    preco: Mapped[Decimal] = mapped_column(PRECO)
    custo_final: Mapped[Decimal] = mapped_column(VALOR)  # RN-03

    pedido: Mapped[Pedido] = relationship(back_populates="itens")


class PrecoHistorico(TenantMixin, Base):
    """RF-20: média histórica por item e fornecedor + alerta de preço alto."""

    __tablename__ = "preco_historico"
    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), index=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"))
    preco: Mapped[Decimal] = mapped_column(PRECO)
    registrado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)


class AvaliacaoFornecedor(TenantMixin, Base):
    """RF-39 (Fase 4): preço, prazo, entrega completa, divergências."""

    __tablename__ = "avaliacoes_fornecedor"
    id: Mapped[int] = mapped_column(primary_key=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"))
    nota_preco: Mapped[float] = mapped_column(default=0)
    nota_prazo: Mapped[float] = mapped_column(default=0)
    nota_entrega: Mapped[float] = mapped_column(default=0)
    periodo: Mapped[str] = mapped_column(String(7), default="")  # "2026-09"

    fornecedor: Mapped[Fornecedor] = relationship(back_populates="avaliacao")


class NFeEntrada(TenantMixin, Base):
    """NF-e de entrada (RF-25..29). RN-05: a chave de acesso é a chave anti-duplicidade (por empresa).

    Guarda o XML original e o resultado da conferência fiscal contra o pedido.
    """

    __tablename__ = "nfe_entradas"
    __table_args__ = (UniqueConstraint("empresa_id", "chave_acesso", name="uq_nfe_chave_empresa"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    chave_acesso: Mapped[str] = mapped_column(String(44), index=True)
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("fornecedores.id"))
    xml: Mapped[str] = mapped_column(Text)
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="recebida")  # recebida|conciliada|divergente
    importada_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    importada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    # Dados extraídos do XML
    numero: Mapped[str | None] = mapped_column(String(9))
    serie: Mapped[str | None] = mapped_column(String(3))
    data_emissao: Mapped[datetime | None] = mapped_column(DateTime)
    emitente_cnpj: Mapped[str | None] = mapped_column(String(14))
    emitente_nome: Mapped[str | None] = mapped_column(String(150))
    emitente_uf: Mapped[str | None] = mapped_column(String(2))
    emitente_municipio: Mapped[str | None] = mapped_column(String(7))  # código IBGE
    destinatario_cnpj: Mapped[str | None] = mapped_column(String(14))
    valor_total: Mapped[Decimal | None] = mapped_column(VALOR)
    valor_frete: Mapped[Decimal | None] = mapped_column(VALOR)
    protocolo_status: Mapped[str | None] = mapped_column(String(3))  # cStat do protNFe (100 = autorizada)

    # Conferência
    resultado: Mapped[ResultadoNFe] = mapped_column(
        enum_col(ResultadoNFe), default=ResultadoNFe.aprovada, server_default="aprovada"
    )
    versao_regras: Mapped[str | None] = mapped_column(String(20))
    analisada_em: Mapped[datetime | None] = mapped_column(DateTime)
    decisao: Mapped[DecisaoNFe] = mapped_column(
        enum_col(DecisaoNFe), default=DecisaoNFe.pendente, server_default="pendente"
    )
    decisao_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    decisao_em: Mapped[datetime | None] = mapped_column(DateTime)
    justificativa: Mapped[str] = mapped_column(Text, default="", server_default="")

    fornecedor: Mapped[Fornecedor | None] = relationship()
    apontamentos: Mapped[list["NFeApontamento"]] = relationship(
        back_populates="nfe", cascade="all, delete-orphan", order_by="NFeApontamento.ordem"
    )


class NFeApontamento(TenantMixin, Base):
    """Uma constatação da conferência (erro, alerta ou informação) sobre uma NF-e."""

    __tablename__ = "nfe_apontamentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nfe_id: Mapped[int] = mapped_column(ForeignKey("nfe_entradas.id"), index=True)
    ordem: Mapped[int] = mapped_column(default=0)
    severidade: Mapped[Severidade] = mapped_column(enum_col(Severidade))
    codigo: Mapped[str] = mapped_column(String(40))
    mensagem: Mapped[str] = mapped_column(Text)
    item_numero: Mapped[int | None]  # nItem da nota; None = a nota inteira
    campo: Mapped[str | None] = mapped_column(String(60))
    esperado: Mapped[str | None] = mapped_column(String(120))
    encontrado: Mapped[str | None] = mapped_column(String(120))
    base_legal: Mapped[str | None] = mapped_column(String(200))

    nfe: Mapped[NFeEntrada] = relationship(back_populates="apontamentos")


class ConfiguracaoFiscal(TenantMixin, Base):
    """Parâmetros da conferência fiscal, por empresa. O gestor/contador mantém os valores vigentes."""

    __tablename__ = "configuracoes_fiscais"
    __table_args__ = (UniqueConstraint("empresa_id", name="uq_config_fiscal_empresa"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    # Alíquota interna de ICMS (%) das operações dentro do mesmo estado. Sem valor = não validar.
    aliquota_interna_icms: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # Tolerância (%) entre o preço do pedido e o da nota.
    tolerancia_preco_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), server_default="0")
    # Códigos IBGE de municípios de fornecedores que NÃO cobram frete na nota (padrão: Maceió/AL).
    frete_zero_municipios: Mapped[str] = mapped_column(String(200), default="2704302", server_default="2704302")
    exigir_protocolo: Mapped[bool] = mapped_column(default=True, server_default=sa_true())
    atualizada_em: Mapped[datetime | None] = mapped_column(DateTime)
    atualizada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))


class Auditoria(TenantMixin, Base):
    """RF-04: toda alteração relevante."""

    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    acao: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str] = mapped_column(String(60))
    entidade_id: Mapped[str] = mapped_column(String(40), default="")
    detalhe: Mapped[str] = mapped_column(Text, default="")
