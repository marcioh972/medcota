from decimal import Decimal

from fastapi import APIRouter

from ..core.deps import CompradorOuGestor, DbSession
from ..schemas.cotacoes import ComparativoItem, OfertaOut
from ..services.comparativo import ItemComparado, calcular_comparativo

router = APIRouter(tags=["comparativo"])

_CENTAVOS = Decimal("0.01")


def _item_out(i: ItemComparado, ver_preco: bool) -> ComparativoItem:
    media = i.media_historica.quantize(_CENTAVOS) if (ver_preco and i.media_historica) else None
    return ComparativoItem(
        produto_id=i.produto_id,
        produto=i.produto,
        demanda=i.demanda,
        media_historica=media,
        sem_oferta_valida=i.sem_oferta_valida,
        ofertas=[
            OfertaOut(
                fornecedor=o.fornecedor,
                preco=o.preco if ver_preco else None,
                quantidade=o.quantidade,
                pagamento=o.pagamento,
                prazo_dias=o.prazo_dias,
                custo_final=o.custo_final if ver_preco else None,
                acima_da_media=o.acima_da_media,
                vencedor=o.vencedor,
            )
            for o in i.ofertas
        ],
    )


@router.get("/comparativo", response_model=list[ComparativoItem])
def comparativo(u: CompradorOuGestor, db: DbSession):
    # RN-04: sem a permissão ver_preco_custo, valores monetários vêm nulos
    return [_item_out(i, u.ver_preco_custo) for i in calcular_comparativo(db, u.empresa_id)]
