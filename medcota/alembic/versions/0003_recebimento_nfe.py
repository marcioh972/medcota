"""recebimento e conferência de NF-e: pedido manual, XML da nota, apontamentos e configuração fiscal

- fornecedores: CNPJ (casa com o emitente da nota) e marcação de credenciado (Decreto AL 72.101/2020);
- pedidos: origem (cotação/manual), situação de recebimento, frete previsto, nº externo e observação;
- nfe_entradas: dados extraídos do XML, resultado da conferência e decisão do comprador;
- nfe_apontamentos e configuracoes_fiscais: novas tabelas (por empresa).

Pedidos e notas já existentes continuam válidos: os novos campos NOT NULL têm valor padrão.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NFE_COLUNAS = [
    ("importada_por", sa.Integer(), None),
    ("numero", sa.String(9), None),
    ("serie", sa.String(3), None),
    ("data_emissao", sa.DateTime(), None),
    ("emitente_cnpj", sa.String(14), None),
    ("emitente_nome", sa.String(150), None),
    ("emitente_uf", sa.String(2), None),
    ("emitente_municipio", sa.String(7), None),
    ("destinatario_cnpj", sa.String(14), None),
    ("valor_total", sa.Numeric(14, 2), None),
    ("valor_frete", sa.Numeric(14, 2), None),
    ("protocolo_status", sa.String(3), None),
    ("resultado", sa.String(30), "aprovada"),
    ("versao_regras", sa.String(20), None),
    ("analisada_em", sa.DateTime(), None),
    ("decisao", sa.String(30), "pendente"),
    ("decisao_por", sa.Integer(), None),
    ("decisao_em", sa.DateTime(), None),
    ("justificativa", sa.Text(), ""),
]


def upgrade() -> None:
    with op.batch_alter_table("fornecedores") as batch:
        batch.add_column(sa.Column("cnpj", sa.String(14), nullable=True))
        batch.add_column(sa.Column("credenciado_72101", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_fornecedores_cnpj", ["cnpj"])
        batch.create_unique_constraint("uq_fornecedor_empresa_cnpj", ["empresa_id", "cnpj"])

    with op.batch_alter_table("pedidos") as batch:
        batch.add_column(sa.Column("origem", sa.String(30), nullable=False, server_default="cotacao"))
        batch.add_column(sa.Column("recebimento", sa.String(30), nullable=False, server_default="aguardando_nfe"))
        batch.add_column(sa.Column("numero_externo", sa.String(40), nullable=True))
        batch.add_column(sa.Column("frete_previsto", sa.Numeric(14, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("observacao", sa.Text(), nullable=False, server_default=""))

    with op.batch_alter_table("nfe_entradas") as batch:
        for nome, tipo, padrao in NFE_COLUNAS:
            batch.add_column(
                sa.Column(nome, tipo, nullable=padrao is None, server_default=None if padrao is None else padrao)
            )
        batch.create_foreign_key("fk_nfe_importada_por", "usuarios", ["importada_por"], ["id"])
        batch.create_foreign_key("fk_nfe_decisao_por", "usuarios", ["decisao_por"], ["id"])
        batch.create_index("ix_nfe_entradas_pedido_id", ["pedido_id"])

    op.create_table(
        "nfe_apontamentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("nfe_id", sa.Integer(), sa.ForeignKey("nfe_entradas.id"), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("severidade", sa.String(30), nullable=False),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("item_numero", sa.Integer(), nullable=True),
        sa.Column("campo", sa.String(60), nullable=True),
        sa.Column("esperado", sa.String(120), nullable=True),
        sa.Column("encontrado", sa.String(120), nullable=True),
        sa.Column("base_legal", sa.String(200), nullable=True),
    )
    op.create_index("ix_nfe_apontamentos_empresa_id", "nfe_apontamentos", ["empresa_id"])
    op.create_index("ix_nfe_apontamentos_nfe_id", "nfe_apontamentos", ["nfe_id"])

    op.create_table(
        "configuracoes_fiscais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("aliquota_interna_icms", sa.Numeric(5, 2), nullable=True),
        sa.Column("tolerancia_preco_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("frete_zero_municipios", sa.String(200), nullable=False, server_default="2704302"),
        sa.Column("exigir_protocolo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("atualizada_em", sa.DateTime(), nullable=True),
        sa.Column("atualizada_por", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.UniqueConstraint("empresa_id", name="uq_config_fiscal_empresa"),
    )
    op.create_index("ix_configuracoes_fiscais_empresa_id", "configuracoes_fiscais", ["empresa_id"])


def downgrade() -> None:
    op.drop_index("ix_configuracoes_fiscais_empresa_id", table_name="configuracoes_fiscais")
    op.drop_table("configuracoes_fiscais")
    op.drop_index("ix_nfe_apontamentos_nfe_id", table_name="nfe_apontamentos")
    op.drop_index("ix_nfe_apontamentos_empresa_id", table_name="nfe_apontamentos")
    op.drop_table("nfe_apontamentos")

    with op.batch_alter_table("nfe_entradas") as batch:
        batch.drop_index("ix_nfe_entradas_pedido_id")
        batch.drop_constraint("fk_nfe_decisao_por", type_="foreignkey")
        batch.drop_constraint("fk_nfe_importada_por", type_="foreignkey")
        for nome, _tipo, _padrao in reversed(NFE_COLUNAS):
            batch.drop_column(nome)

    with op.batch_alter_table("pedidos") as batch:
        for nome in ("observacao", "frete_previsto", "numero_externo", "recebimento", "origem"):
            batch.drop_column(nome)

    with op.batch_alter_table("fornecedores") as batch:
        batch.drop_constraint("uq_fornecedor_empresa_cnpj", type_="unique")
        batch.drop_index("ix_fornecedores_cnpj")
        batch.drop_column("credenciado_72101")
        batch.drop_column("cnpj")
