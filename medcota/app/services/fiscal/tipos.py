"""Estruturas de dados da conferência fiscal (puras: sem banco, sem HTTP)."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ...enums import Severidade

ZERO = Decimal("0")


@dataclass
class ImpostoICMS:
    grupo: str  # ICMS00, ICMS10, ICMSSN102...
    cst: str | None = None  # regime normal
    csosn: str | None = None  # Simples Nacional
    orig: str | None = None
    v: dict[str, Decimal] = field(default_factory=dict)  # vBC, pICMS, vICMS, vBCST, pICMSST, ...

    def get(self, campo: str) -> Decimal | None:
        return self.v.get(campo)


@dataclass
class ImpostoPisCofins:
    cst: str | None = None
    base: Decimal | None = None
    aliquota: Decimal | None = None
    valor: Decimal | None = None


@dataclass
class ImpostoIPI:
    cst: str | None = None
    base: Decimal | None = None
    aliquota: Decimal | None = None
    valor: Decimal | None = None


@dataclass
class ItemNota:
    numero: int
    codigo: str | None
    ean: str | None  # cEAN ("SEM GTIN" vira None)
    ean_trib: str | None
    descricao: str
    ncm: str | None
    cfop: str | None
    unidade: str | None
    quantidade: Decimal
    valor_unitario: Decimal
    valor_produto: Decimal
    valor_frete: Decimal = ZERO
    valor_seguro: Decimal = ZERO
    valor_desconto: Decimal = ZERO
    valor_outros: Decimal = ZERO
    icms: ImpostoICMS | None = None
    pis: ImpostoPisCofins | None = None
    cofins: ImpostoPisCofins | None = None
    ipi: ImpostoIPI | None = None

    @property
    def preco_liquido_unitario(self) -> Decimal:
        """Preço efetivamente pago por unidade: (vProd - vDesc) / qCom."""
        if self.quantidade == 0:
            return self.valor_unitario
        return (self.valor_produto - self.valor_desconto) / self.quantidade


@dataclass
class NotaFiscal:
    chave: str
    versao: str | None
    modelo: str | None
    serie: str | None
    numero: str | None
    data_emissao: datetime | None
    tipo_operacao: str | None  # tpNF: 0 entrada, 1 saída
    finalidade: str | None  # finNFe: 1 normal, 2 complementar, 3 ajuste, 4 devolução
    ambiente: str | None  # tpAmb: 1 produção, 2 homologação
    uf_codigo: str | None  # cUF da identificação
    emit_cnpj: str | None
    emit_nome: str | None
    emit_uf: str | None
    emit_municipio: str | None  # código IBGE
    emit_municipio_nome: str | None
    emit_crt: str | None
    dest_cnpj: str | None
    dest_uf: str | None
    itens: list[ItemNota]
    totais: dict[str, Decimal]  # campos de ICMSTot (vProd, vNF, vFrete, vST, ...)
    modalidade_frete: str | None
    info_complementar: str
    protocolo_status: str | None  # cStat do protNFe
    protocolo_motivo: str | None
    protocolo_chave: str | None


@dataclass
class Apontamento:
    severidade: Severidade
    codigo: str
    mensagem: str
    item_numero: int | None = None
    campo: str | None = None
    esperado: str | None = None
    encontrado: str | None = None
    base_legal: str | None = None


# ---- contexto vindo do sistema (pedido, fornecedor, empresa, configuração) -------------------


@dataclass
class ItemPedidoCtx:
    produto_id: int
    nome: str
    ean: str | None
    ncm: str
    fornecedor_id: int
    quantidade: int
    preco: Decimal


@dataclass
class FornecedorCtx:
    id: int
    nome: str
    cnpj: str | None
    credenciado_72101: bool


@dataclass
class PedidoCtx:
    id: int
    criado_em: datetime
    frete_previsto: Decimal
    itens: list[ItemPedidoCtx]
    fornecedores: list[FornecedorCtx]


@dataclass
class ConfigCtx:
    aliquota_interna_icms: Decimal | None = None
    tolerancia_preco_pct: Decimal = ZERO
    frete_zero_municipios: frozenset[str] = frozenset({"2704302"})  # Maceió/AL
    exigir_protocolo: bool = True


@dataclass
class EmpresaCtx:
    cnpj: str | None
