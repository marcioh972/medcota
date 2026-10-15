"""Recebimento de mercadoria: pedido registrado na tela, XML da NF-e e conferência fiscal.

Fluxo: o comprador registra o pedido (ou usa um pedido fechado pelas cotações) → quando a mercadoria
chega, envia o XML da nota → o sistema confere (preços, quantidades, frete, impostos, totais,
autenticidade) e lista os apontamentos → o comprador aceita ou recusa a nota. Notas com erro só podem
ser aceitas pelo gestor, com justificativa.
"""

import logging
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..core.config import settings
from ..core.errors import erro
from ..core.timeutils import agora_utc
from ..enums import (
    DecisaoNFe,
    OrigemPedido,
    Perfil,
    ResultadoNFe,
    StatusPedido,
    StatusRecebimento,
)
from ..models import (
    Empresa,
    Fornecedor,
    NFeApontamento,
    NFeEntrada,
    Pedido,
    PedidoItem,
    Produto,
    Usuario,
)
from ..schemas.recebimento import (
    ApontamentoOut,
    DecisaoIn,
    FornecedorResumoOut,
    NFeDetalheOut,
    NFeResumoOut,
    PedidoManualIn,
    PedidoRecebimentoItemOut,
    PedidoRecebimentoOut,
)
from . import auditoria, fiscal_config
from .fiscal import regras
from .fiscal.parser import XmlInvalido, ler_nfe
from .fiscal.tipos import EmpresaCtx, FornecedorCtx, ItemPedidoCtx, NotaFiscal, PedidoCtx

logger = logging.getLogger(__name__)
CENTAVOS = Decimal("0.01")


# ================================================================== pedido registrado na tela
def registrar_pedido(db: Session, usuario: Usuario, dados: PedidoManualIn) -> Pedido:
    fornecedor = db.scalar(
        select(Fornecedor).where(Fornecedor.id == dados.fornecedor_id, Fornecedor.empresa_id == usuario.empresa_id)
    )
    if fornecedor is None:  # inexistente OU de outra empresa
        raise erro(404, "fornecedor_nao_encontrado", "Fornecedor não encontrado", campo="fornecedor_id")

    ids = [i.produto_id for i in dados.itens]
    produtos = {
        p.id for p in db.scalars(select(Produto).where(Produto.empresa_id == usuario.empresa_id, Produto.id.in_(ids)))
    }
    faltando = [i for i in ids if i not in produtos]
    if faltando:
        raise erro(404, "produto_nao_encontrado", f"Produto(s) não encontrado(s): {faltando}", campo="itens")

    itens = [
        PedidoItem(
            produto_id=i.produto_id,
            fornecedor_id=fornecedor.id,
            quantidade=i.quantidade,
            preco=i.preco,
            custo_final=(i.preco * i.quantidade).quantize(CENTAVOS, rounding=ROUND_HALF_UP),
        )
        for i in dados.itens
    ]
    total = sum((i.custo_final for i in itens), Decimal("0")) + dados.frete_previsto
    # RN-06: acima da alçada precisa de aprovação do gestor (o gestor aprova os próprios pedidos)
    aprovado = usuario.perfil == Perfil.gestor or total <= settings.alcada_aprovacao
    pedido = Pedido(
        empresa_id=usuario.empresa_id,
        criado_por=usuario.id,
        total=total,
        itens=itens,
        origem=OrigemPedido.manual,
        status=StatusPedido.aprovado if aprovado else StatusPedido.aguardando_aprovacao,
        recebimento=StatusRecebimento.aguardando_nfe,
        numero_externo=dados.numero_externo,
        frete_previsto=dados.frete_previsto,
        observacao=dados.observacao,
    )
    db.add(pedido)
    db.flush()
    auditoria.registrar(
        db, usuario.empresa_id, usuario.id, "registrou_pedido_manual", "pedido", pedido.id, f"total {total}"
    )
    db.commit()
    return pedido


def _pedido_da_empresa(db: Session, empresa_id: int, pedido_id: int) -> Pedido:
    p = db.scalar(
        select(Pedido)
        .where(Pedido.id == pedido_id, Pedido.empresa_id == empresa_id)
        .options(selectinload(Pedido.itens))
    )
    if p is None:  # inexistente OU de outra empresa
        raise erro(404, "pedido_nao_encontrado", "Pedido não encontrado")
    return p


# ================================================================== leitura (montagem das saídas)
def _resumo(n: NFeEntrada) -> NFeResumoOut:
    contagem: dict[str, int] = defaultdict(int)
    for a in n.apontamentos:
        contagem[a.severidade.value] += 1
    return NFeResumoOut(
        id=n.id,
        pedido_id=n.pedido_id,
        chave_acesso=n.chave_acesso,
        numero=n.numero,
        serie=n.serie,
        emitente_nome=n.emitente_nome,
        emitente_cnpj=n.emitente_cnpj,
        data_emissao=n.data_emissao,
        valor_total=n.valor_total,
        valor_frete=n.valor_frete,
        resultado=n.resultado,
        decisao=n.decisao,
        importada_em=n.importada_em,
        erros=contagem["erro"],
        alertas=contagem["alerta"],
        infos=contagem["info"],
    )


def detalhe_nfe(n: NFeEntrada) -> NFeDetalheOut:
    return NFeDetalheOut(
        **_resumo(n).model_dump(),
        fornecedor_id=n.fornecedor_id,
        protocolo_status=n.protocolo_status,
        justificativa=n.justificativa,
        decisao_em=n.decisao_em,
        versao_regras=n.versao_regras,
        apontamentos=[ApontamentoOut.model_validate(a, from_attributes=True) for a in n.apontamentos],
    )


def montar_pedidos(db: Session, empresa_id: int, pedidos: list[Pedido]) -> list[PedidoRecebimentoOut]:
    """Monta as saídas com 3 consultas (produtos, fornecedores, notas), sem N+1."""
    if not pedidos:
        return []
    produtos_ids = {i.produto_id for p in pedidos for i in p.itens}
    forn_ids = {i.fornecedor_id for p in pedidos for i in p.itens}
    produtos = {
        p.id: p
        for p in db.scalars(select(Produto).where(Produto.empresa_id == empresa_id, Produto.id.in_(produtos_ids)))
    }
    fornecedores = {
        f.id: f
        for f in db.scalars(select(Fornecedor).where(Fornecedor.empresa_id == empresa_id, Fornecedor.id.in_(forn_ids)))
    }
    notas: dict[int, list[NFeEntrada]] = defaultdict(list)
    for n in db.scalars(
        select(NFeEntrada)
        .where(NFeEntrada.empresa_id == empresa_id, NFeEntrada.pedido_id.in_([p.id for p in pedidos]))
        .options(selectinload(NFeEntrada.apontamentos))
        .order_by(NFeEntrada.id.desc())
    ):
        notas[n.pedido_id].append(n)

    saida = []
    for p in pedidos:
        fs = {i.fornecedor_id for i in p.itens}
        saida.append(
            PedidoRecebimentoOut(
                id=p.id,
                criado_em=p.criado_em,
                origem=p.origem,
                status=p.status,
                recebimento=p.recebimento,
                total=p.total,
                frete_previsto=p.frete_previsto,
                numero_externo=p.numero_externo,
                observacao=p.observacao,
                fornecedores=[
                    FornecedorResumoOut(
                        id=fornecedores[f].id,
                        nome=fornecedores[f].nome,
                        cnpj=fornecedores[f].cnpj,
                        credenciado_72101=fornecedores[f].credenciado_72101,
                    )
                    for f in sorted(fs)
                    if f in fornecedores
                ],
                itens=[
                    PedidoRecebimentoItemOut(
                        produto_id=i.produto_id,
                        produto=produtos[i.produto_id].nome if i.produto_id in produtos else "(produto removido)",
                        ean=produtos[i.produto_id].ean if i.produto_id in produtos else None,
                        fornecedor_id=i.fornecedor_id,
                        quantidade=i.quantidade,
                        preco=i.preco,
                    )
                    for i in p.itens
                ],
                nfes=[_resumo(n) for n in notas.get(p.id, [])],
            )
        )
    return saida


def listar_pedidos(
    db: Session, empresa_id: int, recebimento: StatusRecebimento | None, limit: int, offset: int
) -> list[PedidoRecebimentoOut]:
    q = (
        select(Pedido)
        .where(Pedido.empresa_id == empresa_id, Pedido.status != StatusPedido.reprovado)
        .options(selectinload(Pedido.itens))
        .order_by(Pedido.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if recebimento is not None:
        q = q.where(Pedido.recebimento == recebimento)
    return montar_pedidos(db, empresa_id, list(db.scalars(q)))


def obter_pedido(db: Session, empresa_id: int, pedido_id: int) -> PedidoRecebimentoOut:
    return montar_pedidos(db, empresa_id, [_pedido_da_empresa(db, empresa_id, pedido_id)])[0]


def _nfe_da_empresa(db: Session, empresa_id: int, nfe_id: int) -> NFeEntrada:
    n = db.scalar(
        select(NFeEntrada)
        .where(NFeEntrada.id == nfe_id, NFeEntrada.empresa_id == empresa_id)
        .options(selectinload(NFeEntrada.apontamentos))
    )
    if n is None:
        raise erro(404, "nfe_nao_encontrada", "Nota fiscal não encontrada")
    return n


def obter_nfe(db: Session, empresa_id: int, nfe_id: int) -> NFeEntrada:
    return _nfe_da_empresa(db, empresa_id, nfe_id)


def listar_nfes(db: Session, empresa_id: int, pedido_id: int | None, limit: int, offset: int) -> list[NFeEntrada]:
    q = (
        select(NFeEntrada)
        .where(NFeEntrada.empresa_id == empresa_id)
        .options(selectinload(NFeEntrada.apontamentos))
        .order_by(NFeEntrada.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if pedido_id is not None:
        q = q.where(NFeEntrada.pedido_id == pedido_id)
    return list(db.scalars(q))


# ================================================================== conferência
def _contexto_pedido(db: Session, empresa_id: int, pedido: Pedido) -> PedidoCtx:
    produtos = {
        p.id: p
        for p in db.scalars(
            select(Produto).where(
                Produto.empresa_id == empresa_id, Produto.id.in_([i.produto_id for i in pedido.itens])
            )
        )
    }
    fornecedores = list(
        db.scalars(
            select(Fornecedor)
            .where(
                Fornecedor.empresa_id == empresa_id,
                Fornecedor.id.in_({i.fornecedor_id for i in pedido.itens}),
            )
            .order_by(Fornecedor.id)
        )
    )
    return PedidoCtx(
        id=pedido.id,
        criado_em=pedido.criado_em,
        frete_previsto=pedido.frete_previsto,
        fornecedores=[FornecedorCtx(f.id, f.nome, f.cnpj, f.credenciado_72101) for f in fornecedores],
        itens=[
            ItemPedidoCtx(
                produto_id=i.produto_id,
                nome=produtos[i.produto_id].nome,
                ean=produtos[i.produto_id].ean,
                ncm=produtos[i.produto_id].ncm,
                fornecedor_id=i.fornecedor_id,
                quantidade=i.quantidade,
                preco=i.preco,
            )
            for i in pedido.itens
            if i.produto_id in produtos
        ],
    )


def _conferir(db: Session, empresa_id: int, pedido: Pedido, nota: NotaFiscal, nfe: NFeEntrada) -> None:
    """Roda o motor de regras e grava o resultado em `nfe` (substitui apontamentos anteriores)."""
    empresa = db.get(Empresa, empresa_id)
    analise = regras.analisar(
        nota,
        _contexto_pedido(db, empresa_id, pedido),
        EmpresaCtx(cnpj=empresa.cnpj if empresa else None),
        fiscal_config.contexto(db, empresa_id),
    )
    nfe.apontamentos.clear()
    db.flush()
    nfe.apontamentos.extend(
        NFeApontamento(
            empresa_id=empresa_id,
            ordem=ordem,
            severidade=a.severidade,
            codigo=a.codigo,
            mensagem=a.mensagem,
            item_numero=a.item_numero,
            campo=a.campo,
            esperado=a.esperado,
            encontrado=a.encontrado,
            base_legal=a.base_legal,
        )
        for ordem, a in enumerate(analise.apontamentos)
    )
    nfe.fornecedor_id = analise.fornecedor_id
    nfe.resultado = (
        ResultadoNFe.reprovada
        if analise.tem_erro
        else ResultadoNFe.com_alertas
        if analise.tem_alerta
        else ResultadoNFe.aprovada
    )
    nfe.versao_regras = regras.VERSAO_REGRAS
    nfe.analisada_em = agora_utc()


def _preencher_dados(nfe: NFeEntrada, nota: NotaFiscal) -> None:
    nfe.numero = nota.numero
    nfe.serie = nota.serie
    nfe.data_emissao = nota.data_emissao
    nfe.emitente_cnpj = nota.emit_cnpj
    nfe.emitente_nome = nota.emit_nome
    nfe.emitente_uf = nota.emit_uf
    nfe.emitente_municipio = nota.emit_municipio
    nfe.destinatario_cnpj = nota.dest_cnpj
    nfe.valor_total = nota.totais.get("vNF")
    nfe.valor_frete = nota.totais.get("vFrete")
    nfe.protocolo_status = nota.protocolo_status


def recalcular_recebimento(db: Session, pedido: Pedido) -> None:
    """recebido = todo fornecedor do pedido tem uma nota aceita; em conferência = há nota aguardando decisão."""
    notas = list(db.scalars(select(NFeEntrada).where(NFeEntrada.pedido_id == pedido.id)))
    fornecedores = {i.fornecedor_id for i in pedido.itens}
    aceitos = {n.fornecedor_id for n in notas if n.decisao == DecisaoNFe.aceita}
    if fornecedores and fornecedores <= aceitos:
        pedido.recebimento = StatusRecebimento.recebido
    elif any(n.decisao == DecisaoNFe.pendente for n in notas):
        pedido.recebimento = StatusRecebimento.em_conferencia
    else:
        pedido.recebimento = StatusRecebimento.aguardando_nfe


def enviar_nfe(db: Session, usuario: Usuario, pedido_id: int, conteudo: bytes) -> NFeEntrada:
    pedido = _pedido_da_empresa(db, usuario.empresa_id, pedido_id)
    if pedido.status != StatusPedido.aprovado:
        raise erro(409, "pedido_nao_aprovado", "O pedido ainda não foi aprovado: não é possível receber a nota.")
    if not conteudo:
        raise erro(422, "arquivo_vazio", "O arquivo está vazio.")
    if len(conteudo) > settings.nfe_max_bytes:
        raise erro(413, "arquivo_grande", f"O arquivo excede o limite de {settings.nfe_max_bytes // 1_000_000} MB.")
    try:
        nota = ler_nfe(conteudo)
    except XmlInvalido as e:
        raise erro(422, "xml_invalido", str(e)) from None

    existente = db.scalar(
        select(NFeEntrada.id).where(NFeEntrada.empresa_id == usuario.empresa_id, NFeEntrada.chave_acesso == nota.chave)
    )
    if existente is not None:
        raise erro(409, "nfe_duplicada", "Esta nota fiscal já foi enviada.", nfe_id=existente)

    nfe = NFeEntrada(
        empresa_id=usuario.empresa_id,
        chave_acesso=nota.chave,
        xml=conteudo.decode("utf-8", errors="replace"),
        pedido_id=pedido.id,
        importada_por=usuario.id,
        status="recebida",
    )
    _preencher_dados(nfe, nota)
    db.add(nfe)
    try:
        db.flush()
    except IntegrityError:  # corrida: duas requisições com a mesma nota
        db.rollback()
        raise erro(409, "nfe_duplicada", "Esta nota fiscal já foi enviada.") from None
    _conferir(db, usuario.empresa_id, pedido, nota, nfe)
    db.flush()
    recalcular_recebimento(db, pedido)
    auditoria.registrar(
        db,
        usuario.empresa_id,
        usuario.id,
        "importou_nfe",
        "nfe",
        nfe.id,
        f"pedido {pedido.id} · {nfe.resultado.value}",
    )
    db.commit()
    logger.info("nfe importada id=%s pedido=%s resultado=%s", nfe.id, pedido.id, nfe.resultado.value)
    return _nfe_da_empresa(db, usuario.empresa_id, nfe.id)


def reanalisar(db: Session, usuario: Usuario, nfe_id: int) -> NFeEntrada:
    """Reexecuta a conferência (ex.: depois de cadastrar o CNPJ do fornecedor ou ajustar os parâmetros)."""
    nfe = _nfe_da_empresa(db, usuario.empresa_id, nfe_id)
    if nfe.decisao != DecisaoNFe.pendente:
        raise erro(409, "nfe_ja_decidida", "A nota já foi aceita ou recusada; não pode ser reanalisada.")
    pedido = _pedido_da_empresa(db, usuario.empresa_id, nfe.pedido_id)
    nota = ler_nfe(nfe.xml.encode("utf-8"))
    _conferir(db, usuario.empresa_id, pedido, nota, nfe)
    auditoria.registrar(db, usuario.empresa_id, usuario.id, "reanalisou_nfe", "nfe", nfe.id, nfe.resultado.value)
    db.commit()
    return _nfe_da_empresa(db, usuario.empresa_id, nfe.id)


def decidir(db: Session, usuario: Usuario, nfe_id: int, dados: DecisaoIn) -> NFeEntrada:
    nfe = _nfe_da_empresa(db, usuario.empresa_id, nfe_id)
    if nfe.decisao != DecisaoNFe.pendente:
        raise erro(409, "nfe_ja_decidida", "A nota já foi aceita ou recusada.")
    justificativa = dados.justificativa

    if dados.decisao == DecisaoNFe.aceita:
        if nfe.resultado == ResultadoNFe.reprovada:
            if usuario.perfil != Perfil.gestor:
                raise erro(
                    403,
                    "aceite_exige_gestor",
                    "Nota com erros só pode ser aceita pelo gestor, com justificativa.",
                )
            if len(justificativa) < 10:
                raise erro(
                    422,
                    "justificativa_obrigatoria",
                    "Explique por que a nota com erros será aceita (mín. 10 caracteres).",
                    campo="justificativa",
                )
        nfe.status = "conciliada"
    else:
        if len(justificativa) < 5:
            raise erro(
                422,
                "justificativa_obrigatoria",
                "Informe o motivo da recusa (mín. 5 caracteres).",
                campo="justificativa",
            )
        nfe.status = "divergente"

    nfe.decisao = dados.decisao
    nfe.decisao_por = usuario.id
    nfe.decisao_em = agora_utc()
    nfe.justificativa = justificativa
    pedido = _pedido_da_empresa(db, usuario.empresa_id, nfe.pedido_id)
    db.flush()
    recalcular_recebimento(db, pedido)
    acao = "aceitou_nfe" if dados.decisao == DecisaoNFe.aceita else "recusou_nfe"
    auditoria.registrar(db, usuario.empresa_id, usuario.id, acao, "nfe", nfe.id, f"resultado {nfe.resultado.value}")
    db.commit()
    return _nfe_da_empresa(db, usuario.empresa_id, nfe.id)
