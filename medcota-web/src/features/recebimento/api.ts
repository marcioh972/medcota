import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api, request } from "@/lib/api"
import type {
  ConfiguracaoFiscal,
  DecisaoNFe,
  NFeDetalhe,
  PedidoManualIn,
  PedidoRecebimento,
  StatusRecebimento,
} from "@/lib/types"

const chaves = {
  pedidos: (situacao?: StatusRecebimento) => ["recebimento", "pedidos", situacao ?? "todos"] as const,
  pedido: (id: number) => ["recebimento", "pedido", id] as const,
  config: ["fiscal", "configuracao"] as const,
}

export const usePedidosRecebimento = (situacao?: StatusRecebimento) =>
  useQuery({
    queryKey: chaves.pedidos(situacao),
    queryFn: ({ signal }) =>
      api.get<PedidoRecebimento[]>("/recebimento/pedidos", { situacao, limit: 100 }, signal),
  })

export const usePedidoRecebimento = (id: number) =>
  useQuery({
    queryKey: chaves.pedido(id),
    queryFn: ({ signal }) => api.get<PedidoRecebimento>(`/recebimento/pedidos/${id}`, undefined, signal),
    enabled: Number.isFinite(id),
  })

export const useConfiguracaoFiscal = () =>
  useQuery({
    queryKey: chaves.config,
    queryFn: ({ signal }) => api.get<ConfiguracaoFiscal>("/fiscal/configuracao", undefined, signal),
  })

/** Invalida a lista e o detalhe do pedido depois de qualquer mudança no recebimento. */
function useInvalidarRecebimento() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: ["recebimento"] })
}

export function useRegistrarPedido() {
  const invalidar = useInvalidarRecebimento()
  return useMutation({
    mutationFn: (dados: PedidoManualIn) => api.post<PedidoRecebimento>("/recebimento/pedidos", dados),
    onSuccess: invalidar,
  })
}

export function useEnviarNfe(pedidoId: number) {
  const invalidar = useInvalidarRecebimento()
  return useMutation({
    mutationFn: (arquivo: File) => {
      const formData = new FormData()
      formData.append("arquivo", arquivo)
      return request<NFeDetalhe>(`/recebimento/pedidos/${pedidoId}/nfe`, { method: "POST", formData })
    },
    onSuccess: invalidar,
  })
}

export const useNfe = (id: number | null) =>
  useQuery({
    queryKey: ["recebimento", "nfe", id],
    queryFn: ({ signal }) => api.get<NFeDetalhe>(`/recebimento/nfes/${id}`, undefined, signal),
    enabled: id !== null,
  })

export function useDecidirNfe() {
  const invalidar = useInvalidarRecebimento()
  return useMutation({
    mutationFn: ({ id, decisao, justificativa }: { id: number; decisao: Exclude<DecisaoNFe, "pendente">; justificativa: string }) =>
      api.post<NFeDetalhe>(`/recebimento/nfes/${id}/decisao`, { decisao, justificativa }),
    onSuccess: invalidar,
  })
}

export function useReanalisarNfe() {
  const invalidar = useInvalidarRecebimento()
  return useMutation({
    mutationFn: (id: number) => api.post<NFeDetalhe>(`/recebimento/nfes/${id}/reanalisar`),
    onSuccess: invalidar,
  })
}

export function useSalvarConfiguracaoFiscal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (dados: Omit<ConfiguracaoFiscal, "atualizada_em">) =>
      request<ConfiguracaoFiscal>("/fiscal/configuracao", { method: "PUT", body: dados }),
    onSuccess: (config) => qc.setQueryData(chaves.config, config),
  })
}
