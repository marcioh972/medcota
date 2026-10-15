from fastapi import APIRouter

from ..core.deps import CompradorOuGestor, DbSession
from ..schemas.dashboard import DashOut
from ..services.dashboard import indicadores

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashOut)
def dashboard(u: CompradorOuGestor, db: DbSession):
    ind = indicadores(db, u.empresa_id)
    return DashOut(
        economia_gerada=ind.economia_gerada if u.ver_preco_custo else None,  # RN-04
        taxa_atendimento=ind.taxa_atendimento,
        itens_em_falta=ind.itens_em_falta,
        pedidos=ind.pedidos,
    )
