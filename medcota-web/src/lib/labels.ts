import type { DecisaoNFe, Pagamento, ResultadoNFe, Severidade, StatusFalta, StatusPedido, StatusRecebimento, Urgencia } from "@/lib/types"

export const PAGAMENTO: Record<Pagamento, string> = {
  a_vista: "À vista",
  "15d": "15 dias",
  "30d": "30 dias",
  "45d": "45 dias",
}

export const URGENCIA: Record<Urgencia, string> = { baixa: "Baixa", media: "Média", alta: "Alta" }

export const STATUS_FALTA: Record<StatusFalta, string> = {
  pendente: "Pendente",
  cotado: "Em cotação",
  comprado: "Comprado",
  sem_oferta: "Sem oferta",
}

export const STATUS_PEDIDO: Record<StatusPedido, string> = {
  aguardando_aprovacao: "Aguardando aprovação",
  aprovado: "Aprovado",
  reprovado: "Reprovado",
}

export const STATUS_RECEBIMENTO: Record<StatusRecebimento, string> = {
  aguardando_nfe: "Aguardando nota",
  em_conferencia: "Em conferência",
  recebido: "Recebido",
}

export const RESULTADO_NFE: Record<ResultadoNFe, string> = {
  aprovada: "Sem apontamentos",
  com_alertas: "Com alertas",
  reprovada: "Com erros",
}

export const DECISAO_NFE: Record<DecisaoNFe, string> = {
  pendente: "Aguardando decisão",
  aceita: "Aceita",
  recusada: "Recusada",
}

export const SEVERIDADE: Record<Severidade, string> = { erro: "Erro", alerta: "Alerta", info: "Informação" }
