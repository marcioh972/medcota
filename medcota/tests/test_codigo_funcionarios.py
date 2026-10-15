import re
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.timeutils import agora_utc
from app.models import Empresa
from tests.conftest import CNPJ_B, SENHA, login

PADRAO_CODIGO = re.compile(r"^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$")


def nova_empresa(client, nome="Empresa Alfa", cnpj="11222333000181", email="gestor@alfa.com.br"):
    """Cadastra a empresa pela API e devolve os headers do gestor."""
    r = client.post(
        "/cadastro/empresa",
        json={
            "empresa_nome": nome,
            "cnpj": cnpj,
            "gestor_nome": "Gestor Alfa",
            "email": email,
            "senha": SENHA,
        },
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def gerar_codigo(client, headers) -> str:
    r = client.post("/empresa/codigo", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["codigo_validacao"]


def cadastrar(client, codigo, email="func@alfa.com.br", perfil="comprador", senha=SENHA, nome="Funcionário"):
    return client.post(
        "/cadastro/funcionario",
        json={"codigo": codigo, "nome": nome, "email": email, "senha": senha, "perfil": perfil},
    )


# ---------------------------------------------------------------- código de validação
def test_empresa_nova_nao_tem_codigo(client):
    h = nova_empresa(client)
    e = client.get("/empresa", headers=h).json()
    assert e["codigo_validacao"] is None and e["codigo_ativo"] is False
    assert e["nome"] == "Empresa Alfa" and e["cnpj"] == "11222333000181"


def test_gestor_gera_codigo_com_formato_e_validade(client):
    h = nova_empresa(client)
    r = client.post("/empresa/codigo", headers=h).json()
    assert PADRAO_CODIGO.match(r["codigo_validacao"]) and r["codigo_ativo"] is True
    assert client.get("/empresa", headers=h).json()["codigo_validacao"] == r["codigo_validacao"]


def test_codigo_e_unico_por_empresa(client):
    c1 = gerar_codigo(client, nova_empresa(client))
    c2 = gerar_codigo(client, nova_empresa(client, "Empresa Beta", CNPJ_B, "gestor@beta.com.br"))
    assert c1 != c2


def test_regenerar_invalida_o_codigo_anterior(client):
    h = nova_empresa(client)
    antigo = gerar_codigo(client, h)
    novo = gerar_codigo(client, h)
    assert antigo != novo
    assert cadastrar(client, antigo).status_code == 422
    assert cadastrar(client, novo).status_code == 201


def test_revogar_codigo(client):
    h = nova_empresa(client)
    codigo = gerar_codigo(client, h)
    r = client.delete("/empresa/codigo", headers=h).json()
    assert r["codigo_validacao"] is None and r["codigo_ativo"] is False
    assert cadastrar(client, codigo).status_code == 422


def test_codigo_expira(client, db):
    h = nova_empresa(client)
    codigo = gerar_codigo(client, h)
    empresa = db.scalar(select(Empresa))
    empresa.codigo_expira_em = agora_utc() - timedelta(seconds=1)
    db.commit()
    assert client.get("/empresa", headers=h).json()["codigo_ativo"] is False
    r = cadastrar(client, codigo)
    assert r.status_code == 422 and r.json()["detail"]["codigo"] == "codigo_invalido"


def test_so_gestor_gerencia_o_codigo(client):
    h = nova_empresa(client)
    cod = gerar_codigo(client, h)
    r = cadastrar(client, cod, perfil="vendedor")
    h_vend = {"Authorization": f"Bearer {r.json()['access_token']}"}
    for metodo, url in (
        ("get", "/empresa"),
        ("post", "/empresa/codigo"),
        ("delete", "/empresa/codigo"),
        ("get", "/empresa/equipe"),
    ):
        assert getattr(client, metodo)(url, headers=h_vend).status_code == 403
        assert getattr(client, metodo)(url).status_code == 401


# ---------------------------------------------------------------- cadastro de funcionários
@pytest.mark.parametrize("perfil", ["comprador", "vendedor"])
def test_funcionario_se_cadastra_com_o_codigo_e_define_a_propria_senha(client, db, perfil):
    h = nova_empresa(client)
    r = cadastrar(client, gerar_codigo(client, h), perfil=perfil, senha="MinhaSenha9")
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["perfil"] == perfil and d["empresa"] == "Empresa Alfa"
    assert login(client, "func@alfa.com.br", "MinhaSenha9").status_code == 200  # senha escolhida por ele
    assert login(client, "func@alfa.com.br", SENHA).status_code == 401

    equipe = {u["email"]: u for u in client.get("/empresa/equipe", headers=h).json()}
    assert equipe["func@alfa.com.br"]["perfil"] == perfil
    assert equipe["func@alfa.com.br"]["ver_preco_custo"] is (perfil == "comprador")


def test_codigo_aceita_minusculas_sem_hifen_e_com_espacos(client):
    h = nova_empresa(client)
    codigo = gerar_codigo(client, h)
    assert cadastrar(client, codigo.lower().replace("-", " ")).status_code == 201
    assert cadastrar(client, "  " + codigo.replace("-", "").lower() + " ", email="b@alfa.com.br").status_code == 201


def test_codigo_pode_ser_reutilizado_enquanto_valido(client):
    h = nova_empresa(client)
    codigo = gerar_codigo(client, h)
    assert cadastrar(client, codigo, email="a@alfa.com.br").status_code == 201
    assert cadastrar(client, codigo, email="b@alfa.com.br").status_code == 201
    assert len(client.get("/empresa/equipe", headers=h).json()) == 3  # gestor + 2


def test_sem_codigo_ou_com_codigo_errado_nao_cadastra(client, db):
    h = nova_empresa(client)
    codigo = gerar_codigo(client, h)
    erradas = ["ZZZZ-ZZZZ-ZZZZ", codigo[:-1] + ("A" if codigo[-1] != "A" else "B"), "abcd"]
    mensagens = set()
    for c in erradas:
        r = cadastrar(client, c)
        assert r.status_code == 422 and r.json()["detail"]["codigo"] == "codigo_invalido"
        assert r.json()["detail"]["campo"] == "codigo"
        mensagens.add(r.json()["detail"]["mensagem"])
    assert len(mensagens) == 1  # mesma mensagem: não revela se o código "quase" existe
    assert login(client, "func@alfa.com.br").status_code == 401


def test_empresa_sem_codigo_ativo_nao_aceita_cadastro(client):
    nova_empresa(client)
    assert cadastrar(client, "ABCD-EFGH-JKLM").status_code == 422


def test_funcionario_nao_pode_ser_gestor(client):
    codigo = gerar_codigo(client, nova_empresa(client))
    r = cadastrar(client, codigo, perfil="gestor")
    assert r.status_code == 422 and "perfil" in r.json()["detail"]["campos"]


@pytest.mark.parametrize("senha", ["curta1A", "semmaiuscula1", "SEMMINUSCULA1", "SemNumeroAqui"])
def test_funcionario_com_senha_fraca_e_rejeitado(client, senha):
    codigo = gerar_codigo(client, nova_empresa(client))
    r = cadastrar(client, codigo, senha=senha)
    assert r.status_code == 422 and "senha" in r.json()["detail"]["campos"]


def test_email_ja_cadastrado_em_qualquer_empresa(client):
    h1 = nova_empresa(client)
    h2 = nova_empresa(client, "Empresa Beta", CNPJ_B, "gestor@beta.com.br")
    assert cadastrar(client, gerar_codigo(client, h1), email="x@t.com").status_code == 201
    r = cadastrar(client, gerar_codigo(client, h2), email="X@t.com")
    assert r.status_code == 409 and r.json()["detail"]["campo"] == "email"


def test_codigo_leva_o_funcionario_somente_para_a_empresa_dona_do_codigo(client):
    h1 = nova_empresa(client)
    h2 = nova_empresa(client, "Empresa Beta", CNPJ_B, "gestor@beta.com.br")
    r = cadastrar(client, gerar_codigo(client, h2), email="joao@t.com", perfil="vendedor")
    assert r.json()["empresa"] == "Empresa Beta"
    assert [u["email"] for u in client.get("/empresa/equipe", headers=h1).json()] == ["gestor@alfa.com.br"]
    assert "joao@t.com" in [u["email"] for u in client.get("/empresa/equipe", headers=h2).json()]


def test_login_inicial_do_funcionario_recem_cadastrado_funciona_pelo_token(client):
    codigo = gerar_codigo(client, nova_empresa(client))
    token = cadastrar(client, codigo, perfil="vendedor").json()["access_token"]
    assert client.get("/faltas/hoje", headers={"Authorization": f"Bearer {token}"}).status_code == 200
