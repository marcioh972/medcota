"""Migrações: caminho completo, dados legados preservados e ausência de divergência com os modelos."""

import sqlite3

import pytest
from alembic.config import Config

from alembic import command


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'mig.db'}"
    monkeypatch.setattr("app.core.config.settings.database_url", url)
    c = Config("alembic.ini")
    c.set_main_option("script_location", "alembic")
    return c, tmp_path / "mig.db"


def test_upgrade_head_nao_diverge_dos_modelos(cfg):
    c, _ = cfg
    command.upgrade(c, "head")
    command.check(c)  # levanta se os modelos tiverem algo que as migrações não criam


def test_dados_legados_vao_para_a_empresa_padrao(cfg):
    c, db = cfg
    command.upgrade(c, "0001")
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO usuarios (nome,email,senha_hash,perfil,ver_preco_custo,ativo,falhas_login)"
        " VALUES ('Legado','l@x.com','h','gestor',1,1,0)"
    )
    con.execute(
        "INSERT INTO produtos (nome,principio_ativo,classe,origem,ncm,cest,controlado,estoque_atual)"
        " VALUES ('P','','Farma','Local','','',0,0)"
    )
    con.commit()
    con.close()

    command.upgrade(c, "head")

    con = sqlite3.connect(db)
    (empresa_id, nome, cnpj) = con.execute("SELECT id, nome, cnpj FROM empresas").fetchone()
    assert (nome, cnpj) == ("Empresa padrão", None)
    assert con.execute("SELECT empresa_id FROM usuarios").fetchone() == (empresa_id,)
    assert con.execute("SELECT empresa_id FROM produtos").fetchone() == (empresa_id,)
    con.close()


def test_banco_vazio_nao_cria_empresa_padrao(cfg):
    c, db = cfg
    command.upgrade(c, "head")
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM empresas").fetchone() == (0,)
    con.close()


def test_downgrade_completo(cfg):
    c, _ = cfg
    command.upgrade(c, "head")
    command.downgrade(c, "base")
