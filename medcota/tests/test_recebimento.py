"""Módulo de recebimento e conferência de NF-e: permissões, fluxo, segurança do upload e isolamento."""

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.enums import Perfil
from app.models import Auditoria, Pedido, PedidoItem
from tests.conftest import CNPJ_A, CNPJ_B, auth, criar_empresa, criar_fornecedores, criar_produto, criar_usuario
from tests.nfe_xml import ItemXml, NfeXml, montar

FORNECEDOR_CNPJ = "12ABC34501DE35"  # CNPJ alfanumérico (formato vigente desde jul/2026)
EAN = "7896094916010"


def agora_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def nota(**kw) -> bytes:
    """Nota correta para o pedido padrão (10 un a R$ 10,00), emitida pelo fornecedor para a empresa A."""
    base = dict(emit_cnpj=FORNECEDOR_CNPJ, dest_cnpj=CNPJ_A, dh_emi=agora_iso())
    return montar(NfeXml(**{**base, **kw}))


def enviar(client, headers, pedido_id, conteudo, nome="nfe.xml"):
    return client.post(
        f"/recebimento/pedidos/{pedido_id}/nfe", headers=headers, files={"arquivo": (nome, conteudo, "text/xml")}
    )


@pytest.fixture
def forn(db, fornecedores):
    f = fornecedores[0]
    f.cnpj = FORNECEDOR_CNPJ
    db.commit()
    return f


@pytest.fixture
def h_comp(client, comprador):
    return auth(client, "bruno@t.com")


@pytest.fixture
def h_gest(client, gestor):
    return auth(client, "carla@t.com")


def registrar(client, headers, produto, fornecedor, qtd=10, preco="10.00", **extra):
    r = client.post(
        "/recebimento/pedidos",
        headers=headers,
        json={
            "fornecedor_id": fornecedor.id,
            "itens": [{"produto_id": produto.id, "quantidade": qtd, "preco": preco}],
            **extra,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def codigos(nfe_json, severidade=None):
    return {a["codigo"] for a in nfe_json["apontamentos"] if severidade is None or a["severidade"] == severidade}


# ================================================================== permissões
class TestPermissoes:
    ROTAS = [
        ("GET", "/recebimento/pedidos"),
        ("POST", "/recebimento/pedidos"),
        ("GET", "/recebimento/pedidos/1"),
        ("POST", "/recebimento/pedidos/1/nfe"),
        ("GET", "/recebimento/nfes"),
        ("GET", "/recebimento/nfes/1"),
        ("GET", "/recebimento/nfes/1/xml"),
        ("POST", "/recebimento/nfes/1/reanalisar"),
        ("POST", "/recebimento/nfes/1/decisao"),
        ("GET", "/fiscal/configuracao"),
        ("PUT", "/fiscal/configuracao"),
    ]

    @pytest.mark.parametrize(("metodo", "rota"), ROTAS)
    def test_vendedor_nao_acessa_nenhuma_rota_do_modulo(self, client, vendedor, metodo, rota):
        r = client.request(metodo, rota, headers=auth(client, "ana@t.com"), json={})
        assert r.status_code == 403
        assert r.json()["detail"]["codigo"] == "perfil_sem_permissao"

    @pytest.mark.parametrize(("metodo", "rota"), ROTAS)
    def test_exige_login(self, client, metodo, rota):
        assert client.request(metodo, rota, json={}).status_code == 401

    def test_comprador_sem_permissao_de_precos_e_barrado(self, client, db, empresa):
        criar_usuario(db, "cego@t.com", Perfil.comprador, ver_preco_custo=False, empresa=empresa)
        r = client.get("/recebimento/pedidos", headers=auth(client, "cego@t.com"))
        assert r.status_code == 403 and r.json()["detail"]["codigo"] == "sem_permissao_precos"

    def test_so_o_gestor_altera_os_parametros_fiscais(self, client, h_comp, h_gest):
        assert client.put("/fiscal/configuracao", headers=h_comp, json={}).status_code == 403
        assert client.put("/fiscal/configuracao", headers=h_gest, json={}).status_code == 200
        assert client.get("/fiscal/configuracao", headers=h_comp).status_code == 200


# ================================================================== pedido registrado na tela
class TestPedidoManual:
    def test_registra_pedido_e_calcula_total(self, client, h_comp, produto, forn):
        p = registrar(
            client, h_comp, produto, forn, qtd=10, preco="10.50", frete_previsto="20.00", numero_externo="PC-77"
        )
        assert D(p["total"]) == D("125.00")  # 10 × 10,50 + frete 20
        assert (p["origem"], p["status"], p["recebimento"]) == ("manual", "aprovado", "aguardando_nfe")
        assert p["itens"][0]["produto"] == "Dipirona 500mg" and p["fornecedores"][0]["cnpj"] == FORNECEDOR_CNPJ
        assert p["numero_externo"] == "PC-77"

    def test_acima_da_alcada_o_comprador_precisa_de_aprovacao_mas_o_gestor_nao(
        self, client, h_comp, h_gest, produto, forn, monkeypatch
    ):
        monkeypatch.setattr(settings, "alcada_aprovacao", D("50"))
        assert registrar(client, h_comp, produto, forn)["status"] == "aguardando_aprovacao"
        assert registrar(client, h_gest, produto, forn)["status"] == "aprovado"

    def test_nao_recebe_nota_de_pedido_aguardando_aprovacao(self, client, h_comp, produto, forn, monkeypatch):
        monkeypatch.setattr(settings, "alcada_aprovacao", D("50"))
        p = registrar(client, h_comp, produto, forn)
        r = enviar(client, h_comp, p["id"], nota())
        assert r.status_code == 409 and r.json()["detail"]["codigo"] == "pedido_nao_aprovado"

    def test_validacoes(self, client, db, h_comp, produto, forn):
        item = {"produto_id": produto.id, "quantidade": 1, "preco": "5.00"}
        corpo = {"fornecedor_id": forn.id, "itens": [item]}
        post = lambda c: client.post("/recebimento/pedidos", headers=h_comp, json=c)  # noqa: E731
        assert post({**corpo, "itens": []}).status_code == 422
        assert post({**corpo, "itens": [item, item]}).status_code == 422  # produto repetido
        assert post({**corpo, "itens": [{**item, "preco": "0"}]}).status_code == 422
        assert post({**corpo, "itens": [{**item, "quantidade": 0}]}).status_code == 422
        assert post({**corpo, "frete_previsto": "-1"}).status_code == 422
        assert post({**corpo, "fornecedor_id": 9999}).status_code == 404
        assert post({**corpo, "itens": [{**item, "produto_id": 9999}]}).status_code == 404

    def test_fornecedor_e_produto_de_outra_empresa_sao_recusados(self, client, db, h_comp, produto, forn):
        outra = criar_empresa(db, "Empresa B", CNPJ_B)
        (forn_b,) = criar_fornecedores(db, outra, nomes=("Forn de B",))
        prod_b = criar_produto(db, outra, nome="Produto de B", ean="7891234567895")
        item = {"produto_id": produto.id, "quantidade": 1, "preco": "5.00"}
        r = client.post("/recebimento/pedidos", headers=h_comp, json={"fornecedor_id": forn_b.id, "itens": [item]})
        assert r.status_code == 404 and r.json()["detail"]["codigo"] == "fornecedor_nao_encontrado"
        r = client.post(
            "/recebimento/pedidos",
            headers=h_comp,
            json={"fornecedor_id": forn.id, "itens": [{**item, "produto_id": prod_b.id}]},
        )
        assert r.status_code == 404 and r.json()["detail"]["codigo"] == "produto_nao_encontrado"

    def test_lista_e_filtra_por_situacao(self, client, h_comp, produto, forn):
        registrar(client, h_comp, produto, forn)
        assert len(client.get("/recebimento/pedidos", headers=h_comp).json()) == 1
        assert client.get("/recebimento/pedidos?situacao=recebido", headers=h_comp).json() == []
        assert client.get("/recebimento/pedidos?situacao=invalida", headers=h_comp).status_code == 422


# ================================================================== fornecedor: CNPJ e credenciamento
class TestFornecedorFiscal:
    def test_cadastra_com_cnpj_e_credenciado_e_nao_repete(self, client, h_comp):
        corpo = {"nome": "Alfa Atacado", "escopo": "Local", "cnpj": "12.ABC.345/01DE-35", "credenciado_72101": True}
        r = client.post("/fornecedores", headers=h_comp, json=corpo)
        assert r.status_code == 201
        assert (r.json()["cnpj"], r.json()["credenciado_72101"]) == (FORNECEDOR_CNPJ, True)
        r = client.post("/fornecedores", headers=h_comp, json={**corpo, "nome": "Outro"})
        assert r.status_code == 409 and r.json()["detail"]["campo"] == "cnpj"
        r = client.post("/fornecedores", headers=h_comp, json={"nome": "Inválido", "cnpj": "11222333000180"})
        assert r.status_code == 422

    def test_patch_ajusta_cnpj_e_credenciamento(self, client, h_comp, fornecedores):
        f = fornecedores[1]
        r = client.patch(
            f"/fornecedores/{f.id}", headers=h_comp, json={"cnpj": "11444777000161", "credenciado_72101": True}
        )
        assert r.status_code == 200 and r.json()["cnpj"] == "11444777000161" and r.json()["credenciado_72101"]
        r = client.patch(f"/fornecedores/{fornecedores[0].id}", headers=h_comp, json={"cnpj": "11444777000161"})
        assert r.status_code == 409
        assert client.patch("/fornecedores/9999", headers=h_comp, json={}).status_code == 404


# ================================================================== fluxo da nota
class TestFluxoNota:
    def test_nota_correta_e_aceita_e_o_pedido_vira_recebido(self, client, db, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        r = enviar(client, h_comp, p["id"], nota())
        assert r.status_code == 201, r.text
        n = r.json()
        assert (n["resultado"], n["decisao"], n["erros"], n["alertas"]) == ("aprovada", "pendente", 0, 0)
        assert n["emitente_cnpj"] == FORNECEDOR_CNPJ and D(n["valor_total"]) == D("100.00")
        assert n["fornecedor_id"] == forn.id and n["versao_regras"]
        assert client.get(f"/recebimento/pedidos/{p['id']}", headers=h_comp).json()["recebimento"] == "em_conferencia"

        r = client.post(f"/recebimento/nfes/{n['id']}/decisao", headers=h_comp, json={"decisao": "aceita"})
        assert r.status_code == 200 and r.json()["decisao"] == "aceita"
        ped = client.get(f"/recebimento/pedidos/{p['id']}", headers=h_comp).json()
        assert ped["recebimento"] == "recebido" and ped["nfes"][0]["decisao"] == "aceita"
        acoes = {a.acao for a in db.scalars(select(Auditoria))}
        assert {"registrou_pedido_manual", "importou_nfe", "aceitou_nfe"} <= acoes

    def test_frete_em_fornecedor_de_maceio_reprova_a_nota(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota(itens=[ItemXml(frete=D("50.00"))])).json()
        assert n["resultado"] == "reprovada" and "FRETE_INDEVIDO" in codigos(n, "erro")
        frete = next(a for a in n["apontamentos"] if a["codigo"] == "FRETE_INDEVIDO")
        assert "Maceió" in frete["mensagem"] and frete["esperado"] == "0,00"

    def test_nota_com_erro_so_o_gestor_aceita_e_com_justificativa(self, client, h_comp, h_gest, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota(itens=[ItemXml(preco=D("12.00"))])).json()
        assert n["resultado"] == "reprovada"
        url = f"/recebimento/nfes/{n['id']}/decisao"
        r = client.post(
            url, headers=h_comp, json={"decisao": "aceita", "justificativa": "Fornecedor reajustou o preço"}
        )
        assert r.status_code == 403 and r.json()["detail"]["codigo"] == "aceite_exige_gestor"
        r = client.post(url, headers=h_gest, json={"decisao": "aceita"})
        assert r.status_code == 422 and r.json()["detail"]["codigo"] == "justificativa_obrigatoria"
        r = client.post(
            url, headers=h_gest, json={"decisao": "aceita", "justificativa": "Reajuste autorizado pela diretoria"}
        )
        assert r.status_code == 200 and r.json()["justificativa"].startswith("Reajuste")

    def test_recusa_exige_motivo_e_libera_nova_nota(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota(itens=[ItemXml(qtd=D("12"))])).json()
        url = f"/recebimento/nfes/{n['id']}/decisao"
        assert client.post(url, headers=h_comp, json={"decisao": "recusada"}).status_code == 422
        r = client.post(
            url, headers=h_comp, json={"decisao": "recusada", "justificativa": "Quantidade acima do pedido"}
        )
        assert r.status_code == 200 and r.json()["decisao"] == "recusada"
        assert client.get(f"/recebimento/pedidos/{p['id']}", headers=h_comp).json()["recebimento"] == "aguardando_nfe"
        # nova nota corrigida (outro número => outra chave)
        n2 = enviar(client, h_comp, p["id"], nota(numero=1235)).json()
        assert n2["resultado"] == "aprovada"
        assert (
            client.post(f"/recebimento/nfes/{n['id']}/decisao", headers=h_comp, json={"decisao": "aceita"}).status_code
            == 409
        )

    def test_decisao_pendente_nao_e_aceita(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota()).json()
        r = client.post(f"/recebimento/nfes/{n['id']}/decisao", headers=h_comp, json={"decisao": "pendente"})
        assert r.status_code == 422

    def test_pedido_com_dois_fornecedores_so_fecha_com_as_duas_notas(
        self, client, db, empresa, h_comp, produto, forn, fornecedores
    ):
        b = fornecedores[1]
        b.cnpj = "11444777000161"
        prod2 = criar_produto(db, empresa, nome="Amoxicilina", ean="7891234567895")
        pedido = Pedido(empresa_id=empresa.id, total=D("160"), status="aprovado")
        pedido.itens = [
            PedidoItem(
                produto_id=produto.id, fornecedor_id=forn.id, quantidade=10, preco=D("10"), custo_final=D("100")
            ),
            PedidoItem(produto_id=prod2.id, fornecedor_id=b.id, quantidade=5, preco=D("12"), custo_final=D("60")),
        ]
        db.add(pedido)
        db.commit()
        a_ok = enviar(client, h_comp, pedido.id, nota()).json()
        assert a_ok["resultado"] == "aprovada"  # só confere os itens do emitente
        client.post(f"/recebimento/nfes/{a_ok['id']}/decisao", headers=h_comp, json={"decisao": "aceita"})
        ped = client.get(f"/recebimento/pedidos/{pedido.id}", headers=h_comp).json()
        assert ped["recebimento"] == "aguardando_nfe"  # falta a nota do fornecedor B

        nb = nota(
            emit_cnpj="11444777000161",
            numero=77,
            itens=[ItemXml(ean="7891234567895", descricao="Amoxicilina", qtd=D("5"), preco=D("12.00"))],
        )
        b_ok = enviar(client, h_comp, pedido.id, nb).json()
        assert b_ok["resultado"] == "aprovada", b_ok["apontamentos"]
        client.post(f"/recebimento/nfes/{b_ok['id']}/decisao", headers=h_comp, json={"decisao": "aceita"})
        assert client.get(f"/recebimento/pedidos/{pedido.id}", headers=h_comp).json()["recebimento"] == "recebido"


# ================================================================== segurança e robustez do upload
class TestUpload:
    def test_nota_duplicada_e_barrada(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        primeira = enviar(client, h_comp, p["id"], nota()).json()
        r = enviar(client, h_comp, p["id"], nota())
        assert r.status_code == 409 and r.json()["detail"]["codigo"] == "nfe_duplicada"
        assert r.json()["detail"]["nfe_id"] == primeira["id"]

    @pytest.mark.parametrize(
        ("conteudo", "codigo", "status"),
        [
            (b"", "arquivo_vazio", 422),
            (b"isto nao e xml", "xml_invalido", 422),
            (b"<html><body/></html>", "xml_invalido", 422),
        ],
    )
    def test_arquivos_invalidos_nao_viram_nota(self, client, h_comp, produto, forn, conteudo, codigo, status):
        p = registrar(client, h_comp, produto, forn)
        r = enviar(client, h_comp, p["id"], conteudo)
        assert (r.status_code, r.json()["detail"]["codigo"]) == (status, codigo)
        assert client.get("/recebimento/nfes", headers=h_comp).json() == []

    def test_xml_com_dtd_ou_entidade_externa_e_bloqueado(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        r = enviar(client, h_comp, p["id"], montar(NfeXml(dtd=True)))
        assert r.status_code == 422 and "não permitidas" in r.json()["detail"]["mensagem"]
        xxe = (
            b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><infNFe Id="NFe1">&e;</infNFe>'
        )
        r = enviar(client, h_comp, p["id"], xxe)
        assert r.status_code == 422 and "root:" not in r.text

    def test_arquivo_acima_do_limite(self, client, h_comp, produto, forn, monkeypatch):
        p = registrar(client, h_comp, produto, forn)
        monkeypatch.setattr(settings, "nfe_max_bytes", 500)
        r = enviar(client, h_comp, p["id"], nota())
        assert r.status_code == 413 and r.json()["detail"]["codigo"] == "arquivo_grande"

    def test_requisicao_sem_arquivo(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        assert client.post(f"/recebimento/pedidos/{p['id']}/nfe", headers=h_comp).status_code == 422

    def test_baixa_o_xml_original(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        conteudo = nota()
        n = enviar(client, h_comp, p["id"], conteudo).json()
        r = client.get(f"/recebimento/nfes/{n['id']}/xml", headers=h_comp)
        assert r.status_code == 200 and r.content == conteudo
        assert (
            r.headers["content-type"].startswith("application/xml") and "attachment" in r.headers["content-disposition"]
        )

    def test_nota_de_outra_empresa_vira_erro_de_destinatario(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota(dest_cnpj=CNPJ_B)).json()
        assert n["resultado"] == "reprovada" and "DESTINATARIO_DIVERGENTE" in codigos(n, "erro")


# ================================================================== reanálise e parâmetros
class TestReanaliseEConfig:
    def test_cadastrar_o_cnpj_do_fornecedor_e_reanalisar_resolve_o_alerta(
        self, client, db, h_comp, produto, fornecedores
    ):
        f = fornecedores[0]  # sem CNPJ
        p = registrar(client, h_comp, produto, f)
        n = enviar(client, h_comp, p["id"], nota()).json()
        assert "FORNECEDOR_SEM_CNPJ" in codigos(n, "alerta") and n["resultado"] == "com_alertas"
        client.patch(f"/fornecedores/{f.id}", headers=h_comp, json={"cnpj": FORNECEDOR_CNPJ})
        r = client.post(f"/recebimento/nfes/{n['id']}/reanalisar", headers=h_comp)
        assert r.status_code == 200 and r.json()["resultado"] == "aprovada"
        assert "FORNECEDOR_SEM_CNPJ" not in codigos(r.json())

    def test_nota_decidida_nao_e_reanalisada(self, client, h_comp, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota()).json()
        client.post(f"/recebimento/nfes/{n['id']}/decisao", headers=h_comp, json={"decisao": "aceita"})
        assert client.post(f"/recebimento/nfes/{n['id']}/reanalisar", headers=h_comp).status_code == 409

    def test_parametros_padrao_e_atualizacao(self, client, h_gest):
        padrao = client.get("/fiscal/configuracao", headers=h_gest).json()
        assert padrao["aliquota_interna_icms"] is None and padrao["frete_zero_municipios"] == ["2704302"]
        r = client.put(
            "/fiscal/configuracao",
            headers=h_gest,
            json={
                "aliquota_interna_icms": "19.00",
                "tolerancia_preco_pct": "2.5",
                "frete_zero_municipios": ["2704302"],
            },
        )
        assert r.status_code == 200 and r.json()["atualizada_em"]
        assert D(client.get("/fiscal/configuracao", headers=h_gest).json()["aliquota_interna_icms"]) == D("19.00")
        for invalido in (
            {"aliquota_interna_icms": "150"},
            {"frete_zero_municipios": ["123"]},
            {"tolerancia_preco_pct": "-1"},
        ):
            assert client.put("/fiscal/configuracao", headers=h_gest, json=invalido).status_code == 422

    def test_alíquota_interna_configurada_passa_a_ser_validada(self, client, h_comp, h_gest, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota(itens=[ItemXml(p_icms=D("17"))])).json()
        assert "ALIQUOTA_INTERNA_NAO_CONFIGURADA" in codigos(
            n, "info"
        ) and "ALIQUOTA_INTERNA_DIVERGENTE" not in codigos(n)
        client.put("/fiscal/configuracao", headers=h_gest, json={"aliquota_interna_icms": "19"})
        r = client.post(f"/recebimento/nfes/{n['id']}/reanalisar", headers=h_comp).json()
        assert "ALIQUOTA_INTERNA_DIVERGENTE" in codigos(r, "erro") and r["resultado"] == "reprovada"

    def test_desligar_a_regra_de_frete_zero_por_municipio(self, client, h_comp, h_gest, produto, forn):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota(itens=[ItemXml(frete=D("50.00"))])).json()
        assert "FRETE_INDEVIDO" in codigos(n, "erro")
        client.put("/fiscal/configuracao", headers=h_gest, json={"frete_zero_municipios": []})
        r = client.post(f"/recebimento/nfes/{n['id']}/reanalisar", headers=h_comp).json()
        assert "FRETE_INDEVIDO" not in codigos(r) and "FRETE_ACIMA_DO_PEDIDO" in codigos(r, "erro")


# ================================================================== isolamento entre empresas
class TestIsolamento:
    @pytest.fixture
    def b(self, db):
        emp = criar_empresa(db, "Empresa B", CNPJ_B)
        (forn_b,) = criar_fornecedores(db, emp, nomes=("Forn de B",))
        forn_b.cnpj = FORNECEDOR_CNPJ  # mesmo CNPJ de fornecedor em outra empresa: permitido
        criar_usuario(db, "comprador@b.com", Perfil.comprador, True, empresa=emp)
        criar_usuario(db, "gestor@b.com", Perfil.gestor, True, empresa=emp)
        return emp, forn_b, criar_produto(db, emp, nome="Dipirona 500mg", ean=EAN)

    def test_a_outra_empresa_nao_ve_nem_mexe(self, client, h_comp, produto, forn, b):
        p = registrar(client, h_comp, produto, forn)
        n = enviar(client, h_comp, p["id"], nota()).json()
        hb = auth(client, "comprador@b.com")
        hgb = auth(client, "gestor@b.com")

        assert client.get("/recebimento/pedidos", headers=hb).json() == []
        assert client.get("/recebimento/nfes", headers=hb).json() == []
        assert client.get(f"/recebimento/pedidos/{p['id']}", headers=hb).status_code == 404
        assert client.get(f"/recebimento/nfes/{n['id']}", headers=hb).status_code == 404
        assert client.get(f"/recebimento/nfes/{n['id']}/xml", headers=hb).status_code == 404
        assert client.post(f"/recebimento/nfes/{n['id']}/reanalisar", headers=hb).status_code == 404
        assert (
            client.post(f"/recebimento/nfes/{n['id']}/decisao", headers=hgb, json={"decisao": "aceita"}).status_code
            == 404
        )
        assert enviar(client, hb, p["id"], nota(numero=9)).status_code == 404
        # nada mudou para a empresa A
        assert client.get(f"/recebimento/nfes/{n['id']}", headers=h_comp).json()["decisao"] == "pendente"

    def test_mesma_nota_pode_existir_em_empresas_diferentes_e_a_config_e_separada(
        self, client, h_comp, h_gest, produto, forn, b
    ):
        emp_b, forn_b, prod_b = b
        hb, hgb = auth(client, "comprador@b.com"), auth(client, "gestor@b.com")
        client.put("/fiscal/configuracao", headers=h_gest, json={"aliquota_interna_icms": "19"})
        assert client.get("/fiscal/configuracao", headers=hgb).json()["aliquota_interna_icms"] is None

        pa = registrar(client, h_comp, produto, forn)
        pb = registrar(client, hb, prod_b, forn_b)
        xml = nota(dest_cnpj=CNPJ_A)
        assert enviar(client, h_comp, pa["id"], xml).status_code == 201
        rb = enviar(client, hb, pb["id"], xml)  # a mesma chave, na outra empresa
        assert rb.status_code == 201 and "DESTINATARIO_DIVERGENTE" in codigos(rb.json(), "erro")
