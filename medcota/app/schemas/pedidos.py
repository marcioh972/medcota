from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from ..enums import StatusPedido


class PedidoItemOut(BaseModel):
    produto_id: int
    fornecedor_id: int
    quantidade: int
    preco: Decimal | None  # None sem permissão ver_preco_custo (RN-04)
    custo_final: Decimal | None


class PedidoOut(BaseModel):
    id: int
    criado_em: datetime
    total: Decimal | None
    status: StatusPedido
    itens: list[PedidoItemOut]
