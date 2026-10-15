"""Tabelas fiscais estáveis usadas pela conferência.

Só entra aqui o que é regra nacional consolidada. Alíquotas internas e parâmetros que mudam
por decreto estadual NÃO ficam no código: são configuração da empresa (`ConfiguracaoFiscal`).
"""

# Alíquotas interestaduais de ICMS (Resolução do Senado 22/1989 e 13/2012).
_SUL_SUDESTE = {"SP", "RJ", "MG", "PR", "SC", "RS"}  # sem o Espírito Santo
_RECEBEM_7 = {
    "AC", "AP", "AM", "PA", "RO", "RR", "TO", "AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE",
    "DF", "GO", "MT", "MS", "ES",
}  # fmt: skip
# Origem da mercadoria (campo orig) com alíquota de 4%: importadas (1, 2) e com conteúdo de
# importação superior a 40% (3, 8).
ORIGENS_ALIQUOTA_4 = {"1", "2", "3", "8"}

# CST de ICMS (regime normal) em que o imposto próprio é destacado e calculado sobre vBC.
CST_ICMS_TRIBUTADO = {"00", "10", "20", "70", "90"}
CST_ICMS_COM_ST = {"10", "30", "70", "90"}

# CST de PIS/COFINS com alíquota e valor calculados sobre a base.
CST_PIS_COFINS_TRIBUTADO = {"01", "02"}
# CST de PIS/COFINS sem tributo: 04 monofásica (alíquota zero), 05 ST, 06 alíquota zero,
# 07 isenta, 08 sem incidência, 09 suspensão.
CST_PIS_COFINS_SEM_TRIBUTO = {"04", "05", "06", "07", "08", "09"}

# NCM de medicamentos (capítulo 30). Tributação monofásica de PIS/COFINS: Lei 10.147/2000.
NCM_MEDICAMENTOS = ("3003", "3004")


def aliquota_interestadual(uf_origem: str, uf_destino: str, origem_mercadoria: str | None) -> int:
    """Alíquota (%) esperada de ICMS em operação interestadual."""
    if origem_mercadoria in ORIGENS_ALIQUOTA_4:
        return 4
    if uf_origem in _SUL_SUDESTE and uf_destino in _RECEBEM_7:
        return 7
    return 12
