from typing import Annotated

from fastapi import APIRouter, Query

from ..core.deps import CompradorOuGestor, DbSession, Vendedor
from ..enums import StatusFalta
from ..models import Falta
from ..schemas.faltas import ConsolidadoOut, FaltaIn, FaltaOut
from ..services import faltas as svc

router = APIRouter(tags=["faltas"])


def falta_out(f: Falta) -> FaltaOut:
    detalhe = ""
    if f.status == StatusFalta.comprado and f.pedido_id:
        detalhe = f"pedido #{f.pedido_id}" + (f" · previsão {f.previsao:%d/%m/%Y}" if f.previsao else "")
    return FaltaOut(
        id=f.id,
        produto=f.produto.nome,
        ean=f.produto.ean,
        cliente=f.cliente,
        quantidade=f.quantidade,
        urgencia=f.urgencia,
        status=f.status,
        detalhe=detalhe,
    )


@router.get("/faltas/hoje", response_model=list[FaltaOut])
def minha_lista_hoje(u: Vendedor, db: DbSession):
    return [falta_out(f) for f in svc.listar_hoje_do_vendedor(db, u)]


@router.post("/faltas", response_model=FaltaOut, status_code=201)
def lancar_falta(
    payload: FaltaIn,
    u: Vendedor,
    db: DbSession,
    somar_duplicata: Annotated[bool, Query(description="RF-08: somar ao item já lançado hoje")] = False,
):
    return falta_out(svc.lancar_falta(db, u, payload, somar_duplicata))


@router.get("/consolidacao", response_model=list[ConsolidadoOut])
def consolidacao(u: CompradorOuGestor, db: DbSession):
    return [
        ConsolidadoOut(
            produto_id=g.produto.id,
            produto=g.produto.nome,
            ean=g.produto.ean,
            origem=g.produto.origem.value,
            demanda=g.demanda,
            solicitantes=sorted(g.solicitantes),
            clientes=len(g.clientes),
            urgencia_maxima=g.urgencia,
        )
        for g in svc.consolidar_hoje(db, u.empresa_id)
    ]
