"""Gerador de NF-e (layout 4.00) para os testes: por padrão a nota sai correta e coerente.

Cada parâmetro permite injetar um defeito específico (preço, frete, imposto, totais...).
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.services.fiscal.chave import digito_verificador

D = Decimal


def q2(v: Decimal) -> Decimal:
    return v.quantize(D("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class ItemXml:
    ean: str = "7896094916010"
    descricao: str = "Dipirona 500mg"
    ncm: str = "30049099"
    cfop: str = "5102"
    qtd: Decimal = D("10")
    preco: Decimal = D("10.00")
    desconto: Decimal = D("0")
    frete: Decimal = D("0")
    cst: str = "00"  # CST de ICMS ("102" => Simples/CSOSN)
    orig: str = "0"
    p_icms: Decimal | None = None  # None => usa o padrão da operação
    p_red_bc: Decimal = D("0")
    mva_st: bool = False  # com ST: base ST = base * 1.30 (só para gerar números coerentes)
    p_icms_st: Decimal = D("20")
    p_fcp: Decimal = D("0")
    pis_cst: str = "04"
    cofins_cst: str = "04"
    # sobreposições para injetar defeitos
    v_icms: Decimal | None = None
    v_icms_st: Decimal | None = None
    v_pis: Decimal | None = None
    v_prod: Decimal | None = None


@dataclass
class NfeXml:
    itens: list[ItemXml] = field(default_factory=lambda: [ItemXml()])
    emit_cnpj: str = "11222333000181"
    emit_nome: str = "Distribuidora Alfa Ltda"
    emit_uf: str = "AL"
    emit_cmun: str = "2704302"
    emit_xmun: str = "Maceió"
    dest_cnpj: str = "11444777000161"
    dest_uf: str = "AL"
    numero: int = 1234
    serie: int = 1
    dh_emi: str = "2026-10-05T10:00:00-03:00"
    tp_amb: str = "1"
    tp_nf: str = "1"
    fin_nfe: str = "1"
    crt: str = "3"
    mod_frete: str = "0"
    v_frete_total: Decimal | None = None  # None => soma dos itens
    v_outro: Decimal = D("0")
    protocolo: bool = True
    c_stat: str = "100"
    v_nf_override: Decimal | None = None
    v_icms_total_override: Decimal | None = None
    chave_override: str | None = None
    com_totais: bool = True
    dtd: bool = False

    def chave(self) -> str:
        if self.chave_override:
            return self.chave_override
        uf = {"AL": "27", "SP": "35", "PE": "26"}[self.emit_uf]
        aamm = self.dh_emi[2:4] + self.dh_emi[5:7]
        base = f"{uf}{aamm}{self.emit_cnpj}55{self.serie:03d}{self.numero:09d}1{12345678:08d}"
        return base + str(digito_verificador(base))


def _tag(nome: str, valor) -> str:
    return f"<{nome}>{valor}</{nome}>"


def _icms_xml(it: ItemXml, v_prod: Decimal, interna: bool, p_padrao: Decimal) -> tuple[str, dict]:
    t = {"vBC": D("0"), "vICMS": D("0"), "vBCST": D("0"), "vST": D("0"), "vFCP": D("0")}
    if it.cst == "102":  # Simples Nacional
        return f"<ICMSSN102><orig>{it.orig}</orig><CSOSN>102</CSOSN></ICMSSN102>", t
    base = q2((v_prod - it.desconto + it.frete) * (1 - it.p_red_bc / 100))
    p = it.p_icms if it.p_icms is not None else p_padrao
    v_icms = it.v_icms if it.v_icms is not None else q2(base * p / 100)
    if it.cst in {"00", "20"}:
        extra = _tag("pRedBC", it.p_red_bc) if it.cst == "20" else ""
        fcp = ""
        if it.p_fcp:
            v_fcp = q2(base * it.p_fcp / 100)
            fcp = _tag("vBCFCP", base) + _tag("pFCP", it.p_fcp) + _tag("vFCP", v_fcp)
            t["vFCP"] = v_fcp
        t.update(vBC=base, vICMS=v_icms)
        return (f"<ICMS{it.cst}><orig>{it.orig}</orig><CST>{it.cst}</CST><modBC>3</modBC>{extra}"
                f"{_tag('vBC', base)}{_tag('pICMS', p)}{_tag('vICMS', v_icms)}{fcp}</ICMS{it.cst}>"), t  # fmt: skip
    if it.cst == "10":
        base_st = q2(base * D("1.30"))
        v_st = it.v_icms_st if it.v_icms_st is not None else q2(base_st * it.p_icms_st / 100 - v_icms)
        t.update(vBC=base, vICMS=v_icms, vBCST=base_st, vST=v_st)
        return (f"<ICMS10><orig>{it.orig}</orig><CST>10</CST><modBC>3</modBC>{_tag('vBC', base)}{_tag('pICMS', p)}"
                f"{_tag('vICMS', v_icms)}<modBCST>4</modBCST>{_tag('pMVAST', '30.00')}{_tag('vBCST', base_st)}"
                f"{_tag('pICMSST', it.p_icms_st)}{_tag('vICMSST', v_st)}</ICMS10>"), t  # fmt: skip
    if it.cst == "60":
        return f"<ICMS60><orig>{it.orig}</orig><CST>60</CST></ICMS60>", t
    raise ValueError(f"CST {it.cst} não suportado pelo gerador")


def _pis_cofins(nome: str, cst: str, base: Decimal, v_forcado: Decimal | None) -> tuple[str, Decimal]:
    if cst in {"01", "02"}:
        aliq = D("1.65") if nome == "PIS" else D("7.60")
        v = v_forcado if v_forcado is not None else q2(base * aliq / 100)
        corpo = f"<CST>{cst}</CST>{_tag('vBC', base)}{_tag('p' + nome, aliq)}{_tag('v' + nome, v)}"
        return f"<{nome}><{nome}Aliq>{corpo}</{nome}Aliq></{nome}>", v
    return f"<{nome}><{nome}NT><CST>{cst}</CST></{nome}NT></{nome}>", D("0")


def montar(n: NfeXml) -> bytes:
    interna = n.emit_uf == n.dest_uf
    p_padrao = D("19") if interna else D("12")
    dets, tot = (
        [],
        dict.fromkeys(("vBC", "vICMS", "vBCST", "vST", "vFCP", "vPIS", "vCOFINS", "vProd", "vDesc", "vFrete"), D("0")),
    )
    for i, it in enumerate(n.itens, start=1):
        v_prod = it.v_prod if it.v_prod is not None else q2(it.qtd * it.preco)
        icms, t = _icms_xml(it, v_prod, interna, p_padrao)
        base_pc = q2(v_prod - it.desconto + it.frete)
        pis, v_pis = _pis_cofins("PIS", it.pis_cst, base_pc, it.v_pis)
        cof, v_cof = _pis_cofins("COFINS", it.cofins_cst, base_pc, None)
        opc = (_tag("vFrete", it.frete) if it.frete else "") + (_tag("vDesc", it.desconto) if it.desconto else "")
        dets.append(
            f'<det nItem="{i}"><prod><cProd>P{i}</cProd><cEAN>{it.ean}</cEAN><xProd>{it.descricao}</xProd>'
            f"<NCM>{it.ncm}</NCM><CFOP>{it.cfop}</CFOP><uCom>UN</uCom><qCom>{it.qtd}</qCom><vUnCom>{it.preco}</vUnCom>"
            f"<vProd>{v_prod}</vProd><cEANTrib>{it.ean}</cEANTrib><uTrib>UN</uTrib><qTrib>{it.qtd}</qTrib>"
            f"<vUnTrib>{it.preco}</vUnTrib>{opc}<indTot>1</indTot></prod>"
            f"<imposto><ICMS>{icms}</ICMS>{pis}{cof}</imposto></det>"
        )
        for k in ("vBC", "vICMS", "vBCST", "vST", "vFCP"):
            tot[k] += t[k]
        tot["vPIS"] += v_pis
        tot["vCOFINS"] += v_cof
        tot["vProd"] += v_prod
        tot["vDesc"] += it.desconto
        tot["vFrete"] += it.frete
    v_frete = n.v_frete_total if n.v_frete_total is not None else tot["vFrete"]
    v_nf = tot["vProd"] - tot["vDesc"] + tot["vST"] + v_frete + n.v_outro
    v_nf = n.v_nf_override if n.v_nf_override is not None else v_nf
    v_icms_t = n.v_icms_total_override if n.v_icms_total_override is not None else tot["vICMS"]
    total = (
        f"<total><ICMSTot>{_tag('vBC', tot['vBC'])}{_tag('vICMS', v_icms_t)}{_tag('vICMSDeson', '0.00')}"
        f"{_tag('vFCP', tot['vFCP'])}{_tag('vBCST', tot['vBCST'])}{_tag('vST', tot['vST'])}{_tag('vFCPST', '0.00')}"
        f"{_tag('vFCPSTRet', '0.00')}{_tag('vProd', tot['vProd'])}{_tag('vFrete', v_frete)}{_tag('vSeg', '0.00')}"
        f"{_tag('vDesc', tot['vDesc'])}{_tag('vII', '0.00')}{_tag('vIPI', '0.00')}{_tag('vIPIDevol', '0.00')}"
        f"{_tag('vPIS', tot['vPIS'])}{_tag('vCOFINS', tot['vCOFINS'])}{_tag('vOutro', n.v_outro)}{_tag('vNF', v_nf)}"
        f"</ICMSTot></total>"
        if n.com_totais
        else ""
    )
    chave = n.chave()
    prot = (
        f'<protNFe versao="4.00"><infProt><tpAmb>1</tpAmb><chNFe>{chave}</chNFe><cStat>{n.c_stat}</cStat>'
        f"<xMotivo>Autorizado o uso da NF-e</xMotivo></infProt></protNFe>"
        if n.protocolo
        else ""
    )
    doctype = '<!DOCTYPE x [<!ENTITY a "aaaa">]>' if n.dtd else ""
    xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>{doctype}<nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">'
        f'<NFe><infNFe Id="NFe{chave}" versao="4.00"><ide><cUF>{chave[:2]}</cUF><natOp>Venda</natOp><mod>55</mod>'
        f"<serie>{n.serie}</serie><nNF>{n.numero}</nNF><dhEmi>{n.dh_emi}</dhEmi><tpNF>{n.tp_nf}</tpNF>"
        f"<tpAmb>{n.tp_amb}</tpAmb><finNFe>{n.fin_nfe}</finNFe></ide>"
        f"<emit><CNPJ>{n.emit_cnpj}</CNPJ><xNome>{n.emit_nome}</xNome><enderEmit><cMun>{n.emit_cmun}</cMun>"
        f"<xMun>{n.emit_xmun}</xMun><UF>{n.emit_uf}</UF></enderEmit><CRT>{n.crt}</CRT></emit>"
        f"<dest><CNPJ>{n.dest_cnpj}</CNPJ><xNome>Empresa Teste</xNome><enderDest><UF>{n.dest_uf}</UF></enderDest></dest>"
        f"{''.join(dets)}{total}<transp><modFrete>{n.mod_frete}</modFrete></transp></infNFe></NFe>{prot}</nfeProc>"
    )
    return xml.encode("utf-8")
