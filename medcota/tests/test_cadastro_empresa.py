import pytest
from sqlalchemy import select

from app.enums import Perfil
from app.models import Auditoria, Empresa, Usuario
from tests.conftest import CNPJ_A, CNPJ_B, SENHA, criar_usuario, login

URL = "/cadastro/empresa"


def corpo(**extra):
    base = {
        "empresa_nome": "Distribuidora Alfa",
        "cnpj": "11.222.333/0001-81",
        "gestor_nome": "Carla Prado",
        "email": "carla@alfa.com.br",
        "senha": SENHA,
    }
    return {**base, **extra}


def test_cadastra_empresa_e_gestor_com_login_automatico(client, db):
    r = client.post(URL, json=corpo())
    assert r.status_code == 201, r.text
    dados = r.json()
    assert dados["perfil"] == "gestor" and dados["empresa"] == "Distribuidora Alfa"
    assert dados["access_token"]

    empresa = db.scalar(select(Empresa))
    assert empresa.cnpj == CNPJ_A  # guardado sem máscara
    assert empresa.codigo_validacao is None  # o gestor precisa GERAR o código
    gestor = db.scalar(select(Usuario))
    assert gestor.empresa_id == empresa.id and gestor.perfil == Perfil.gestor
    assert gestor.ver_preco_custo is True
    assert gestor.senha_hash != SENHA and gestor.senha_hash.startswith("$2")  # bcrypt
    assert db.scalar(select(Auditoria.acao)) == "cadastrou_empresa"

    # o token devolvido já funciona, e o login normal também
    h = {"Authorization": f"Bearer {dados['access_token']}"}
    assert client.get("/empresa", headers=h).status_code == 200
    assert login(client, "carla@alfa.com.br").status_code == 200


def test_email_e_normalizado_para_minusculas(client, db):
    client.post(URL, json=corpo(email="Carla@ALFA.com.br"))
    assert db.scalar(select(Usuario.email)) == "carla@alfa.com.br"
    assert login(client, "CARLA@alfa.com.br").status_code == 200


def test_aceita_cnpj_alfanumerico(client, db):
    r = client.post(URL, json=corpo(cnpj="12.ABC.345/01DE-35"))
    assert r.status_code == 201
    assert db.scalar(select(Empresa.cnpj)) == "12ABC34501DE35"


@pytest.mark.parametrize("cnpj", ["11.222.333/0001-80", "00000000000000", "123", ""])
def test_cnpj_invalido(client, cnpj):
    r = client.post(URL, json=corpo(cnpj=cnpj))
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "validacao"
    assert "cnpj" in r.json()["detail"]["campos"]


@pytest.mark.parametrize(
    ("senha", "trecho"),
    [
        ("Ab1", "pelo menos 8 caracteres"),
        ("abcdefg1", "maiúscula"),
        ("ABCDEFG1", "minúscula"),
        ("Abcdefgh", "número"),
    ],
)
def test_senha_fraca_e_rejeitada_com_motivo(client, db, senha, trecho):
    r = client.post(URL, json=corpo(senha=senha))
    assert r.status_code == 422
    assert trecho in r.json()["detail"]["campos"]["senha"]
    assert "Value error" not in r.json()["detail"]["campos"]["senha"]
    assert db.scalar(select(Empresa)) is None  # nada foi criado


def test_senha_nao_e_alterada_por_strip(client):
    """Espaços na senha fazem parte dela: o login precisa funcionar exatamente com eles."""
    senha = " Senha-teste-123 "
    assert client.post(URL, json=corpo(senha=senha)).status_code == 201
    assert login(client, "carla@alfa.com.br", senha).status_code == 200
    assert login(client, "carla@alfa.com.br", senha.strip()).status_code == 401


def test_cnpj_duplicado(client, db):
    assert client.post(URL, json=corpo()).status_code == 201
    r = client.post(URL, json=corpo(email="outra@alfa.com.br", cnpj="11222333000181"))
    assert r.status_code == 409
    assert r.json()["detail"] == {
        "codigo": "cnpj_em_uso",
        "mensagem": "Já existe uma empresa cadastrada com este CNPJ.",
        "campo": "cnpj",
    }


def test_email_duplicado_mesmo_em_outra_empresa(client, db):
    assert client.post(URL, json=corpo()).status_code == 201
    r = client.post(URL, json=corpo(cnpj=CNPJ_B))
    assert r.status_code == 409 and r.json()["detail"]["campo"] == "email"
    assert len(db.scalars(select(Empresa)).all()) == 1  # a segunda empresa não ficou pela metade


def test_email_invalido_e_campos_obrigatorios(client):
    r = client.post(URL, json=corpo(email="isso-nao-e-email"))
    assert r.status_code == 422 and "email" in r.json()["detail"]["campos"]
    r = client.post(URL, json={})
    assert r.status_code == 422
    assert {"empresa_nome", "cnpj", "gestor_nome", "email", "senha"} <= set(r.json()["detail"]["campos"])


def test_nao_da_para_escolher_perfil_nem_empresa_no_cadastro(client, db):
    """Campos extras (perfil/empresa_id) são ignorados: o cadastro SEMPRE cria um gestor novo."""
    r = client.post(URL, json=corpo(perfil="comprador", empresa_id=999, ver_preco_custo=False))
    assert r.status_code == 201 and r.json()["perfil"] == "gestor"


def test_login_de_conta_existente_nao_e_afetado(client, db):
    criar_usuario(db, "velho@t.com", Perfil.comprador)
    assert login(client, "velho@t.com").json()["empresa"] == "Empresa A"
