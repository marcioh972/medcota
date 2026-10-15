from datetime import timedelta
from decimal import Decimal

from app.core.config import settings
from app.core.timeutils import agora_utc
from app.enums import Perfil
from app.models import Cotacao, Falta
from tests.conftest import auth, criar_usuario


def _preparar(client, produto, qtd=10):
    h_v = auth(client, "ana@t.com")
    client.post(
        "/faltas",
        headers=h_v,
        json={"produto_id": produto.id, "cliente": "Farmácia Central", "quantidade": qtd},
    )
    h_c = auth(client, "bruno@t.com")
    r = client.post("/cotacoes/gerar", headers=h_c)
    assert r.status_code == 201, r.text
    return h_c, {c["fornecedor"]: c for c in r.json()}


def _responder(client, token, preco, pagamento="a_vista", qtd=10, prazo=3):
    item_id = client.get(f"/c/{token}").json()["itens"][0]["item_id"]
    return client.post(
        f"/c/{token}/responder",
        json=[
            {
                "item_id": item_id,
                "preco": preco,
                "quantidade": qtd,
                "prazo_dias": prazo,
                "pagamento": pagamento,
            }
        ],
    )


def test_fluxo_completo(client, vendedor, comprador, produto, fornecedores, db):
    h_c, cot = _preparar(client, produto)
    assert set(cot) == {"Forn A", "Forn B"}
    assert len(cot["Forn A"]["token"]) >= 32  # token imprevisível

    assert _responder(client, cot["Forn A"]["token"], "10.00", "a_vista").status_code == 204
    assert _responder(client, cot["Forn B"]["token"], "9.50", "30d", prazo=5).status_code == 204

    comp = client.get("/comparativo", headers=h_c).json()
    assert len(comp) == 1 and comp[0]["demanda"] == 10
    vencedor = next(o for o in comp[0]["ofertas"] if o["vencedor"])
    assert vencedor["fornecedor"] == "Forn B"  # 138,58 < 140,00
    assert Decimal(vencedor["custo_final"]) == Decimal("138.58")

    r = client.post("/pedidos", headers=h_c)
    assert r.status_code == 201, r.text
    pedido = r.json()
    assert Decimal(pedido["total"]) == Decimal("138.58")
    assert pedido["status"] == "aprovado"
    assert pedido["itens"][0]["quantidade"] == 10  # quantidade = demanda, não a oferta

    falta = client.get("/faltas/hoje", headers=auth(client, "ana@t.com")).json()[0]
    assert falta["status"] == "comprado"
    assert falta["detalhe"].startswith(f"pedido #{pedido['id']}")

    # não compra duas vezes
    r = client.post("/pedidos", headers=h_c)
    assert r.status_code == 422 and r.json()["detail"]["codigo"] == "sem_itens"

    dash = client.get("/dashboard", headers=h_c).json()
    assert dash["pedidos"] == 1 and dash["taxa_atendimento"] == 100.0


def test_nao_gera_cotacoes_duas_vezes(client, vendedor, comprador, produto, fornecedores):
    h_c, _ = _preparar(client, produto)
    r = client.post("/cotacoes/gerar", headers=h_c)
    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "cotacoes_ja_geradas"


def test_get_publico_nao_altera_estado_e_post_abertura_conta(client, vendedor, comprador, produto, fornecedores):
    h_c, cot = _preparar(client, produto)
    token = cot["Forn A"]["token"]
    client.get(f"/c/{token}")
    client.get(f"/c/{token}")
    assert client.post(f"/c/{token}/abertura").status_code == 204
    lista = client.get("/cotacoes", headers=h_c).json()
    assert next(c for c in lista if c["token"] == token)["aberturas"] == 1


def test_link_invalido_e_expirado(client, vendedor, comprador, produto, fornecedores, db):
    h_c, cot = _preparar(client, produto)
    assert client.get("/c/token-que-nao-existe").status_code == 404
    token = cot["Forn A"]["token"]
    c = db.query(Cotacao).filter_by(token=token).one()
    c.expira_em = agora_utc() - timedelta(minutes=1)
    db.commit()
    r = client.get(f"/c/{token}")
    assert r.status_code == 410 and r.json()["detail"]["codigo"] == "link_expirado"

    # 2ª rodada reabre o link
    assert client.post(f"/cotacoes/{c.id}/segunda-rodada", headers=h_c).json()["rodada"] == 2
    assert client.get(f"/c/{token}").status_code == 200


def test_resposta_invalida(client, vendedor, comprador, produto, fornecedores):
    _, cot = _preparar(client, produto)
    token = cot["Forn A"]["token"]
    item_id = client.get(f"/c/{token}").json()["itens"][0]["item_id"]
    base = {"item_id": item_id, "preco": "10", "quantidade": 10, "prazo_dias": 3}
    assert client.post(f"/c/{token}/responder", json=[{**base, "pagamento": "fiado"}]).status_code == 422
    assert client.post(f"/c/{token}/responder", json=[{**base, "preco": "-1"}]).status_code == 422
    assert client.post(f"/c/{token}/responder", json=[{**base, "item_id": 99999}]).status_code == 422
    assert client.post(f"/c/{token}/responder", json=[]).status_code == 422


def test_oferta_com_quantidade_insuficiente_nao_vence(client, vendedor, comprador, produto, fornecedores):
    h_c, cot = _preparar(client, produto)
    _responder(client, cot["Forn A"]["token"], "10.00", qtd=10)
    _responder(client, cot["Forn B"]["token"], "1.00", qtd=5)  # baratíssima, mas só 5 un
    comp = client.get("/comparativo", headers=h_c).json()[0]
    assert next(o for o in comp["ofertas"] if o["vencedor"])["fornecedor"] == "Forn A"


def test_sem_oferta_valida_marca_falta(client, vendedor, comprador, produto, fornecedores):
    h_c, cot = _preparar(client, produto)
    _responder(client, cot["Forn A"]["token"], "10.00", qtd=3)
    r = client.post("/pedidos", headers=h_c)
    assert r.status_code == 422 and r.json()["detail"]["codigo"] == "sem_oferta_valida"
    assert client.get("/faltas/hoje", headers=auth(client, "ana@t.com")).json()[0]["status"] == "sem_oferta"


def test_alcada_aprovacao_gestor(client, db, vendedor, comprador, gestor, produto, fornecedores, monkeypatch):
    monkeypatch.setattr(settings, "alcada_aprovacao", Decimal("100"))
    h_c, cot = _preparar(client, produto)
    _responder(client, cot["Forn A"]["token"], "10.00")
    pedido = client.post("/pedidos", headers=h_c).json()
    assert pedido["status"] == "aguardando_aprovacao"

    h_g = auth(client, "carla@t.com")
    assert client.post(f"/pedidos/{pedido['id']}/aprovar?aprovado=true", headers=h_c).status_code == 403
    r = client.post(f"/pedidos/{pedido['id']}/aprovar?aprovado=true", headers=h_g)
    assert r.status_code == 200 and r.json()["status"] == "aprovado"
    r = client.post(f"/pedidos/{pedido['id']}/aprovar?aprovado=false", headers=h_g)
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "pedido_fora_de_alcada"


def test_reprovar_devolve_faltas(client, db, vendedor, comprador, gestor, produto, fornecedores, monkeypatch):
    monkeypatch.setattr(settings, "alcada_aprovacao", Decimal("100"))
    h_c, cot = _preparar(client, produto)
    _responder(client, cot["Forn A"]["token"], "10.00")
    pedido = client.post("/pedidos", headers=h_c).json()
    client.post(f"/pedidos/{pedido['id']}/aprovar?aprovado=false", headers=auth(client, "carla@t.com"))
    assert db.query(Falta).one().status.value == "sem_oferta"


def test_rn04_usuario_sem_permissao_nao_ve_precos(client, db, vendedor, comprador, produto, fornecedores):
    criar_usuario(db, "cego@t.com", Perfil.comprador, ver_preco_custo=False)
    h_c, cot = _preparar(client, produto)
    _responder(client, cot["Forn A"]["token"], "10.00")
    h_cego = auth(client, "cego@t.com")

    oferta = client.get("/comparativo", headers=h_cego).json()[0]["ofertas"][0]
    assert oferta["preco"] is None and oferta["custo_final"] is None
    assert oferta["vencedor"] is True  # a decisão continua visível
    assert client.get("/dashboard", headers=h_cego).json()["economia_gerada"] is None

    oferta = client.get("/comparativo", headers=h_c).json()[0]["ofertas"][0]
    assert oferta["preco"] is not None


def test_listagens_paginadas(client, vendedor, comprador, produto, fornecedores):
    h_c, _ = _preparar(client, produto)
    assert len(client.get("/cotacoes?limit=1", headers=h_c).json()) == 1
    assert client.get("/cotacoes?limit=0", headers=h_c).status_code == 422
    assert client.get("/pedidos", headers=h_c).json() == []
