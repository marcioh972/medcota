"""Leitura segura do XML da NF-e (layout 4.00, com ou sem o envelope `nfeProc`).

Segurança: usa `defusedxml` com DTD proibido, o que bloqueia XXE e "billion laughs".
O parser só extrai dados; quem julga é `regras.py`.
"""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from .tipos import (
    ZERO,
    ImpostoICMS,
    ImpostoIPI,
    ImpostoPisCofins,
    ItemNota,
    NotaFiscal,
)


class XmlInvalido(ValueError):
    """O arquivo não é uma NF-e legível. A mensagem é segura para mostrar ao usuário."""


def _sem_namespace(raiz: Element) -> None:
    for el in raiz.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def _txt(el: Element | None, caminho: str) -> str | None:
    if el is None:
        return None
    achado = el.find(caminho)
    if achado is None or achado.text is None:
        return None
    valor = achado.text.strip()
    return valor or None


def _dec(el: Element | None, caminho: str) -> Decimal | None:
    valor = _txt(el, caminho)
    if valor is None:
        return None
    try:
        d = Decimal(valor)
    except InvalidOperation:
        raise XmlInvalido(f"Valor numérico inválido em <{caminho}>: {valor!r}.") from None
    if not d.is_finite():
        raise XmlInvalido(f"Valor numérico inválido em <{caminho}>.")
    return d


def _dec0(el: Element | None, caminho: str) -> Decimal:
    return _dec(el, caminho) or ZERO


def _data(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor)
    except ValueError:
        return None
    # guardamos UTC ingênuo, como o resto do sistema
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


def _ean(valor: str | None) -> str | None:
    if not valor or not valor.isdigit():  # "SEM GTIN" etc.
        return None
    return valor


def _icms(imposto: Element | None) -> ImpostoICMS | None:
    grupo_pai = imposto.find("ICMS") if imposto is not None else None
    if grupo_pai is None or len(grupo_pai) == 0:
        return None
    g = grupo_pai[0]
    icms = ImpostoICMS(grupo=g.tag, cst=_txt(g, "CST"), csosn=_txt(g, "CSOSN"), orig=_txt(g, "orig"))
    for filho in g:
        if filho.tag in {"orig", "CST", "CSOSN", "motDesICMS"} or filho.text is None:
            continue
        try:
            icms.v[filho.tag] = Decimal(filho.text.strip())
        except InvalidOperation:
            continue
    return icms


def _pis_cofins(imposto: Element | None, nome: str, sufixo: str) -> ImpostoPisCofins | None:
    pai = imposto.find(nome) if imposto is not None else None
    if pai is None or len(pai) == 0:
        return None
    g = pai[0]
    return ImpostoPisCofins(
        cst=_txt(g, "CST"), base=_dec(g, "vBC"), aliquota=_dec(g, f"p{sufixo}"), valor=_dec(g, f"v{sufixo}")
    )


def _ipi(imposto: Element | None) -> ImpostoIPI | None:
    trib = imposto.find("IPI/IPITrib") if imposto is not None else None
    if trib is None:
        return None
    return ImpostoIPI(
        cst=_txt(trib, "CST"), base=_dec(trib, "vBC"), aliquota=_dec(trib, "pIPI"), valor=_dec(trib, "vIPI")
    )


def _item(det: Element) -> ItemNota:
    prod = det.find("prod")
    if prod is None:
        raise XmlInvalido("Item da nota sem o grupo <prod>.")
    try:
        numero = int(det.get("nItem", "0"))
    except ValueError:
        raise XmlInvalido("Atributo nItem inválido.") from None
    imposto = det.find("imposto")
    return ItemNota(
        numero=numero,
        codigo=_txt(prod, "cProd"),
        ean=_ean(_txt(prod, "cEAN")),
        ean_trib=_ean(_txt(prod, "cEANTrib")),
        descricao=_txt(prod, "xProd") or "",
        ncm=_txt(prod, "NCM"),
        cfop=_txt(prod, "CFOP"),
        unidade=_txt(prod, "uCom"),
        quantidade=_dec0(prod, "qCom"),
        valor_unitario=_dec0(prod, "vUnCom"),
        valor_produto=_dec0(prod, "vProd"),
        valor_frete=_dec0(prod, "vFrete"),
        valor_seguro=_dec0(prod, "vSeg"),
        valor_desconto=_dec0(prod, "vDesc"),
        valor_outros=_dec0(prod, "vOutro"),
        icms=_icms(imposto),
        pis=_pis_cofins(imposto, "PIS", "PIS"),
        cofins=_pis_cofins(imposto, "COFINS", "COFINS"),
        ipi=_ipi(imposto),
    )


def ler_nfe(conteudo: bytes) -> NotaFiscal:
    try:
        raiz = fromstring(conteudo, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except DefusedXmlException:
        raise XmlInvalido("O XML contém declarações (DTD/entidades) não permitidas.") from None
    except ParseError:
        raise XmlInvalido("O arquivo não é um XML válido.") from None
    _sem_namespace(raiz)

    inf = raiz if raiz.tag == "infNFe" else raiz.find(".//infNFe")
    if inf is None:
        raise XmlInvalido("O arquivo não é uma NF-e (elemento infNFe não encontrado).")

    identificador = inf.get("Id", "")
    chave = identificador[3:] if identificador.startswith("NFe") else identificador
    if len(chave) != 44:
        raise XmlInvalido("Chave de acesso ausente ou com tamanho inválido (esperado: 44 caracteres).")

    ide, emit, dest = inf.find("ide"), inf.find("emit"), inf.find("dest")
    dets = inf.findall("det")
    if ide is None or emit is None or not dets:
        raise XmlInvalido("NF-e incompleta: identificação, emitente ou itens ausentes.")

    totais: dict[str, Decimal] = {}
    icms_tot = inf.find("total/ICMSTot")
    if icms_tot is not None:
        for filho in icms_tot:
            if filho.text is not None:
                try:
                    totais[filho.tag] = Decimal(filho.text.strip())
                except InvalidOperation:
                    raise XmlInvalido(f"Valor numérico inválido em <{filho.tag}> do total.") from None

    prot = raiz.find(".//protNFe/infProt")
    ender_emit = emit.find("enderEmit")
    return NotaFiscal(
        chave=chave,
        versao=inf.get("versao"),
        modelo=_txt(ide, "mod"),
        serie=_txt(ide, "serie"),
        numero=_txt(ide, "nNF"),
        data_emissao=_data(_txt(ide, "dhEmi") or _txt(ide, "dEmi")),
        tipo_operacao=_txt(ide, "tpNF"),
        finalidade=_txt(ide, "finNFe"),
        ambiente=_txt(ide, "tpAmb"),
        uf_codigo=_txt(ide, "cUF"),
        emit_cnpj=_txt(emit, "CNPJ"),
        emit_nome=_txt(emit, "xNome"),
        emit_uf=_txt(ender_emit, "UF"),
        emit_municipio=_txt(ender_emit, "cMun"),
        emit_municipio_nome=_txt(ender_emit, "xMun"),
        emit_crt=_txt(emit, "CRT"),
        dest_cnpj=_txt(dest, "CNPJ"),
        dest_uf=_txt(dest, "enderDest/UF"),
        itens=[_item(d) for d in dets],
        totais=totais,
        modalidade_frete=_txt(inf, "transp/modFrete"),
        info_complementar=_txt(inf, "infAdic/infCpl") or "",
        protocolo_status=_txt(prot, "cStat"),
        protocolo_motivo=_txt(prot, "xMotivo"),
        protocolo_chave=_txt(prot, "chNFe"),
    )
