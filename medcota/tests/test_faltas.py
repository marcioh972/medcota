from datetime import time

from app.core.config import settings
from tests.conftest import auth


def lancar(client, h, produto, qtd=10, cliente="Farmácia Central", **extra):
    return client.post(
        "/faltas", headers=h, json={"produto_id": produto.id, "cliente": cliente, "quantidade": qtd, **extra}
    )


def test_lancar_e_listar(client, vendedor, produto):
    h = auth(client, "ana@t.com")
    r = lancar(client, h, produto, 10, urgencia="alta")
    assert r.status_code == 201
    assert r.json()["status"] == "pendente"
    lista = client.get("/faltas/hoje", headers=h).json()
    assert [f["quantidade"] for f in lista] == [10]


def test_duplicata_pede_confirmacao_e_depois_soma(client, vendedor, produto):
    h = auth(client, "ana@t.com")
    lancar(client, h, produto, 10)
    r = lancar(client, h, produto, 5)
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "duplicata"
    assert r.json()["detail"]["somar_quantidade"] is True

    r = client.post(
        "/faltas?somar_duplicata=true",
        headers=h,
        json={"produto_id": produto.id, "cliente": "Farmácia Central", "quantidade": 5},
    )
    assert r.status_code == 201
    assert r.json()["quantidade"] == 15


def test_somar_com_outro_cliente_cria_linha_propria(client, vendedor, produto):
    h = auth(client, "ana@t.com")
    lancar(client, h, produto, 10, cliente="Cliente A")
    r = client.post(
        "/faltas?somar_duplicata=true",
        headers=h,
        json={"produto_id": produto.id, "cliente": "Cliente B", "quantidade": 3},
    )
    assert r.status_code == 201
    assert r.json()["quantidade"] == 3  # não mexe na linha do Cliente A
    assert len(client.get("/faltas/hoje", headers=h).json()) == 2


def test_lista_fechada_apos_horario_de_corte(client, vendedor, produto, monkeypatch):
    monkeypatch.setattr(settings, "horario_corte", time(0, 0))
    r = lancar(client, auth(client, "ana@t.com"), produto)
    assert r.status_code == 422
    assert r.json()["detail"]["codigo"] == "lista_fechada"


def test_validacoes(client, vendedor, produto):
    h = auth(client, "ana@t.com")
    assert lancar(client, h, produto, 0).status_code == 422
    assert lancar(client, h, produto, 5, urgencia="urgentissima").status_code == 422
    r = client.post("/faltas", headers=h, json={"produto_id": 9999, "cliente": "X Y", "quantidade": 1})
    assert r.status_code == 404


def test_consolidacao_soma_vendedores(client, db, vendedor, comprador, produto):
    from app.enums import Perfil
    from tests.conftest import criar_usuario

    criar_usuario(db, "joao@t.com", Perfil.vendedor, False)
    lancar(client, auth(client, "ana@t.com"), produto, 10, cliente="Cliente A", urgencia="baixa")
    client.post(
        "/faltas?somar_duplicata=true",
        headers=auth(client, "joao@t.com"),
        json={"produto_id": produto.id, "cliente": "Cliente B", "quantidade": 5, "urgencia": "alta"},
    )
    r = client.get("/consolidacao", headers=auth(client, "bruno@t.com")).json()
    assert r[0]["demanda"] == 15
    assert r[0]["clientes"] == 2
    assert r[0]["urgencia_maxima"] == "alta"
    assert r[0]["solicitantes"] == ["Ana", "Joao"]


def test_busca_de_produtos(client, vendedor, produto):
    h = auth(client, "ana@t.com")
    assert client.get("/produtos", headers=h).json()[0]["nome"] == "Dipirona 500mg"
    assert len(client.get("/produtos?q=dipir", headers=h).json()) == 1
    assert len(client.get("/produtos?q=7896094", headers=h).json()) == 1  # prefixo do EAN
    assert client.get("/produtos?q=zzz", headers=h).json() == []
    assert client.get("/produtos?q=%25", headers=h).json() == []  # '%' não vira curinga
    assert client.get("/produtos").status_code == 401
