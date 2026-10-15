"""Motor de conferência fiscal: parte de uma nota correta e injeta um defeito por vez."""

from datetime import datetime
from decimal import Decimal as D

import pytest

from app.enums import Severidade
from app.services.fiscal import chave, regras
from app.services.fiscal.parser import XmlInvalido, ler_nfe
from app.services.fiscal.tipos import (
    ConfigCtx,
    EmpresaCtx,
    FornecedorCtx,
    ItemPedidoCtx,
    PedidoCtx,
)
from tests.nfe_xml import ItemXml, NfeXml, montar

CNPJ_FORN = "11222333000181"
CNPJ_EMPRESA = "11444777000161"
AGORA = datetime(2026, 10, 6, 12, 0)


def pedido(preco="10.00", qtd=10, frete="0", fornecedores=None, itens=None):
    forn = FornecedorCtx(id=1, nome="Alfa", cnpj=CNPJ_FORN, credenciado_72101=False)
    return PedidoCtx(
        id=1,
        criado_em=datetime(2026, 10, 1),
        frete_previsto=D(frete),
        fornecedores=fornecedores or [forn],
        itens=itens or [ItemPedidoCtx(1, "Dipirona 500mg", "7896094916010", "30049099", 1, qtd, D(preco))],
    )


def rodar(nf: NfeXml, ped=None, cfg=None, empresa_cnpj=CNPJ_EMPRESA):
    resultado = regras.analisar(
        ler_nfe(montar(nf)), ped or pedido(), EmpresaCtx(empresa_cnpj), cfg or ConfigCtx(), agora=AGORA
    )
    por_codigo: dict[str, list] = {}
    for a in resultado.apontamentos:
        por_codigo.setdefault(a.codigo, []).append(a)
    return resultado, por_codigo


def severidade(por_codigo, codigo):
    return por_codigo[codigo][0].severidade


def erros(por_codigo):
    return {c for c, v in por_codigo.items() if v[0].severidade == Severidade.erro}


def alertas(por_codigo):
    return {c for c, v in por_codigo.items() if v[0].severidade == Severidade.alerta}


# ---------------------------------------------------------------------------------- nota correta
def test_nota_correta_nao_tem_erro_nem_alerta():
    r, c = rodar(NfeXml())
    assert erros(c) == set() and alertas(c) == set()
    assert r.fornecedor_id == 1
    # limites declarados da conferência aparecem como informação
    assert {
        "SEFAZ_NAO_CONSULTADA",
        "ALIQUOTA_INTERNA_NAO_CONFIGURADA",
        "DEC72101_CREDENCIAMENTO_NAO_INFORMADO",
    } <= set(c)


# ---------------------------------------------------------------------------------- parser seguro
class TestParser:
    def test_le_dados_principais(self):
        n = ler_nfe(montar(NfeXml()))
        assert (n.emit_cnpj, n.emit_uf, n.emit_municipio, n.numero) == (CNPJ_FORN, "AL", "2704302", "1234")
        assert n.itens[0].ean == "7896094916010" and n.itens[0].quantidade == D("10")
        assert n.totais["vNF"] == D("100.00") and n.protocolo_status == "100"

    @pytest.mark.parametrize("conteudo", [b"isto nao e xml", b"<a><b></a>", b"<NFe><x/></NFe>", b""])
    def test_rejeita_o_que_nao_e_nfe(self, conteudo):
        with pytest.raises(XmlInvalido):
            ler_nfe(conteudo)

    def test_bloqueia_dtd_e_entidades(self):
        with pytest.raises(XmlInvalido, match="não permitidas"):
            ler_nfe(montar(NfeXml(dtd=True)))

    def test_bloqueia_entidade_externa_xxe(self):
        xxe = (
            b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><infNFe Id="NFe1">&e;</infNFe>'
        )
        with pytest.raises(XmlInvalido):
            ler_nfe(xxe)

    def test_valor_numerico_invalido(self):
        xml = montar(NfeXml()).replace(b"<qCom>10</qCom>", b"<qCom>dez</qCom>")
        with pytest.raises(XmlInvalido, match="numérico"):
            ler_nfe(xml)

    def test_chave_com_tamanho_errado(self):
        xml = montar(NfeXml()).replace(NfeXml().chave().encode(), b"123", 1)
        with pytest.raises(XmlInvalido, match="44"):
            ler_nfe(xml)


# ---------------------------------------------------------------------------------- identificação
class TestIdentificacao:
    def test_digito_verificador_incorreto(self):
        boa = NfeXml().chave()
        ruim = boa[:43] + str((int(boa[43]) + 1) % 10)
        _, c = rodar(NfeXml(chave_override=ruim))
        assert "CHAVE_DV" in erros(c)

    def test_chave_nao_bate_com_os_dados_da_nota(self):
        outra = NfeXml(numero=9999).chave()  # DV válido, mas de outro número
        assert chave.dv_valido(outra)
        _, c = rodar(NfeXml(numero=1234, chave_override=outra))
        assert "CHAVE_INCONSISTENTE" in erros(c) and "número" in c["CHAVE_INCONSISTENTE"][0].mensagem

    def test_dv_modulo_11_vetor_conhecido(self):
        # chave de exemplo do manual: DV calculado sobre as 43 primeiras posições
        assert chave.digito_verificador("3519091122233300018155001000000012100000012") == 7

    def test_sem_protocolo_e_nao_autorizada(self):
        _, c = rodar(NfeXml(protocolo=False))
        assert "PROTOCOLO_AUSENTE" in erros(c)
        _, c = rodar(NfeXml(protocolo=False), cfg=ConfigCtx(exigir_protocolo=False))
        assert "PROTOCOLO_AUSENTE" in alertas(c)
        _, c = rodar(NfeXml(c_stat="110"))
        assert "NFE_NAO_AUTORIZADA" in erros(c)

    def test_homologacao_e_nota_de_entrada(self):
        _, c = rodar(NfeXml(tp_amb="2"))
        assert "AMBIENTE_HOMOLOGACAO" in erros(c)
        _, c = rodar(NfeXml(tp_nf="0"))
        assert "NFE_DE_ENTRADA" in erros(c)
        _, c = rodar(NfeXml(fin_nfe="4"))
        assert "FINALIDADE_NAO_NORMAL" in alertas(c)

    def test_destinatario(self):
        _, c = rodar(NfeXml(dest_cnpj="11222333000181"))
        assert "DESTINATARIO_DIVERGENTE" in erros(c)
        _, c = rodar(NfeXml(), empresa_cnpj=None)
        assert "DESTINATARIO_NAO_VALIDADO" in c and "DESTINATARIO_DIVERGENTE" not in c

    def test_emissao_anterior_ao_pedido(self):
        _, c = rodar(NfeXml(dh_emi="2026-09-20T10:00:00-03:00"))
        assert "EMISSAO_ANTERIOR_AO_PEDIDO" in alertas(c)


# ---------------------------------------------------------------------------------- fornecedor
class TestFornecedor:
    def test_emitente_diferente_do_fornecedor_do_pedido(self):
        f = FornecedorCtx(1, "Beta", "11444777000161", False)
        _, c = rodar(NfeXml(), pedido(fornecedores=[f]))
        assert "EMITENTE_DIVERGENTE" in erros(c)

    def test_fornecedor_sem_cnpj_vira_alerta(self):
        f = FornecedorCtx(1, "Alfa", None, False)
        r, c = rodar(NfeXml(), pedido(fornecedores=[f]))
        assert "FORNECEDOR_SEM_CNPJ" in alertas(c) and r.fornecedor_id == 1

    def test_varios_fornecedores_sem_correspondencia(self):
        fs = [FornecedorCtx(1, "X", "11444777000161", False), FornecedorCtx(2, "Y", None, False)]
        r, c = rodar(NfeXml(), pedido(fornecedores=fs))
        assert "EMITENTE_NAO_ENCONTRADO" in erros(c) and r.fornecedor_id is None

    def test_pedido_com_varios_fornecedores_compara_so_os_itens_do_emitente(self):
        fs = [FornecedorCtx(1, "Alfa", CNPJ_FORN, False), FornecedorCtx(2, "Beta", "11444777000161", False)]
        itens = [
            ItemPedidoCtx(1, "Dipirona 500mg", "7896094916010", "30049099", 1, 10, D("10.00")),
            ItemPedidoCtx(2, "Outro produto", "7891234567895", "30049099", 2, 5, D("3.00")),
        ]
        r, c = rodar(NfeXml(), pedido(fornecedores=fs, itens=itens))
        assert r.fornecedor_id == 1 and "ITEM_NAO_FATURADO" not in c  # o item do fornecedor 2 não conta


# ---------------------------------------------------------------------------------- pedido x nota
class TestPedidoXNota:
    def test_item_fora_do_pedido(self):
        _, c = rodar(NfeXml(itens=[ItemXml(ean="7890000000001", descricao="Produto desconhecido")]))
        assert "ITEM_FORA_DO_PEDIDO" in erros(c) and "ITEM_NAO_FATURADO" in alertas(c)

    def test_casa_pela_descricao_quando_nao_ha_ean(self):
        _, c = rodar(NfeXml(itens=[ItemXml(ean="SEM GTIN")]))
        assert "ITEM_FORA_DO_PEDIDO" not in c

    def test_preco_acima_e_abaixo(self):
        _, c = rodar(NfeXml(itens=[ItemXml(preco=D("10.50"))]))
        assert "PRECO_ACIMA_DO_PEDIDO" in erros(c)
        _, c = rodar(NfeXml(itens=[ItemXml(preco=D("9.50"))]))
        assert "PRECO_ABAIXO_DO_PEDIDO" in alertas(c)

    def test_tolerancia_percentual_do_preco(self):
        nf = NfeXml(itens=[ItemXml(preco=D("10.30"))])  # +3%
        _, c = rodar(nf)
        assert "PRECO_ACIMA_DO_PEDIDO" in erros(c)
        _, c = rodar(nf, cfg=ConfigCtx(tolerancia_preco_pct=D("5")))
        assert "PRECO_ACIMA_DO_PEDIDO" not in c

    def test_desconto_do_item_conta_no_preco_efetivo(self):
        # preço de tabela 11,00 com desconto de 10,00 no item => 10,00/un efetivo
        _, c = rodar(NfeXml(itens=[ItemXml(preco=D("11.00"), desconto=D("10.00"))]))
        assert "PRECO_ACIMA_DO_PEDIDO" not in c

    def test_quantidade_acima_e_entrega_parcial(self):
        _, c = rodar(NfeXml(itens=[ItemXml(qtd=D("12"))]))
        assert "QUANTIDADE_ACIMA_DO_PEDIDO" in erros(c)
        _, c = rodar(NfeXml(itens=[ItemXml(qtd=D("6"))]))
        assert "ENTREGA_PARCIAL" in alertas(c)

    def test_varias_linhas_do_mesmo_produto_somam(self):
        _, c = rodar(NfeXml(itens=[ItemXml(qtd=D("6")), ItemXml(qtd=D("4"))]))
        assert not erros(c) and "ENTREGA_PARCIAL" not in c

    def test_ncm_diferente_do_cadastro(self):
        _, c = rodar(NfeXml(itens=[ItemXml(ncm="30049069")]))
        assert "NCM_DIVERGENTE_CADASTRO" in alertas(c)


# ---------------------------------------------------------------------------------- totais
class TestTotais:
    def test_quantidade_x_valor_unitario_nao_fecha(self):
        _, c = rodar(NfeXml(itens=[ItemXml(v_prod=D("101.00"))]))
        assert "ITEM_TOTAL_INCONSISTENTE" in erros(c)

    def test_valor_total_da_nota(self):
        _, c = rodar(NfeXml(v_nf_override=D("105.00")))
        assert "TOTAL_NF_DIVERGENTE" in erros(c)

    def test_total_de_imposto_difere_da_soma_dos_itens(self):
        _, c = rodar(NfeXml(v_icms_total_override=D("30.00")))
        assert "TOTAL_IMPOSTO_DIVERGENTE" in erros(c)

    def test_nota_sem_totais(self):
        _, c = rodar(NfeXml(com_totais=False))
        assert "TOTAIS_AUSENTES" in erros(c)

    def test_arredondamento_de_centavo_e_tolerado(self):
        # 3 x 3,3333 = 9,9999 -> vProd 10,00 (arredondado pela emissão)
        ped = pedido(preco="3.3333", qtd=3)
        _, c = rodar(NfeXml(itens=[ItemXml(qtd=D("3"), preco=D("3.3333"))]), ped)
        assert "ITEM_TOTAL_INCONSISTENTE" not in c and "PRECO_ACIMA_DO_PEDIDO" not in c


# ---------------------------------------------------------------------------------- frete
class TestFrete:
    def test_fornecedor_de_maceio_nao_cobra_frete(self):
        _, c = rodar(NfeXml(itens=[ItemXml(frete=D("50.00"))]))
        e = c["FRETE_INDEVIDO"][0]
        assert e.severidade == Severidade.erro and "Maceió" in e.mensagem
        assert (e.esperado, e.encontrado) == ("0,00", "50.00")
        assert "FRETE_ACIMA_DO_PEDIDO" not in c  # não duplica o apontamento

    def test_frete_informado_so_no_total_tambem_e_pego(self):
        _, c = rodar(NfeXml(v_frete_total=D("30.00")))
        assert "FRETE_INDEVIDO" in erros(c)

    def test_municipio_configuravel(self):
        nf = NfeXml(itens=[ItemXml(frete=D("50.00"))])
        _, c = rodar(nf, cfg=ConfigCtx(frete_zero_municipios=frozenset()))
        assert "FRETE_INDEVIDO" not in c and "FRETE_ACIMA_DO_PEDIDO" in erros(c)

    def test_fora_de_maceio_frete_so_ate_o_previsto(self):
        recife = dict(emit_uf="PE", emit_cmun="2611606", emit_xmun="Recife", dest_uf="AL")
        item = ItemXml(frete=D("50.00"), cfop="6102")
        _, c = rodar(NfeXml(itens=[item], **recife))
        assert "FRETE_ACIMA_DO_PEDIDO" in erros(c) and "FRETE_INDEVIDO" not in c
        _, c = rodar(NfeXml(itens=[item], **recife), pedido(frete="50"))
        assert "FRETE_ACIMA_DO_PEDIDO" not in c and "FRETE_INDEVIDO" not in c

    def test_despesa_acessoria_em_fornecedor_sem_frete(self):
        _, c = rodar(NfeXml(v_outro=D("12.00")))
        assert "DESPESA_ACESSORIA_EM_FORNECEDOR_SEM_FRETE" in alertas(c)

    def test_modalidade_fob_com_frete_cobrado(self):
        recife = dict(emit_uf="PE", emit_cmun="2611606", emit_xmun="Recife")
        _, c = rodar(
            NfeXml(itens=[ItemXml(frete=D("20.00"), cfop="6102")], mod_frete="1", **recife),
            pedido(frete="20"),
        )
        assert "FRETE_MODALIDADE_INCOERENTE" in alertas(c)


# ---------------------------------------------------------------------------------- impostos
class TestImpostos:
    def test_icms_com_calculo_errado(self):
        _, c = rodar(NfeXml(itens=[ItemXml(v_icms=D("15.00"))]))
        assert "ICMS_CALCULO_INCORRETO" in erros(c)

    def test_icms_st_correto_e_incorreto(self):
        _, c = rodar(NfeXml(itens=[ItemXml(cst="10", cfop="5403")]))
        assert not erros(c)
        _, c = rodar(NfeXml(itens=[ItemXml(cst="10", cfop="5403", v_icms_st=D("3.00"))]))
        assert "ICMS_ST_CALCULO_INCORRETO" in erros(c)
        assert "142/2018" in c["ICMS_ST_CALCULO_INCORRETO"][0].base_legal

    def test_cst_20_base_reduzida(self):
        _, c = rodar(NfeXml(itens=[ItemXml(cst="20", p_red_bc=D("33.33"))]))
        assert not erros(c) and "ICMS_BASE_REDUZIDA_DIVERGENTE" not in c

    def test_aliquota_interestadual(self):
        pe = dict(emit_uf="PE", emit_cmun="2611606", emit_xmun="Recife", dest_uf="AL")
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="6102", p_icms=D("7"))], **pe), pedido(frete="0"))
        assert "ALIQUOTA_INTERESTADUAL_DIVERGENTE" in alertas(c)  # NE→NE é 12%
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="6102", p_icms=D("12"))], **pe))
        assert "ALIQUOTA_INTERESTADUAL_DIVERGENTE" not in c
        sp = dict(emit_uf="SP", emit_cmun="3550308", emit_xmun="São Paulo", dest_uf="AL")
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="6102", p_icms=D("7"))], **sp))  # S/SE → NE é 7%
        assert "ALIQUOTA_INTERESTADUAL_DIVERGENTE" not in c
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="6102", p_icms=D("12"))], **sp))
        assert "ALIQUOTA_INTERESTADUAL_DIVERGENTE" in alertas(c)
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="6102", p_icms=D("4"), orig="1")], **sp))  # importado: 4%
        assert "ALIQUOTA_INTERESTADUAL_DIVERGENTE" not in c

    def test_aliquota_interna_so_e_validada_se_configurada(self):
        nf = NfeXml(itens=[ItemXml(p_icms=D("17"))])
        _, c = rodar(nf)
        assert "ALIQUOTA_INTERNA_DIVERGENTE" not in c and "ALIQUOTA_INTERNA_NAO_CONFIGURADA" in c
        r, c = rodar(nf, cfg=ConfigCtx(aliquota_interna_icms=D("19")))
        assert "ALIQUOTA_INTERNA_DIVERGENTE" in erros(c) and "ALIQUOTA_INTERNA_NAO_CONFIGURADA" not in c
        _, c = rodar(NfeXml(), cfg=ConfigCtx(aliquota_interna_icms=D("19")))
        assert "ALIQUOTA_INTERNA_DIVERGENTE" not in c

    def test_cfop(self):
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="6102")]))
        assert "CFOP_UF_INCOERENTE" in erros(c)
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="1102")]))
        assert "CFOP_DE_ENTRADA" in erros(c)
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="5405")]))  # ST retida pede CST 60
        assert "CFOP_CST_INCOERENTE" in alertas(c)
        _, c = rodar(NfeXml(itens=[ItemXml(cfop="5405", cst="60")]))
        assert "CFOP_CST_INCOERENTE" not in c

    def test_ncm_invalido(self):
        _, c = rodar(NfeXml(itens=[ItemXml(ncm="123")]))
        assert "NCM_INVALIDO" in erros(c)

    def test_pis_calculo_e_monofasico(self):
        _, c = rodar(NfeXml(itens=[ItemXml(pis_cst="01", cofins_cst="01", v_pis=D("9.99"))]))
        assert "PIS_CALCULO_INCORRETO" in erros(c)
        assert "COFINS_CALCULO_INCORRETO" not in c
        # medicamento (NCM 3004) tributado em PIS/COFINS: revisar monofásico
        _, c = rodar(NfeXml(itens=[ItemXml(pis_cst="01", cofins_cst="01")]))
        assert (
            "PIS_COFINS_MONOFASICO_REVISAR" in alertas(c)
            and "Lei 10.147" in c["PIS_COFINS_MONOFASICO_REVISAR"][0].base_legal
        )
        _, c = rodar(
            NfeXml(itens=[ItemXml(pis_cst="01", cofins_cst="01", ncm="22021000")]),
            pedido(itens=[ItemPedidoCtx(1, "Dipirona 500mg", "7896094916010", "22021000", 1, 10, D("10.00"))]),
        )
        assert "PIS_COFINS_MONOFASICO_REVISAR" not in c

    def test_simples_nacional_nao_recalcula_icms(self):
        _, c = rodar(NfeXml(crt="1", itens=[ItemXml(cst="102")]))
        assert not erros(c) and "ICMS_SIMPLES_NACIONAL" in c


# ---------------------------------------------------------------------------------- decreto 72.101
class TestDecreto72101:
    def test_credenciado_explica_o_alcance(self):
        f = FornecedorCtx(1, "Alfa", CNPJ_FORN, True)
        _, c = rodar(NfeXml(), pedido(fornecedores=[f]))
        i = c["DEC72101_ESCOPO"][0]
        assert i.severidade == Severidade.info and "72.101/2020" in i.base_legal and "mensalmente" in i.mensagem
        assert "DEC72101_CREDENCIAMENTO_NAO_INFORMADO" not in c

    def test_credenciado_mas_emitente_fora_de_alagoas(self):
        f = FornecedorCtx(1, "Alfa", CNPJ_FORN, True)
        _, c = rodar(
            NfeXml(
                emit_uf="PE",
                emit_cmun="2611606",
                emit_xmun="Recife",
                itens=[ItemXml(cfop="6102", p_icms=D("12"))],
            ),
            pedido(fornecedores=[f]),
        )
        assert "DEC72101_EMITENTE_FORA_DE_AL" in alertas(c)

    def test_sem_medicamento_nao_comenta_o_decreto(self):
        _, c = rodar(NfeXml(itens=[ItemXml(ncm="22021000")]))
        assert "DEC72101_CREDENCIAMENTO_NAO_INFORMADO" not in c


def test_todo_apontamento_tem_mensagem_e_codigo():
    _, c = rodar(NfeXml(itens=[ItemXml(preco=D("11"), v_icms=D("1.00"), cfop="6102")], v_outro=D("3")))
    for lista in c.values():
        for a in lista:
            assert a.codigo and a.mensagem and isinstance(a.severidade, Severidade)
