"""Regras de conferência de uma NF-e de entrada contra o pedido, a empresa e a configuração fiscal.

Cada regra devolve `Apontamento`s (erro, alerta ou info). O motor é puro: recebe dados, devolve
constatações. Convenções:

* **erro**   – inconsistência objetiva (conta que não fecha, nota de outra empresa, preço acima do
               pedido...). Uma nota com erro é "reprovada" e só o gestor pode aceitá-la, com justificativa.
* **alerta** – situação suspeita que exige olhar humano (suspeita de classificação fiscal, entrega parcial).
* **info**   – esclarecimento ou limite da conferência (o que o sistema NÃO conseguiu validar).

Este módulo NÃO substitui a análise do contador: não consulta a SEFAZ e não valida benefícios
fiscais do emitente. Parâmetros que mudam por decreto (alíquota interna) vêm da configuração.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ...enums import Severidade
from . import chave as chave_nfe
from . import tabelas
from .tipos import (
    ZERO,
    Apontamento,
    ConfigCtx,
    EmpresaCtx,
    FornecedorCtx,
    ItemNota,
    ItemPedidoCtx,
    NotaFiscal,
    PedidoCtx,
)

VERSAO_REGRAS = "2026.10.1"

CENTAVO = Decimal("0.01")
BASE_DECRETO = "Decreto AL nº 72.101/2020"
BASE_ST = "Convênio ICMS 142/2018 (cálculo da substituição tributária)"
BASE_INTERESTADUAL = "Resoluções do Senado 22/1989 e 13/2012 (alíquotas interestaduais de ICMS)"
BASE_MONOFASICO = "Lei 10.147/2000 (PIS/COFINS monofásico de medicamentos)"
BASE_LEIAUTE = "Manual de Orientação do Contribuinte da NF-e (leiaute 4.00)"
BASE_FRETE = "Regra da empresa: fornecedores de Maceió/AL não cobram frete na nota (Parâmetros fiscais)"


def brl(v: Decimal) -> str:
    texto = f"{v:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _s(v: Decimal, casas: int = 2) -> str:
    return f"{v:.{casas}f}"


class _Saida:
    def __init__(self) -> None:
        self.itens: list[Apontamento] = []

    def _add(self, sev: Severidade, codigo: str, mensagem: str, **kw) -> None:
        self.itens.append(Apontamento(sev, codigo, mensagem, **kw))

    def erro(self, codigo: str, mensagem: str, **kw) -> None:
        self._add(Severidade.erro, codigo, mensagem, **kw)

    def alerta(self, codigo: str, mensagem: str, **kw) -> None:
        self._add(Severidade.alerta, codigo, mensagem, **kw)

    def info(self, codigo: str, mensagem: str, **kw) -> None:
        self._add(Severidade.info, codigo, mensagem, **kw)


# ---------------------------------------------------------------------------------------------
# 1. Identificação e autenticidade
# ---------------------------------------------------------------------------------------------
def _identificacao(n: NotaFiscal, empresa: EmpresaCtx, cfg: ConfigCtx, pedido: PedidoCtx,
                   agora: datetime, o: _Saida) -> None:  # fmt: skip
    if n.modelo != "55":
        o.erro("MODELO_INVALIDO", f"Modelo de documento {n.modelo!r}; compras entre empresas usam a NF-e modelo 55.",
               campo="mod", esperado="55", encontrado=n.modelo, base_legal=BASE_LEIAUTE)  # fmt: skip
    if n.ambiente == "2":
        o.erro("AMBIENTE_HOMOLOGACAO", "NF-e emitida em ambiente de homologação: não tem valor fiscal.",
               campo="tpAmb", esperado="1 (produção)", encontrado="2 (homologação)")  # fmt: skip
    if n.tipo_operacao == "0":
        o.erro("NFE_DE_ENTRADA", "A nota está marcada como de entrada (tpNF=0); uma compra chega como nota de saída do fornecedor.",
               campo="tpNF", esperado="1 (saída)", encontrado="0 (entrada)")  # fmt: skip
    if n.finalidade and n.finalidade != "1":
        nomes = {"2": "complementar", "3": "de ajuste", "4": "de devolução"}
        o.alerta("FINALIDADE_NAO_NORMAL", f"A nota é {nomes.get(n.finalidade, 'com finalidade ' + n.finalidade)}, não uma nota normal de venda.",
                 campo="finNFe", esperado="1 (normal)", encontrado=n.finalidade)  # fmt: skip

    # chave de acesso
    if not chave_nfe.formato_valido(n.chave):
        o.erro(
            "CHAVE_FORMATO",
            "A chave de acesso não tem o formato esperado (44 posições).",
            campo="chNFe",
            encontrado=n.chave,
        )
    elif not chave_nfe.dv_valido(n.chave):
        o.erro("CHAVE_DV", "O dígito verificador da chave de acesso não confere: a chave pode ter sido adulterada ou digitada errada.",
               campo="chNFe", esperado=str(chave_nfe.digito_verificador(n.chave[:43])), encontrado=n.chave[43])  # fmt: skip
    else:
        p = chave_nfe.partes(n.chave)
        divergencias = []
        if n.uf_codigo and p.uf_codigo != n.uf_codigo:
            divergencias.append("UF")
        if n.emit_cnpj and p.cnpj != n.emit_cnpj:
            divergencias.append("CNPJ do emitente")
        if n.modelo and p.modelo != n.modelo:
            divergencias.append("modelo")
        if n.serie and p.serie.lstrip("0") != n.serie.lstrip("0"):
            divergencias.append("série")
        if n.numero and p.numero.lstrip("0") != n.numero.lstrip("0"):
            divergencias.append("número")
        if n.data_emissao and p.ano_mes != n.data_emissao.strftime("%y%m"):
            divergencias.append("mês/ano de emissão")
        if divergencias:
            o.erro("CHAVE_INCONSISTENTE", "A chave de acesso não bate com os dados da nota: " + ", ".join(divergencias) + ".",
                   campo="chNFe", base_legal=BASE_LEIAUTE)  # fmt: skip

    # protocolo de autorização
    if n.protocolo_status is None:
        msg = "O XML não traz o protocolo de autorização da SEFAZ. Use o XML autorizado (arquivo com <nfeProc>)."
        (o.erro if cfg.exigir_protocolo else o.alerta)("PROTOCOLO_AUSENTE", msg, campo="protNFe")
    elif n.protocolo_status not in {"100", "150"}:
        o.erro("NFE_NAO_AUTORIZADA", f"A nota não está autorizada para uso (cStat {n.protocolo_status}: {n.protocolo_motivo or 'sem motivo informado'}).",
               campo="cStat", esperado="100 (autorizada)", encontrado=n.protocolo_status)  # fmt: skip
    elif n.protocolo_chave and n.protocolo_chave != n.chave:
        o.erro(
            "PROTOCOLO_CHAVE_DIVERGENTE",
            "O protocolo de autorização pertence a outra chave de acesso.",
            campo="chNFe",
        )
    o.info("SEFAZ_NAO_CONSULTADA", "A situação atual da nota (cancelamento, denegação) não foi consultada na SEFAZ: confira no portal da NF-e se necessário.",
           campo="protNFe")  # fmt: skip

    # destinatário = a própria empresa
    if empresa.cnpj is None:
        o.info(
            "DESTINATARIO_NAO_VALIDADO",
            "A empresa não tem CNPJ cadastrado; o destinatário da nota não foi validado.",
            campo="dest/CNPJ",
        )
    elif n.dest_cnpj != empresa.cnpj:
        o.erro("DESTINATARIO_DIVERGENTE", "O destinatário da nota não é a sua empresa.",
               campo="dest/CNPJ", esperado=empresa.cnpj, encontrado=n.dest_cnpj or "(sem CNPJ)")  # fmt: skip

    # datas
    if n.data_emissao:
        if n.data_emissao > agora.replace(tzinfo=None) + timedelta(days=1):
            o.alerta(
                "EMISSAO_FUTURA",
                "A data de emissão está no futuro.",
                campo="dhEmi",
                encontrado=n.data_emissao.date().isoformat(),
            )
        if n.data_emissao.date() < pedido.criado_em.date():
            o.alerta("EMISSAO_ANTERIOR_AO_PEDIDO", "A nota foi emitida antes do registro do pedido: confirme se ela corresponde a este pedido.",
                     campo="dhEmi", esperado=f">= {pedido.criado_em.date().isoformat()}", encontrado=n.data_emissao.date().isoformat())  # fmt: skip


# ---------------------------------------------------------------------------------------------
# 2. Fornecedor (emitente) x pedido
# ---------------------------------------------------------------------------------------------
def _fornecedor(n: NotaFiscal, pedido: PedidoCtx, o: _Saida) -> FornecedorCtx | None:
    por_cnpj = [f for f in pedido.fornecedores if f.cnpj and f.cnpj == n.emit_cnpj]
    if por_cnpj:
        return por_cnpj[0]
    if len(pedido.fornecedores) == 1:
        f = pedido.fornecedores[0]
        if f.cnpj:
            o.erro("EMITENTE_DIVERGENTE", f"O emitente da nota não é o fornecedor do pedido ({f.nome}).",
                   campo="emit/CNPJ", esperado=f.cnpj, encontrado=n.emit_cnpj or "(sem CNPJ)")  # fmt: skip
        else:
            o.alerta("FORNECEDOR_SEM_CNPJ", f"O fornecedor {f.nome} não tem CNPJ cadastrado, então o emitente não pôde ser validado. "
                     f"Cadastre o CNPJ {n.emit_cnpj} para conferir as próximas notas.", campo="emit/CNPJ", encontrado=n.emit_cnpj)  # fmt: skip
        return f
    o.erro("EMITENTE_NAO_ENCONTRADO", "O emitente da nota não corresponde a nenhum fornecedor deste pedido; os itens não foram comparados.",
           campo="emit/CNPJ", encontrado=n.emit_cnpj or "(sem CNPJ)")  # fmt: skip
    return None


# ---------------------------------------------------------------------------------------------
# 3. Itens: pedido x nota (produto, quantidade, preço)
# ---------------------------------------------------------------------------------------------
def _casar_itens(n: NotaFiscal, esperados: list[ItemPedidoCtx]) -> list[tuple[ItemNota, ItemPedidoCtx | None]]:
    por_ean = {i.ean: i for i in esperados if i.ean}
    por_nome = {i.nome.casefold(): i for i in esperados}
    pares = []
    for item in n.itens:
        alvo = (
            por_ean.get(item.ean or "") or por_ean.get(item.ean_trib or "") or por_nome.get(item.descricao.casefold())
        )
        pares.append((item, alvo))
    return pares


def _pedido_x_nota(n: NotaFiscal, pedido: PedidoCtx, fornecedor: FornecedorCtx, cfg: ConfigCtx, o: _Saida) -> None:
    esperados = [i for i in pedido.itens if i.fornecedor_id == fornecedor.id]
    pares = _casar_itens(n, esperados)
    qtd_nota: dict[int, Decimal] = {}
    primeira_linha: dict[int, int] = {}
    tol = cfg.tolerancia_preco_pct / Decimal(100)

    for item, alvo in pares:
        if alvo is None:
            ref = f" (EAN {item.ean})" if item.ean else ""
            o.erro("ITEM_FORA_DO_PEDIDO", f"O item “{item.descricao}”{ref} não consta no pedido.",
                   item_numero=item.numero, campo="prod/xProd", encontrado=item.descricao)  # fmt: skip
            continue
        qtd_nota[alvo.produto_id] = qtd_nota.get(alvo.produto_id, ZERO) + item.quantidade
        primeira_linha.setdefault(alvo.produto_id, item.numero)

        liquido = item.valor_produto - item.valor_desconto
        previsto = alvo.preco * item.quantidade
        folga = previsto * tol + CENTAVO
        if liquido - previsto > folga:
            o.erro("PRECO_ACIMA_DO_PEDIDO", f"{alvo.nome}: preço da nota ({brl(item.preco_liquido_unitario)}/un) acima do pedido ({brl(alvo.preco)}/un).",
                   item_numero=item.numero, campo="prod/vUnCom", esperado=_s(alvo.preco, 4), encontrado=_s(item.preco_liquido_unitario, 4))  # fmt: skip
        elif previsto - liquido > folga:
            o.alerta("PRECO_ABAIXO_DO_PEDIDO", f"{alvo.nome}: preço da nota ({brl(item.preco_liquido_unitario)}/un) abaixo do pedido ({brl(alvo.preco)}/un). Confirme se houve desconto combinado.",
                     item_numero=item.numero, campo="prod/vUnCom", esperado=_s(alvo.preco, 4), encontrado=_s(item.preco_liquido_unitario, 4))  # fmt: skip

        if alvo.ncm and item.ncm and alvo.ncm != item.ncm:
            o.alerta("NCM_DIVERGENTE_CADASTRO", f"{alvo.nome}: o NCM da nota ({item.ncm}) difere do cadastrado no produto ({alvo.ncm}).",
                     item_numero=item.numero, campo="prod/NCM", esperado=alvo.ncm, encontrado=item.ncm)  # fmt: skip

    for ped in esperados:
        recebido = qtd_nota.get(ped.produto_id)
        if recebido is None:
            o.alerta("ITEM_NAO_FATURADO", f"{ped.nome}: está no pedido ({ped.quantidade} un) mas não foi faturado nesta nota.",
                     campo="prod/qCom", esperado=str(ped.quantidade), encontrado="0")  # fmt: skip
        elif recebido > ped.quantidade:
            o.erro("QUANTIDADE_ACIMA_DO_PEDIDO", f"{ped.nome}: a nota traz {recebido:g} un, acima das {ped.quantidade} un pedidas.",
                   item_numero=primeira_linha[ped.produto_id], campo="prod/qCom", esperado=str(ped.quantidade), encontrado=f"{recebido:g}")  # fmt: skip
        elif recebido < ped.quantidade:
            o.alerta("ENTREGA_PARCIAL", f"{ped.nome}: a nota traz {recebido:g} un de {ped.quantidade} pedidas (entrega parcial).",
                     item_numero=primeira_linha[ped.produto_id], campo="prod/qCom", esperado=str(ped.quantidade), encontrado=f"{recebido:g}")  # fmt: skip


# ---------------------------------------------------------------------------------------------
# 4. Totais
# ---------------------------------------------------------------------------------------------
def _soma(n: NotaFiscal, getter) -> Decimal:
    return sum((getter(i) or ZERO for i in n.itens), ZERO)


def _totais(n: NotaFiscal, o: _Saida) -> None:
    tol_item = CENTAVO
    for i in n.itens:
        calculado = i.quantidade * i.valor_unitario
        if abs(calculado - i.valor_produto) > tol_item:
            o.erro("ITEM_TOTAL_INCONSISTENTE", f"Item {i.numero}: quantidade × valor unitário ({brl(calculado)}) difere do valor do produto ({brl(i.valor_produto)}).",
                   item_numero=i.numero, campo="prod/vProd", esperado=_s(calculado), encontrado=_s(i.valor_produto))  # fmt: skip

    t = n.totais
    if not t:
        o.erro(
            "TOTAIS_AUSENTES",
            "A nota não traz o grupo de totais (ICMSTot).",
            campo="total/ICMSTot",
            base_legal=BASE_LEIAUTE,
        )
        return
    tol = Decimal("0.02") + Decimal("0.001") * len(n.itens)

    def conferir(campo: str, soma: Decimal, codigo: str = "TOTAL_IMPOSTO_DIVERGENTE") -> None:
        if campo in t and abs(t[campo] - soma) > tol:
            o.erro(codigo, f"O total {campo} da nota ({brl(t[campo])}) difere da soma dos itens ({brl(soma)}).",
                   campo=f"total/{campo}", esperado=_s(soma), encontrado=_s(t[campo]), base_legal=BASE_LEIAUTE)  # fmt: skip

    conferir("vProd", _soma(n, lambda i: i.valor_produto), "TOTAL_PRODUTOS_DIVERGENTE")
    for campo, getter in (("vFrete", lambda i: i.valor_frete), ("vSeg", lambda i: i.valor_seguro),
                          ("vDesc", lambda i: i.valor_desconto), ("vOutro", lambda i: i.valor_outros)):  # fmt: skip
        soma = _soma(n, getter)
        if soma:  # informado por item: precisa fechar com o total
            conferir(campo, soma, "TOTAL_PRODUTOS_DIVERGENTE")

    def icms(campo: str):
        return lambda i: i.icms.get(campo) if i.icms else None

    conferir("vBC", _soma(n, icms("vBC")))
    conferir("vICMS", _soma(n, icms("vICMS")))
    conferir("vBCST", _soma(n, icms("vBCST")))
    conferir("vST", _soma(n, icms("vICMSST")))
    conferir("vFCP", _soma(n, icms("vFCP")))
    conferir("vFCPST", _soma(n, icms("vFCPST")))
    conferir("vIPI", _soma(n, lambda i: i.ipi.valor if i.ipi else None))
    conferir("vPIS", _soma(n, lambda i: i.pis.valor if i.pis else None))
    conferir("vCOFINS", _soma(n, lambda i: i.cofins.valor if i.cofins else None))

    if "vNF" in t:
        g = lambda k: t.get(k, ZERO)  # noqa: E731
        esperado = (g("vProd") - g("vDesc") - g("vICMSDeson") + g("vFCPST") + g("vST") + g("vFrete")
                    + g("vSeg") + g("vOutro") + g("vII") + g("vIPI") + g("vIPIDevol"))  # fmt: skip
        if abs(t["vNF"] - esperado) > tol:
            o.erro("TOTAL_NF_DIVERGENTE", f"O valor total da nota ({brl(t['vNF'])}) não fecha com seus componentes ({brl(esperado)}): produtos − descontos + ST + FCP-ST + frete + seguro + outras despesas + II + IPI.",
                   campo="total/vNF", esperado=_s(esperado), encontrado=_s(t["vNF"]), base_legal=BASE_LEIAUTE)  # fmt: skip


# ---------------------------------------------------------------------------------------------
# 5. Frete
# ---------------------------------------------------------------------------------------------
def _frete(n: NotaFiscal, pedido: PedidoCtx, cfg: ConfigCtx, o: _Saida) -> None:
    frete = max(n.totais.get("vFrete", ZERO), _soma(n, lambda i: i.valor_frete))
    sem_frete = (n.emit_municipio or "") in cfg.frete_zero_municipios
    local = f"{n.emit_municipio_nome or n.emit_municipio}/{n.emit_uf}"

    if sem_frete and frete > 0:
        o.erro("FRETE_INDEVIDO", f"Fornecedor de {local} não cobra frete na nota, mas a nota traz frete de {brl(frete)}.",
               campo="total/vFrete", esperado="0,00", encontrado=_s(frete), base_legal=BASE_FRETE)  # fmt: skip
    elif frete > pedido.frete_previsto + CENTAVO:
        o.erro("FRETE_ACIMA_DO_PEDIDO", f"O frete da nota ({brl(frete)}) é maior que o previsto no pedido ({brl(pedido.frete_previsto)}).",
               campo="total/vFrete", esperado=_s(pedido.frete_previsto), encontrado=_s(frete))  # fmt: skip

    if sem_frete:
        acessorias = n.totais.get("vOutro", ZERO) + n.totais.get("vSeg", ZERO)
        if acessorias > 0:
            o.alerta("DESPESA_ACESSORIA_EM_FORNECEDOR_SEM_FRETE", f"Fornecedor de {local} não cobra frete, mas a nota tem {brl(acessorias)} em seguro/outras despesas: verifique se não é frete disfarçado.",
                     campo="total/vOutro", esperado="0,00", encontrado=_s(acessorias), base_legal=BASE_FRETE)  # fmt: skip
    if n.modalidade_frete == "1" and frete > 0:
        o.alerta("FRETE_MODALIDADE_INCOERENTE", "A modalidade de frete indica transporte por conta do destinatário (FOB), mas a nota cobra frete.",
                 campo="transp/modFrete", esperado="0 (CIF) ou frete zerado", encontrado="1 (FOB) com frete")  # fmt: skip


# ---------------------------------------------------------------------------------------------
# 6. Impostos por item
# ---------------------------------------------------------------------------------------------
def _pct(base: Decimal, aliquota: Decimal) -> Decimal:
    return base * aliquota / Decimal(100)


def _icms_item(n: NotaFiscal, i: ItemNota, cfg: ConfigCtx, o: _Saida, flags: set[str]) -> None:
    ic = i.icms
    if ic is None:
        o.alerta("ICMS_AUSENTE", f"Item {i.numero}: sem grupo de ICMS.", item_numero=i.numero, campo="imposto/ICMS")
        return
    if ic.csosn is not None:
        flags.add("simples")
        return
    cst = ic.cst or ""
    base_item = i.valor_produto + i.valor_frete + i.valor_seguro + i.valor_outros - i.valor_desconto
    v_bc, p_icms, v_icms = ic.get("vBC"), ic.get("pICMS"), ic.get("vICMS")

    if cst in tabelas.CST_ICMS_TRIBUTADO:
        if v_bc is not None and p_icms is not None and v_icms is not None:
            calculado = _pct(v_bc, p_icms)
            if abs(calculado - v_icms) > CENTAVO:
                o.erro("ICMS_CALCULO_INCORRETO", f"Item {i.numero}: ICMS de {brl(v_icms)} não bate com base × alíquota ({brl(v_bc)} × {p_icms:g}% = {brl(calculado)}).",
                       item_numero=i.numero, campo="ICMS/vICMS", esperado=_s(calculado), encontrado=_s(v_icms))  # fmt: skip
        if v_bc is not None and cst == "00" and abs(v_bc - base_item) > Decimal("0.02"):
            ipi = i.ipi.valor if i.ipi and i.ipi.valor else ZERO
            if abs(v_bc - (base_item + ipi)) > Decimal("0.02"):
                o.alerta("ICMS_BASE_DIVERGENTE", f"Item {i.numero}: a base do ICMS ({brl(v_bc)}) difere do valor do item com frete/seguro/despesas e desconto ({brl(base_item)}).",
                         item_numero=i.numero, campo="ICMS/vBC", esperado=_s(base_item), encontrado=_s(v_bc))  # fmt: skip
        red = ic.get("pRedBC")
        if cst == "20" and v_bc is not None and red is not None:
            esperado = base_item * (1 - red / Decimal(100))
            if abs(v_bc - esperado) > Decimal("0.02"):
                o.alerta("ICMS_BASE_REDUZIDA_DIVERGENTE", f"Item {i.numero}: a base reduzida ({brl(v_bc)}) não corresponde à redução de {red:g}% ({brl(esperado)}).",
                         item_numero=i.numero, campo="ICMS/vBC", esperado=_s(esperado), encontrado=_s(v_bc))  # fmt: skip
        if p_icms is not None and n.emit_uf and n.dest_uf:
            if n.emit_uf != n.dest_uf:
                esp = Decimal(tabelas.aliquota_interestadual(n.emit_uf, n.dest_uf, ic.orig))
                if p_icms != esp:
                    o.alerta("ALIQUOTA_INTERESTADUAL_DIVERGENTE", f"Item {i.numero}: alíquota de ICMS {p_icms:g}% em operação {n.emit_uf}→{n.dest_uf}; o esperado é {esp:g}% (salvo benefício fiscal).",
                             item_numero=i.numero, campo="ICMS/pICMS", esperado=f"{esp:g}", encontrado=f"{p_icms:g}", base_legal=BASE_INTERESTADUAL)  # fmt: skip
            elif cfg.aliquota_interna_icms is None:
                flags.add("sem_aliquota_interna")
            elif p_icms != cfg.aliquota_interna_icms:
                o.erro("ALIQUOTA_INTERNA_DIVERGENTE", f"Item {i.numero}: alíquota interna de ICMS {p_icms:g}%; a configurada pela empresa é {cfg.aliquota_interna_icms:g}%.",
                       item_numero=i.numero, campo="ICMS/pICMS", esperado=f"{cfg.aliquota_interna_icms:g}", encontrado=f"{p_icms:g}",
                       base_legal="Alíquota configurada em Parâmetros fiscais")  # fmt: skip

    # substituição tributária
    v_bc_st, p_st, v_st = ic.get("vBCST"), ic.get("pICMSST"), ic.get("vICMSST")
    if cst in tabelas.CST_ICMS_COM_ST and v_bc_st is not None and p_st is not None and v_st is not None:
        proprio = v_icms if (v_icms is not None and cst != "30") else ZERO
        esperado = _pct(v_bc_st, p_st) - proprio
        if abs(esperado - v_st) > CENTAVO:
            o.erro("ICMS_ST_CALCULO_INCORRETO", f"Item {i.numero}: ICMS-ST de {brl(v_st)} não bate com base ST × alíquota − ICMS próprio ({brl(v_bc_st)} × {p_st:g}% − {brl(proprio)} = {brl(esperado)}).",
                   item_numero=i.numero, campo="ICMS/vICMSST", esperado=_s(esperado), encontrado=_s(v_st), base_legal=BASE_ST)  # fmt: skip
    # fundo de combate à pobreza (FCP)
    for base_k, pct_k, val_k, cod in (("vBCFCP", "pFCP", "vFCP", "FCP_CALCULO_INCORRETO"),
                                      ("vBCFCPST", "pFCPST", "vFCPST", "FCP_ST_CALCULO_INCORRETO")):  # fmt: skip
        b, p, v = ic.get(base_k), ic.get(pct_k), ic.get(val_k)
        if b is not None and p is not None and v is not None and abs(_pct(b, p) - v) > CENTAVO:
            o.erro(cod, f"Item {i.numero}: {val_k} de {brl(v)} não bate com base × alíquota ({brl(b)} × {p:g}% = {brl(_pct(b, p))}).",
                   item_numero=i.numero, campo=f"ICMS/{val_k}", esperado=_s(_pct(b, p)), encontrado=_s(v))  # fmt: skip
    if cst in {"40", "41", "50"} and (v_icms or ZERO) > 0:
        o.alerta("ICMS_DESTACADO_EM_CST_ISENTO", f"Item {i.numero}: CST {cst} (isento/não tributado/suspenso) com ICMS destacado.",
                 item_numero=i.numero, campo="ICMS/vICMS", esperado="0,00", encontrado=_s(v_icms or ZERO))  # fmt: skip


def _cfop_item(n: NotaFiscal, i: ItemNota, o: _Saida) -> None:
    cfop = i.cfop or ""
    if len(cfop) != 4 or not cfop.isdigit():
        o.erro(
            "CFOP_INVALIDO",
            f"Item {i.numero}: CFOP inválido ({cfop or 'vazio'}).",
            item_numero=i.numero,
            campo="prod/CFOP",
            encontrado=cfop or None,
        )
        return
    if cfop[0] in "123":
        o.erro("CFOP_DE_ENTRADA", f"Item {i.numero}: CFOP {cfop} é de entrada; a nota de venda do fornecedor usa CFOP iniciado em 5 ou 6.",
               item_numero=i.numero, campo="prod/CFOP", esperado="5xxx ou 6xxx", encontrado=cfop)  # fmt: skip
    elif n.emit_uf and n.dest_uf and cfop[0] in "56":
        esperado = "5" if n.emit_uf == n.dest_uf else "6"
        if cfop[0] != esperado:
            tipo = "dentro do estado" if esperado == "5" else "interestadual"
            o.erro("CFOP_UF_INCOERENTE", f"Item {i.numero}: CFOP {cfop} não combina com a operação {tipo} ({n.emit_uf}→{n.dest_uf}).",
                   item_numero=i.numero, campo="prod/CFOP", esperado=f"{esperado}xxx", encontrado=cfop)  # fmt: skip
    cst = i.icms.cst if i.icms else None
    if cst:
        sufixo = cfop[1:]
        if sufixo == "405" and cst != "60":
            o.alerta(
                "CFOP_CST_INCOERENTE",
                f"Item {i.numero}: CFOP {cfop} (ST já retida) pede CST 60; a nota traz CST {cst}.",
                item_numero=i.numero,
                campo="ICMS/CST",
                esperado="60",
                encontrado=cst,
            )
        elif sufixo in {"401", "403"} and cst not in tabelas.CST_ICMS_COM_ST:
            o.alerta("CFOP_CST_INCOERENTE", f"Item {i.numero}: CFOP {cfop} (substituto tributário) pede CST 10, 30, 70 ou 90; a nota traz CST {cst}.", item_numero=i.numero, campo="ICMS/CST", encontrado=cst)  # fmt: skip
        elif sufixo in {"101", "102"} and cst in {"10", "30", "60", "70"}:
            o.alerta("CFOP_CST_INCOERENTE", f"Item {i.numero}: CFOP {cfop} (venda sem ST) com CST {cst} (com ST): confira a classificação.", item_numero=i.numero, campo="ICMS/CST", encontrado=cst)  # fmt: skip


def _pis_cofins_item(i: ItemNota, o: _Saida) -> None:
    tributados = []
    for nome, g in (("PIS", i.pis), ("COFINS", i.cofins)):
        if g is None:
            o.alerta(
                f"{nome}_AUSENTE",
                f"Item {i.numero}: sem grupo de {nome}.",
                item_numero=i.numero,
                campo=f"imposto/{nome}",
            )
            continue
        if g.cst in tabelas.CST_PIS_COFINS_TRIBUTADO:
            tributados.append(nome)
            if g.base is not None and g.aliquota is not None and g.valor is not None:
                calculado = _pct(g.base, g.aliquota)
                if abs(calculado - g.valor) > CENTAVO:
                    o.erro(f"{nome}_CALCULO_INCORRETO", f"Item {i.numero}: {nome} de {brl(g.valor)} não bate com base × alíquota ({brl(g.base)} × {g.aliquota:g}% = {brl(calculado)}).",
                           item_numero=i.numero, campo=f"{nome}/v{nome}", esperado=_s(calculado), encontrado=_s(g.valor))  # fmt: skip
        elif g.cst in tabelas.CST_PIS_COFINS_SEM_TRIBUTO and (g.valor or ZERO) > 0:
            o.erro(f"{nome}_VALOR_EM_CST_SEM_TRIBUTO", f"Item {i.numero}: {nome} com CST {g.cst} (sem tributo) mas com valor destacado.",
                   item_numero=i.numero, campo=f"{nome}/v{nome}", esperado="0,00", encontrado=_s(g.valor or ZERO))  # fmt: skip
    if tributados and (i.ncm or "").startswith(tabelas.NCM_MEDICAMENTOS):
        o.alerta("PIS_COFINS_MONOFASICO_REVISAR", f"Item {i.numero}: medicamento (NCM {i.ncm}) com {' e '.join(tributados)} tributado(s). Na revenda, medicamentos costumam ter tributação monofásica com alíquota zero: revise a classificação.",
                 item_numero=i.numero, campo="PIS/CST", encontrado=(i.pis.cst if i.pis else None), base_legal=BASE_MONOFASICO)  # fmt: skip


def _impostos(n: NotaFiscal, cfg: ConfigCtx, o: _Saida) -> set[str]:
    flags: set[str] = set()
    for i in n.itens:
        if not i.ncm or len(i.ncm) != 8 or not i.ncm.isdigit():
            o.erro(
                "NCM_INVALIDO",
                f"Item {i.numero}: NCM inválido ({i.ncm or 'vazio'}); deve ter 8 dígitos.",
                item_numero=i.numero,
                campo="prod/NCM",
                encontrado=i.ncm,
            )
        _cfop_item(n, i, o)
        _icms_item(n, i, cfg, o, flags)
        _pis_cofins_item(i, o)
        ipi = i.ipi
        if ipi and ipi.cst == "50" and ipi.base is not None and ipi.aliquota is not None and ipi.valor is not None:
            calculado = _pct(ipi.base, ipi.aliquota)
            if abs(calculado - ipi.valor) > CENTAVO:
                o.erro("IPI_CALCULO_INCORRETO", f"Item {i.numero}: IPI de {brl(ipi.valor)} não bate com base × alíquota ({brl(ipi.base)} × {ipi.aliquota:g}% = {brl(calculado)}).",
                       item_numero=i.numero, campo="IPI/vIPI", esperado=_s(calculado), encontrado=_s(ipi.valor))  # fmt: skip
    return flags


# ---------------------------------------------------------------------------------------------
# 7. Decreto AL nº 72.101/2020 (atacadistas credenciados de medicamentos) — alcance da conferência
# ---------------------------------------------------------------------------------------------
def _decreto_72101(n: NotaFiscal, fornecedor: FornecedorCtx | None, o: _Saida) -> None:
    tem_medicamento = any((i.ncm or "").startswith(tabelas.NCM_MEDICAMENTOS) for i in n.itens)
    if fornecedor and fornecedor.credenciado_72101:
        o.info("DEC72101_ESCOPO", "Fornecedor marcado como atacadista credenciado no Decreto 72.101/2020 (AL). O ICMS que o atacadista "
               "recolhe nesse regime é apurado mensalmente por ele e não aparece na nota: o sistema confere o ICMS, ICMS-ST e FCP "
               "destacados, não o recolhimento mensal. Confirme o credenciamento na SEFAZ-AL.", base_legal=BASE_DECRETO)  # fmt: skip
        if n.emit_uf and n.emit_uf != "AL":
            o.alerta("DEC72101_EMITENTE_FORA_DE_AL", f"O fornecedor está marcado como credenciado no decreto de Alagoas, mas a nota é de {n.emit_uf}.",
                     campo="emit/UF", esperado="AL", encontrado=n.emit_uf, base_legal=BASE_DECRETO)  # fmt: skip
    elif n.emit_uf == "AL" and tem_medicamento:
        o.info("DEC72101_CREDENCIAMENTO_NAO_INFORMADO", "Emitente de Alagoas com medicamentos: se for atacadista credenciado no Decreto 72.101/2020, "
               "marque isso no cadastro do fornecedor e confirme o credenciamento na SEFAZ-AL.", base_legal=BASE_DECRETO)  # fmt: skip


# ---------------------------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------------------------
@dataclass
class Analise:
    apontamentos: list[Apontamento]
    fornecedor_id: int | None

    @property
    def tem_erro(self) -> bool:
        return any(a.severidade == Severidade.erro for a in self.apontamentos)

    @property
    def tem_alerta(self) -> bool:
        return any(a.severidade == Severidade.alerta for a in self.apontamentos)


def analisar(
    nota: NotaFiscal,
    pedido: PedidoCtx,
    empresa: EmpresaCtx,
    cfg: ConfigCtx,
    agora: datetime | None = None,
) -> Analise:
    """Confere a nota contra o pedido, a empresa e a configuração fiscal."""
    agora = agora or datetime.now(UTC).replace(tzinfo=None)
    o = _Saida()

    _identificacao(nota, empresa, cfg, pedido, agora, o)
    fornecedor = _fornecedor(nota, pedido, o)
    if fornecedor is not None:
        _pedido_x_nota(nota, pedido, fornecedor, cfg, o)
    _totais(nota, o)
    _frete(nota, pedido, cfg, o)
    flags = _impostos(nota, cfg, o)
    _decreto_72101(nota, fornecedor, o)

    if "simples" in flags:
        o.info(
            "ICMS_SIMPLES_NACIONAL",
            "O emitente é optante pelo Simples Nacional (CSOSN): o ICMS dos itens não foi recalculado.",
            campo="ICMS/CSOSN",
        )
    if "sem_aliquota_interna" in flags:
        o.info("ALIQUOTA_INTERNA_NAO_CONFIGURADA", "A alíquota interna de ICMS não está configurada: as operações dentro do estado não tiveram a alíquota validada. "
               "Informe-a em Parâmetros fiscais (o valor vigente depende da legislação estadual e do produto).", campo="ICMS/pICMS")  # fmt: skip
    return Analise(o.itens, fornecedor.id if fornecedor else None)
