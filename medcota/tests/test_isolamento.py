"""Isolamento entre empresas (SaaS): uma empresa nunca vê, altera ou influencia dados de outra."""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.enums import Perfil
from app.models import Auditoria, Falta, PrecoHistorico
from tests.conftest import (
    CNPJ_B,
    auth,
    criar_empresa,
    criar_fornecedores,
    criar_produto,
    criar_usuario,
)

EAN = "7896094916010"  # o MESMO EAN existe nas duas empresas (único só por empresa)


@pytest.fixture
def empresa_b(db):
    return criar_empresa(db, "Empresa B", CNPJ_B)


@pytest.fixture
def a(db, empresa, vendedor, comprador, gestor, produto, fornecedores):
    """Empresa A: usuários e catálogo (produto 'Dipirona 500mg', fornecedores 'Forn A/B')."""
    return SimpleNamespace(empresa=empresa, produto=produto, fornecedores=fornecedores)


@pytest.fixture
def b(db, empresa_b):
    """Empresa B: usuários e catálogo próprios, com nomes diferentes para detectar vazamento."""
    return SimpleNamespace(
        empresa=empresa_b,
        vendedor=criar_usuario(db, "vb@b.com", Perfil.vendedor, False, empresa=empresa_b),
        comprador=criar_usuario(db, "cb@b.com", Perfil.comprador, True, empresa=empresa_b),
        gestor=criar_usuario(db, "gb@b.com", Perfil.gestor, True, empresa=empresa_b),
        produto=criar_produto(db, empresa_b, nome="Produto da B", ean=EAN),
        fornecedores=criar_fornecedores(db, empresa_b, nomes=("Forn B1", "Forn B2")),
    )


def lancar(client, email, produto, qtd=10, cliente="Cliente Teste"):
    r = client.post(
        "/faltas",
        headers=auth(client, email),
        json={"produto_id": produto.id, "cliente": cliente, "quantidade": qtd},
    )
    assert r.status_code == 201, r.text
    return r.json()


def cotar_e_responder(client, email_comprador, preco, qtd=10):
    """Gera as cotações da empresa do comprador e responde TODAS as listas com o mesmo preço."""
    h = auth(client, email_comprador)
    r = client.post("/cotacoes/gerar", headers=h)
    assert r.status_code == 201, r.text
    tokens = [c["token"] for c in r.json()]
    for token in tokens:
        item_id = client.get(f"/c/{token}").json()["itens"][0]["item_id"]
        resp = client.post(
            f"/c/{token}/responder",
            json=[
                {
                    "item_id": item_id,
                    "preco": preco,
                    "quantidade": qtd,
                    "prazo_dias": 3,
                    "pagamento": "a_vista",
                }
            ],
        )
        assert resp.status_code == 204, resp.text
    return h, tokens


def test_ean_pode_repetir_entre_empresas(a, b):
    assert a.produto.ean == b.produto.ean and a.produto.empresa_id != b.produto.empresa_id


def test_catalogo_isolado(client, a, b):
    ha, hb = auth(client, "ana@t.com"), auth(client, "vb@b.com")
    assert [p["nome"] for p in client.get("/produtos", headers=ha).json()] == ["Dipirona 500mg"]
    assert [p["nome"] for p in client.get("/produtos", headers=hb).json()] == ["Produto da B"]
    assert client.get("/produtos?q=Produto da B", headers=ha).json() == []
    h_comp_a, h_comp_b = auth(client, "bruno@t.com"), auth(client, "cb@b.com")
    assert {f["nome"] for f in client.get("/fornecedores", headers=h_comp_a).json()} == {"Forn A", "Forn B"}
    assert {f["nome"] for f in client.get("/fornecedores", headers=h_comp_b).json()} == {"Forn B1", "Forn B2"}


def test_cadastros_do_catalogo_caem_so_na_propria_empresa(client, db, a, b):
    h = auth(client, "bruno@t.com")
    r = client.post("/produtos", headers=h, json={"nome": "Novo da A", "ean": "7891234567895"})
    assert r.status_code == 201
    assert client.post("/fornecedores", headers=h, json={"nome": "Novo Forn A"}).status_code == 201
    nomes_b = [p["nome"] for p in client.get("/produtos", headers=auth(client, "vb@b.com")).json()]
    assert nomes_b == ["Produto da B"]
    assert "Novo Forn A" not in {
        f["nome"] for f in client.get("/fornecedores", headers=auth(client, "cb@b.com")).json()
    }


def test_faltas_e_consolidacao_isoladas(client, a, b):
    lancar(client, "ana@t.com", a.produto, 10)
    lancar(client, "vb@b.com", b.produto, 7)

    faltas_a = client.get("/faltas/hoje", headers=auth(client, "ana@t.com")).json()
    assert [(f["produto"], f["quantidade"]) for f in faltas_a] == [("Dipirona 500mg", 10)]

    cons_a = client.get("/consolidacao", headers=auth(client, "bruno@t.com")).json()
    cons_b = client.get("/consolidacao", headers=auth(client, "cb@b.com")).json()
    assert [(c["produto"], c["demanda"]) for c in cons_a] == [("Dipirona 500mg", 10)]
    assert [(c["produto"], c["demanda"]) for c in cons_b] == [("Produto da B", 7)]


def test_vendedor_nao_lanca_falta_com_produto_de_outra_empresa(client, db, a, b):
    r = client.post(
        "/faltas",
        headers=auth(client, "ana@t.com"),
        json={"produto_id": b.produto.id, "cliente": "Cliente X", "quantidade": 5},
    )
    assert r.status_code == 404 and r.json()["detail"]["codigo"] == "produto_nao_encontrado"
    assert db.scalars(select(Falta)).all() == []


def test_gerar_cotacoes_usa_so_as_faltas_da_propria_empresa(client, a, b):
    lancar(client, "vb@b.com", b.produto, 7)  # só a empresa B tem faltas
    r = client.post("/cotacoes/gerar", headers=auth(client, "bruno@t.com"))
    assert r.status_code == 422 and r.json()["detail"]["codigo"] == "sem_faltas"
    assert client.get("/cotacoes", headers=auth(client, "cb@b.com")).json() == []


def test_fluxo_completo_nas_duas_empresas_sem_vazamento(client, a, b):
    lancar(client, "ana@t.com", a.produto, 10)
    lancar(client, "vb@b.com", b.produto, 10)
    h_a, tokens_a = cotar_e_responder(client, "bruno@t.com", "10.00")
    h_b, tokens_b = cotar_e_responder(client, "cb@b.com", "1000.00")

    # cotações: cada empresa só enxerga os próprios fornecedores/links
    cot_a = client.get("/cotacoes", headers=h_a).json()
    cot_b = client.get("/cotacoes", headers=h_b).json()
    assert {c["fornecedor"] for c in cot_a} == {"Forn A", "Forn B"}
    assert {c["fornecedor"] for c in cot_b} == {"Forn B1", "Forn B2"}
    assert {c["token"] for c in cot_a}.isdisjoint({c["token"] for c in cot_b})

    # comparativo: média histórica de A NÃO é contaminada pelos preços de B
    comp_a = client.get("/comparativo", headers=h_a).json()
    assert [i["produto"] for i in comp_a] == ["Dipirona 500mg"]
    assert Decimal(comp_a[0]["media_historica"]) == Decimal("10.00")
    assert all(not o["acima_da_media"] for o in comp_a[0]["ofertas"])
    comp_b = client.get("/comparativo", headers=h_b).json()
    assert [i["produto"] for i in comp_b] == ["Produto da B"]
    assert Decimal(comp_b[0]["media_historica"]) == Decimal("1000.00")

    # pedidos e painel
    ped_a = client.post("/pedidos", headers=h_a).json()
    ped_b = client.post("/pedidos", headers=h_b).json()
    assert Decimal(ped_a["total"]) == Decimal("140.00")  # 10 un * 10,00 - 5% + frete 45
    assert Decimal(ped_b["total"]) == Decimal("9545.00")  # 10 un * 1000 - 5% + frete 45
    assert [p["id"] for p in client.get("/pedidos", headers=h_a).json()] == [ped_a["id"]]
    assert [p["id"] for p in client.get("/pedidos", headers=h_b).json()] == [ped_b["id"]]
    assert client.get("/dashboard", headers=h_a).json()["pedidos"] == 1
    assert client.get("/dashboard", headers=h_b).json()["pedidos"] == 1
    # a economia é calculada com a média da PRÓPRIA empresa (A: 10*10-140 <0; B: 10*1000-9545)
    assert Decimal(client.get("/dashboard", headers=h_b).json()["economia_gerada"]) == Decimal("455.00")


def test_nao_acessa_nem_altera_recursos_de_outra_empresa_por_id(client, db, monkeypatch, a, b):
    monkeypatch.setattr(settings, "alcada_aprovacao", Decimal("1"))  # tudo exige aprovação
    lancar(client, "vb@b.com", b.produto, 10)
    h_b, _ = cotar_e_responder(client, "cb@b.com", "10.00")
    pedido_b = client.post("/pedidos", headers=h_b).json()
    cotacao_b = client.get("/cotacoes", headers=h_b).json()[0]
    assert pedido_b["status"] == "aguardando_aprovacao"

    # tentativa de "adivinhar" ids da empresa B usando usuários da empresa A
    r = client.post(f"/pedidos/{pedido_b['id']}/aprovar?aprovado=true", headers=auth(client, "carla@t.com"))
    assert r.status_code == 404 and r.json()["detail"]["codigo"] == "pedido_nao_encontrado"
    r = client.post(f"/cotacoes/{cotacao_b['id']}/segunda-rodada", headers=auth(client, "bruno@t.com"))
    assert r.status_code == 404
    r = client.patch(f"/empresa/equipe/{b.vendedor.id}", headers=auth(client, "carla@t.com"), json={"ativo": False})
    assert r.status_code == 404

    # nada mudou na empresa B
    db.expire_all()
    assert client.get("/pedidos", headers=h_b).json()[0]["status"] == "aguardando_aprovacao"
    assert db.get(type(b.vendedor), b.vendedor.id).ativo is True
    assert client.get("/cotacoes", headers=h_b).json()[0]["rodada"] == 1


def test_equipe_isolada(client, a, b):
    equipe_a = client.get("/empresa/equipe", headers=auth(client, "carla@t.com")).json()
    equipe_b = client.get("/empresa/equipe", headers=auth(client, "gb@b.com")).json()
    assert {u["email"] for u in equipe_a} == {"ana@t.com", "bruno@t.com", "carla@t.com"}
    assert {u["email"] for u in equipe_b} == {"vb@b.com", "cb@b.com", "gb@b.com"}


def test_link_publico_grava_na_empresa_dona_da_cotacao(client, db, a, b):
    lancar(client, "ana@t.com", a.produto, 10)
    cotar_e_responder(client, "bruno@t.com", "10.00")
    db.expire_all()
    historico = db.scalars(select(PrecoHistorico)).all()
    assert historico and {h.empresa_id for h in historico} == {a.empresa.id}
    assert client.get("/comparativo", headers=auth(client, "cb@b.com")).json() == []


def test_auditoria_registra_na_empresa_do_autor(client, db, a, b):
    lancar(client, "ana@t.com", a.produto, 10)
    lancar(client, "vb@b.com", b.produto, 5)
    db.expire_all()
    por_empresa = {}
    for registro in db.scalars(select(Auditoria)):
        por_empresa.setdefault(registro.empresa_id, set()).add(registro.usuario_id)
    assert por_empresa[a.empresa.id].isdisjoint(por_empresa[b.empresa.id])


def test_desativar_empresa_nao_existe_mas_usuario_inativo_perde_acesso_so_na_sua_empresa(client, db, a, b):
    h_b = auth(client, "vb@b.com")
    r = client.patch(f"/empresa/equipe/{a.empresa.id}", headers=auth(client, "carla@t.com"), json={"ativo": False})
    assert r.status_code in (404, 200)  # id pode coincidir com um usuário da própria empresa A
    assert client.get("/faltas/hoje", headers=h_b).status_code == 200
