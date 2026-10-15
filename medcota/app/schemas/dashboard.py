from decimal import Decimal

from pydantic import BaseModel


class DashOut(BaseModel):
    economia_gerada: Decimal | None  # None sem permissão ver_preco_custo (RN-04)
    taxa_atendimento: float
    itens_em_falta: int
    pedidos: int
