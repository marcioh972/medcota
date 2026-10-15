from app.core.security import criar_token
from app.enums import Perfil
from tests.conftest import SENHA, auth, criar_usuario, login


def test_login_ok(client, vendedor):
    r = login(client, "ana@t.com")
    assert r.status_code == 200
    assert r.json()["perfil"] == "vendedor"
    assert r.json()["access_token"]


def test_login_email_case_insensitive(client, vendedor):
    assert login(client, "  ANA@T.COM ").status_code == 200


def test_senha_errada_e_email_inexistente_dao_a_mesma_resposta(client, vendedor):
    a = login(client, "ana@t.com", "errada")
    b = login(client, "naoexiste@t.com", "errada")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_bloqueio_apos_5_falhas_mesmo_com_senha_correta(client, vendedor):
    for _ in range(5):
        assert login(client, "ana@t.com", "errada").status_code == 401
    r = login(client, "ana@t.com", SENHA)
    assert r.status_code == 423
    assert r.json()["detail"]["codigo"] == "conta_bloqueada"


def test_usuario_inativo_nao_loga(client, db):
    criar_usuario(db, "off@t.com", Perfil.vendedor, ativo=False)
    assert login(client, "off@t.com").status_code == 401


def test_endpoint_exige_token(client):
    assert client.get("/faltas/hoje").status_code == 401
    assert client.get("/faltas/hoje", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_token_valido_funciona_com_sub_string(client, vendedor):
    h = {"Authorization": f"Bearer {criar_token(vendedor.id)}"}
    assert client.get("/faltas/hoje", headers=h).status_code == 200


def test_perfil_errado_recebe_403(client, vendedor, comprador):
    assert client.post("/pedidos", headers=auth(client, "ana@t.com")).status_code == 403
    assert client.get("/faltas/hoje", headers=auth(client, "bruno@t.com")).status_code == 403


def test_saude(client):
    assert client.get("/saude").json() == {"status": "ok"}
