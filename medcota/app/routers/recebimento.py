"""Módulo de recebimento e conferência fiscal de NF-e (comprador e gestor; nunca o vendedor)."""

from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile

from ..core.config import settings
from ..core.deps import ConferenciaFiscal, DbSession, Gestor
from ..enums import StatusRecebimento
from ..schemas.recebimento import (
    ConfiguracaoFiscalIn,
    ConfiguracaoFiscalOut,
    DecisaoIn,
    NFeDetalheOut,
    NFeResumoOut,
    PedidoManualIn,
    PedidoRecebimentoOut,
)
from ..services import fiscal_config, recebimento

router = APIRouter(prefix="/recebimento", tags=["recebimento e conferência de NF-e"])
fiscal = APIRouter(prefix="/fiscal", tags=["conferência fiscal"])

Limite = Annotated[int, Query(ge=1, le=200)]
Deslocamento = Annotated[int, Query(ge=0)]


@router.post("/pedidos", response_model=PedidoRecebimentoOut, status_code=201)
def registrar_pedido(dados: PedidoManualIn, u: ConferenciaFiscal, db: DbSession):
    pedido = recebimento.registrar_pedido(db, u, dados)
    return recebimento.obter_pedido(db, u.empresa_id, pedido.id)


@router.get("/pedidos", response_model=list[PedidoRecebimentoOut])
def listar_pedidos(
    u: ConferenciaFiscal,
    db: DbSession,
    situacao: StatusRecebimento | None = None,
    limit: Limite = 50,
    offset: Deslocamento = 0,
):
    return recebimento.listar_pedidos(db, u.empresa_id, situacao, limit, offset)


@router.get("/pedidos/{pedido_id}", response_model=PedidoRecebimentoOut)
def obter_pedido(pedido_id: int, u: ConferenciaFiscal, db: DbSession):
    return recebimento.obter_pedido(db, u.empresa_id, pedido_id)


@router.post("/pedidos/{pedido_id}/nfe", response_model=NFeDetalheOut, status_code=201)
def enviar_nfe(pedido_id: int, u: ConferenciaFiscal, db: DbSession, arquivo: Annotated[UploadFile, File()]):
    """Recebe o XML da NF-e, confere contra o pedido e devolve o resultado com os apontamentos."""
    # lê no máximo limite+1 bytes: nunca carrega um arquivo gigante inteiro na memória
    conteudo = arquivo.file.read(settings.nfe_max_bytes + 1)
    return recebimento.detalhe_nfe(recebimento.enviar_nfe(db, u, pedido_id, conteudo))


@router.get("/nfes", response_model=list[NFeResumoOut])
def listar_nfes(
    u: ConferenciaFiscal,
    db: DbSession,
    pedido_id: int | None = None,
    limit: Limite = 50,
    offset: Deslocamento = 0,
):
    return [recebimento._resumo(n) for n in recebimento.listar_nfes(db, u.empresa_id, pedido_id, limit, offset)]


@router.get("/nfes/{nfe_id}", response_model=NFeDetalheOut)
def obter_nfe(nfe_id: int, u: ConferenciaFiscal, db: DbSession):
    return recebimento.detalhe_nfe(recebimento.obter_nfe(db, u.empresa_id, nfe_id))


@router.get("/nfes/{nfe_id}/xml")
def baixar_xml(nfe_id: int, u: ConferenciaFiscal, db: DbSession):
    nfe = recebimento.obter_nfe(db, u.empresa_id, nfe_id)
    return Response(
        content=nfe.xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="NFe{nfe.chave_acesso}.xml"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/nfes/{nfe_id}/reanalisar", response_model=NFeDetalheOut)
def reanalisar(nfe_id: int, u: ConferenciaFiscal, db: DbSession):
    return recebimento.detalhe_nfe(recebimento.reanalisar(db, u, nfe_id))


@router.post("/nfes/{nfe_id}/decisao", response_model=NFeDetalheOut)
def decidir(nfe_id: int, dados: DecisaoIn, u: ConferenciaFiscal, db: DbSession):
    return recebimento.detalhe_nfe(recebimento.decidir(db, u, nfe_id, dados))


# ---------------------------------------------------------------- parâmetros fiscais
@fiscal.get("/configuracao", response_model=ConfiguracaoFiscalOut)
def ler_configuracao(u: ConferenciaFiscal, db: DbSession):
    return fiscal_config.obter(db, u.empresa_id)


@fiscal.put("/configuracao", response_model=ConfiguracaoFiscalOut)
def salvar_configuracao(dados: ConfiguracaoFiscalIn, u: Gestor, db: DbSession):
    # lista de municípios vazia é válida: desliga a regra de "fornecedor local não cobra frete"
    return fiscal_config.atualizar(db, u, dados)
