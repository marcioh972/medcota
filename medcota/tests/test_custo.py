from decimal import Decimal

from app.enums import Pagamento
from app.services.comparativo import custo_final


def test_custo_final_a_vista_com_frete_rateado():
    # 10 un * 10,00 = 100 ; -5% = 95 ; + frete 45 / 1 item = 140,00
    assert custo_final(Decimal("10"), 10, Pagamento.a_vista, 1) == Decimal("140.00")


def test_custo_final_rateia_frete_entre_itens():
    # 100 * 0,985 = 98,5 ; frete 45/3 = 15 -> 113,50
    assert custo_final(Decimal("10"), 10, Pagamento.d30, 3) == Decimal("113.50")


def test_arredondamento_half_up_em_centavos():
    # 10 * 9,5 = 95 ; * 0,985 = 93,575 ; + 45 = 138,575 -> 138,58
    assert custo_final(Decimal("9.5"), 10, Pagamento.d30, 1) == Decimal("138.58")
