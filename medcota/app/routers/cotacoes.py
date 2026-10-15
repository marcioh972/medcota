from typing import Annotated

from fastapi import APIRouter, Query

from ..core.deps import Comprador, CompradorOuGestor, DbSession
from ..models import Cotacao
from ..schemas.cotacoes import CotacaoOut
from ..services import cotacoes as svc

router = APIRouter(prefix="/cotacoes", tags=["cotações"])


def cotacao_out(c: Cotacao) -> CotacaoOut:
    return CotacaoOut(
        id=c.id,
        fornecedor=c.fornecedor.nome,
        escopo=c.fornecedor.escopo.value,
        token=c.token,
        url=f"/c/{c.token}",
        expira_em=c.expira_em,
        itens=len(c.itens),
        respostas=sum(1 for i in c.itens if i.resposta),
        rodada=c.rodada,
        aberturas=c.aberturas,
    )


@router.post("/gerar", response_model=list[CotacaoOut], status_code=201)
def gerar_cotacoes(u: Comprador, db: DbSession):
    return [cotacao_out(c) for c in svc.gerar_cotacoes(db, u)]


@router.get("", response_model=list[CotacaoOut])
def listar_cotacoes(
    u: CompradorOuGestor,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return [cotacao_out(c) for c in svc.listar_cotacoes(db, u.empresa_id, limit, offset)]


@router.post("/{cotacao_id}/segunda-rodada", response_model=CotacaoOut)
def segunda_rodada(cotacao_id: int, u: Comprador, db: DbSession):
    return cotacao_out(svc.segunda_rodada(db, u, cotacao_id))
