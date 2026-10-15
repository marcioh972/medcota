"""multiempresa (SaaS): tabela empresas + empresa_id em todas as tabelas de negócio

Dados existentes (instalações de empresa única) são movidos para uma empresa "Empresa padrão",
sem CNPJ, para que nada se perca. O gestor dessa instalação continua acessando normalmente.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABELAS_TENANT = [
    "usuarios",
    "produtos",
    "fornecedores",
    "faltas",
    "cotacoes",
    "pedidos",
    "preco_historico",
    "avaliacoes_fornecedor",
    "nfe_entradas",
    "auditoria",
]


def _empresa_padrao(conn) -> int | None:
    """Cria a empresa padrão só se já houver dados em alguma tabela de negócio."""
    tem_dados = any(conn.execute(sa.text(f"SELECT 1 FROM {t} LIMIT 1")).first() for t in TABELAS_TENANT)
    if not tem_dados:
        return None
    conn.execute(sa.text("INSERT INTO empresas (nome, criada_em) VALUES ('Empresa padrão', CURRENT_TIMESTAMP)"))
    return conn.execute(sa.text("SELECT MAX(id) FROM empresas")).scalar()


def upgrade() -> None:
    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("codigo_validacao", sa.String(length=16), nullable=True),
        sa.Column("codigo_expira_em", sa.DateTime(), nullable=True),
        sa.Column("criada_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cnpj", name="uq_empresas_cnpj"),
        sa.UniqueConstraint("codigo_validacao", name="uq_empresas_codigo_validacao"),
    )
    conn = op.get_bind()
    padrao = _empresa_padrao(conn)

    for tabela in TABELAS_TENANT:
        # 1) coluna nula  2) preenche com a empresa padrão  3) vira NOT NULL + FK nomeada + índice
        with op.batch_alter_table(tabela) as batch:
            batch.add_column(sa.Column("empresa_id", sa.Integer(), nullable=True))
        if padrao is not None:
            conn.execute(sa.text(f"UPDATE {tabela} SET empresa_id = :e"), {"e": padrao})
        with op.batch_alter_table(tabela) as batch:
            batch.alter_column("empresa_id", existing_type=sa.Integer(), nullable=False)
            batch.create_foreign_key(f"fk_{tabela}_empresa_id", "empresas", ["empresa_id"], ["id"])
            batch.create_index(f"ix_{tabela}_empresa_id", ["empresa_id"], unique=False)

    # EAN e chave da NF-e passam a ser únicos POR EMPRESA (antes eram únicos globalmente)
    with op.batch_alter_table("produtos") as batch:
        batch.drop_index("ix_produtos_ean")
        batch.create_index("ix_produtos_ean", ["ean"], unique=False)
        batch.create_unique_constraint("uq_produto_ean_empresa", ["empresa_id", "ean"])
    with op.batch_alter_table("nfe_entradas") as batch:
        batch.drop_index("ix_nfe_entradas_chave_acesso")
        batch.create_index("ix_nfe_entradas_chave_acesso", ["chave_acesso"], unique=False)
        batch.create_unique_constraint("uq_nfe_chave_empresa", ["empresa_id", "chave_acesso"])


def downgrade() -> None:
    # ATENÇÃO: se houver 2+ empresas, voltar a EAN/chave únicos globais pode falhar por duplicidade.
    with op.batch_alter_table("nfe_entradas") as batch:
        batch.drop_constraint("uq_nfe_chave_empresa", type_="unique")
        batch.drop_index("ix_nfe_entradas_chave_acesso")
        batch.create_index("ix_nfe_entradas_chave_acesso", ["chave_acesso"], unique=True)
    with op.batch_alter_table("produtos") as batch:
        batch.drop_constraint("uq_produto_ean_empresa", type_="unique")
        batch.drop_index("ix_produtos_ean")
        batch.create_index("ix_produtos_ean", ["ean"], unique=True)

    for tabela in reversed(TABELAS_TENANT):
        with op.batch_alter_table(tabela) as batch:
            batch.drop_index(f"ix_{tabela}_empresa_id")
            batch.drop_constraint(f"fk_{tabela}_empresa_id", type_="foreignkey")
            batch.drop_column("empresa_id")
    op.drop_table("empresas")
