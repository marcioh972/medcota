/** Tipos espelhando os schemas da API MedCota. Valores monetários chegam como string (Decimal). */
export type Perfil = "vendedor" | "comprador" | "gestor"
export type StatusFalta = "pendente" | "cotado" | "comprado" | "sem_oferta"
export type Urgencia = "baixa" | "media" | "alta"
export type Pagamento = "a_vista" | "15d" | "30d" | "45d"
export type StatusPedido = "aguardando_aprovacao" | "aprovado" | "reprovado"
export type Escopo = "Local" | "Nacional"

/** Decimal serializado como string, ou null quando o usuário não tem `ver_preco_custo` (RN-04). */
export type Dinheiro = string | null

export interface LoginOut {
  access_token: string
  token_type: string
  perfil: Perfil
  nome: string
  empresa: string
}

export interface Produto {
  id: number
  nome: string
  principio_ativo: string
  ean: string | null
  classe: "Farma" | "Hospitalar"
  origem: Escopo
  controlado: boolean
}

export interface Falta {
  id: number
  produto: string
  ean: string | null
  cliente: string
  quantidade: number
  urgencia: Urgencia
  status: StatusFalta
  detalhe: string
}

export interface FaltaIn {
  produto_id: number
  cliente: string
  quantidade: number
  urgencia: Urgencia
  observacao?: string
}

export interface Consolidado {
  produto_id: number
  produto: string
  ean: string | null
  origem: Escopo
  demanda: number
  solicitantes: string[]
  clientes: number
  urgencia_maxima: Urgencia
}

export interface Cotacao {
  id: number
  fornecedor: string
  escopo: Escopo
  token: string
  url: string
  expira_em: string
  itens: number
  respostas: number
  rodada: number
  aberturas: number
}

export interface Oferta {
  fornecedor: string
  preco: Dinheiro
  quantidade: number
  pagamento: Pagamento
  prazo_dias: number
  custo_final: Dinheiro
  acima_da_media: boolean
  vencedor: boolean
}

export interface ItemComparado {
  produto_id: number
  produto: string
  demanda: number
  media_historica: Dinheiro
  ofertas: Oferta[]
  sem_oferta_valida: boolean
}

export interface PedidoItem {
  produto_id: number
  fornecedor_id: number
  quantidade: number
  preco: Dinheiro
  custo_final: Dinheiro
}

export interface Pedido {
  id: number
  criado_em: string
  total: Dinheiro
  status: StatusPedido
  itens: PedidoItem[]
}

export interface Dashboard {
  economia_gerada: Dinheiro
  taxa_atendimento: number
  itens_em_falta: number
  pedidos: number
}

export interface ItemCotacaoPublico {
  item_id: number
  produto: string
  ean: string | null
  demanda: number
}

export interface CotacaoPublica {
  fornecedor: string
  expira_em: string
  rodada: number
  itens: ItemCotacaoPublico[]
}

export interface RespostaIn {
  item_id: number
  preco: string
  quantidade: number
  prazo_dias: number
  pagamento: Pagamento
  lote?: string
}

export interface Fornecedor {
  id: number
  nome: string
  escopo: Escopo
  email: string
  cnpj: string | null
  /** Atacadista credenciado no Decreto AL 72.101/2020 (informado pela empresa). */
  credenciado_72101: boolean
}

export interface ProdutoIn {
  nome: string
  principio_ativo?: string
  ean?: string
  classe: "Farma" | "Hospitalar"
  origem: Escopo
  controlado: boolean
}

export interface FornecedorIn {
  nome: string
  escopo: Escopo
  email?: string
  cnpj?: string
  credenciado_72101?: boolean
}

export interface FornecedorPatch {
  cnpj?: string | null
  email?: string | null
  credenciado_72101?: boolean
}

export interface EmpresaInfo {
  id: number
  nome: string
  cnpj: string | null
  /** Código formatado (ABCD-EFGH-JKLM), ou null se não houver código. */
  codigo_validacao: string | null
  codigo_expira_em: string | null
  codigo_ativo: boolean
}

export interface Membro {
  id: number
  nome: string
  email: string
  perfil: Perfil
  ativo: boolean
  ver_preco_custo: boolean
}

export interface CadastroEmpresaIn {
  empresa_nome: string
  cnpj: string
  gestor_nome: string
  email: string
  senha: string
}

export interface CadastroFuncionarioIn {
  codigo: string
  nome: string
  email: string
  senha: string
  perfil: "vendedor" | "comprador"
}

// ---- Recebimento e conferência de NF-e
export type Severidade = "erro" | "alerta" | "info"
export type ResultadoNFe = "aprovada" | "com_alertas" | "reprovada"
export type DecisaoNFe = "pendente" | "aceita" | "recusada"
export type StatusRecebimento = "aguardando_nfe" | "em_conferencia" | "recebido"

export interface Apontamento {
  severidade: Severidade
  codigo: string
  mensagem: string
  item_numero: number | null
  campo: string | null
  esperado: string | null
  encontrado: string | null
  base_legal: string | null
}

export interface NFeResumo {
  id: number
  pedido_id: number | null
  chave_acesso: string
  numero: string | null
  serie: string | null
  emitente_nome: string | null
  emitente_cnpj: string | null
  data_emissao: string | null
  valor_total: string | null
  valor_frete: string | null
  resultado: ResultadoNFe
  decisao: DecisaoNFe
  importada_em: string
  erros: number
  alertas: number
  infos: number
}

export interface NFeDetalhe extends NFeResumo {
  fornecedor_id: number | null
  protocolo_status: string | null
  justificativa: string
  decisao_em: string | null
  versao_regras: string | null
  apontamentos: Apontamento[]
}

export interface PedidoRecebimento {
  id: number
  criado_em: string
  origem: "cotacao" | "manual"
  status: StatusPedido
  recebimento: StatusRecebimento
  total: string
  frete_previsto: string
  numero_externo: string | null
  observacao: string
  fornecedores: { id: number; nome: string; cnpj: string | null; credenciado_72101: boolean }[]
  itens: { produto_id: number; produto: string; ean: string | null; fornecedor_id: number; quantidade: number; preco: string }[]
  nfes: NFeResumo[]
}

export interface PedidoManualIn {
  fornecedor_id: number
  itens: { produto_id: number; quantidade: number; preco: string }[]
  frete_previsto: string
  numero_externo?: string
  observacao?: string
}

export interface ConfiguracaoFiscal {
  aliquota_interna_icms: string | null
  tolerancia_preco_pct: string
  frete_zero_municipios: string[]
  exigir_protocolo: boolean
  atualizada_em: string | null
}
