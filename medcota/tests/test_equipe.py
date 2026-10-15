from tests.conftest import SENHA, login
from tests.test_codigo_funcionarios import cadastrar, gerar_codigo, nova_empresa


def setup_equipe(client):
    h = nova_empresa(client)
    codigo = gerar_codigo(client, h)
    comprador = cadastrar(client, codigo, "comp@alfa.com.br", "comprador").json()
    equipe = {u["email"]: u for u in client.get("/empresa/equipe", headers=h).json()}
    return h, equipe, {"Authorization": f"Bearer {comprador['access_token']}"}


def test_gestor_desativa_e_reativa_funcionario(client):
    h, equipe, h_comp = setup_equipe(client)
    uid = equipe["comp@alfa.com.br"]["id"]
    assert client.get("/produtos", headers=h_comp).status_code == 200

    r = client.patch(f"/empresa/equipe/{uid}", json={"ativo": False}, headers=h)
    assert r.status_code == 200 and r.json()["ativo"] is False
    # efeito imediato: o token já emitido deixa de valer e o login é recusado
    assert client.get("/produtos", headers=h_comp).status_code == 401
    assert login(client, "comp@alfa.com.br").status_code == 401

    client.patch(f"/empresa/equipe/{uid}", json={"ativo": True}, headers=h)
    assert client.get("/produtos", headers=h_comp).status_code == 200
    assert login(client, "comp@alfa.com.br").status_code == 200


def test_gestor_altera_permissao_de_ver_precos(client):
    h, equipe, _ = setup_equipe(client)
    uid = equipe["comp@alfa.com.br"]["id"]
    assert equipe["comp@alfa.com.br"]["ver_preco_custo"] is True
    r = client.patch(f"/empresa/equipe/{uid}", json={"ver_preco_custo": False}, headers=h)
    assert r.json()["ver_preco_custo"] is False and r.json()["ativo"] is True


def test_gestor_nao_pode_se_desativar(client):
    h, equipe, _ = setup_equipe(client)
    r = client.patch(f"/empresa/equipe/{equipe['gestor@alfa.com.br']['id']}", json={"ativo": False}, headers=h)
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "nao_pode_desativar_a_si_mesmo"
    assert login(client, "gestor@alfa.com.br").status_code == 200


def test_patch_vazio_e_usuario_inexistente(client):
    h, equipe, _ = setup_equipe(client)
    uid = equipe["comp@alfa.com.br"]["id"]
    assert client.patch(f"/empresa/equipe/{uid}", json={}, headers=h).status_code == 422
    assert client.patch("/empresa/equipe/99999", json={"ativo": False}, headers=h).status_code == 404


def test_comprador_nao_acessa_a_equipe(client):
    h, equipe, h_comp = setup_equipe(client)
    uid = equipe["gestor@alfa.com.br"]["id"]
    assert client.get("/empresa/equipe", headers=h_comp).status_code == 403
    assert client.patch(f"/empresa/equipe/{uid}", json={"ativo": False}, headers=h_comp).status_code == 403


def test_senha_nunca_aparece_na_resposta(client):
    h, _, _ = setup_equipe(client)
    texto = client.get("/empresa/equipe", headers=h).text
    assert "senha" not in texto and SENHA not in texto and "$2" not in texto
