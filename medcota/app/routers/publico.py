"""Link público do fornecedor (RF-16): sem login, protegido por token imprevisível + rate limit."""

from typing import Annotated

from fastapi import APIRouter, Body, Request, Response

from ..core.config import settings
from ..core.deps import DbSession
from ..core.ratelimit import limiter
from ..schemas.cotacoes import CotacaoPublicaOut, ItemCotacaoPublico, RespostaIn
from ..services import cotacoes as svc

router = APIRouter(prefix="/c", tags=["fornecedor (link público)"])


@router.get("/{token}", response_model=CotacaoPublicaOut)
@limiter.limit(settings.rate_limit_publico)
def abrir_link_publico(request: Request, token: str, db: DbSession):
    """Somente leitura (GET seguro). A contagem de aberturas é feita em POST /abertura."""
    c = svc.cotacao_por_token(db, token)
    return CotacaoPublicaOut(
        fornecedor=c.fornecedor.nome,
        expira_em=c.expira_em,
        rodada=c.rodada,
        itens=[
            ItemCotacaoPublico(item_id=i.id, produto=i.produto.nome, ean=i.produto.ean, demanda=i.quantidade)
            for i in c.itens
        ],
    )


@router.post("/{token}/abertura", status_code=204)
@limiter.limit(settings.rate_limit_publico)
def registrar_abertura(request: Request, token: str, db: DbSession):  # RF-17
    svc.registrar_abertura(db, svc.cotacao_por_token(db, token))
    return Response(status_code=204)


@router.post("/{token}/responder", status_code=204)
@limiter.limit(settings.rate_limit_publico)
def responder_cotacao(
    request: Request,
    token: str,
    db: DbSession,
    respostas: Annotated[list[RespostaIn], Body(min_length=1, max_length=500)],
):
    svc.registrar_respostas(db, svc.cotacao_por_token(db, token), respostas)
    return Response(status_code=204)
