import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { Consolidado, Cotacao, ItemComparado, Pedido } from "@/lib/types"

export const useConsolidacao = () =>
  useQuery({
    queryKey: ["consolidacao"],
    queryFn: ({ signal }) => api.get<Consolidado[]>("/consolidacao", undefined, signal),
  })

export const useCotacoes = () =>
  useQuery({
    queryKey: ["cotacoes"],
    queryFn: ({ signal }) => api.get<Cotacao[]>("/cotacoes", { limit: 100 }, signal),
  })

export const useComparativo = () =>
  useQuery({
    queryKey: ["comparativo"],
    queryFn: ({ signal }) => api.get<ItemComparado[]>("/comparativo", undefined, signal),
  })

export const usePedidos = () =>
  useQuery({
    queryKey: ["pedidos"],
    queryFn: ({ signal }) => api.get<Pedido[]>("/pedidos", { limit: 100 }, signal),
  })

export function useGerarCotacoes() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<Cotacao[]>("/cotacoes/gerar"),
    onSuccess: () =>
      Promise.all(["cotacoes", "consolidacao", "comparativo"].map((k) => qc.invalidateQueries({ queryKey: [k] }))),
  })
}

export function useSegundaRodada() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.post<Cotacao>(`/cotacoes/${id}/segunda-rodada`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cotacoes"] }),
  })
}

export function useFecharCompra() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<Pedido>("/pedidos"),
    onSettled: () =>
      Promise.all(["pedidos", "comparativo", "consolidacao", "dashboard"].map((k) => qc.invalidateQueries({ queryKey: [k] }))),
  })
}

export function useAprovarPedido() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, aprovado }: { id: number; aprovado: boolean }) =>
      api.post<Pedido>(`/pedidos/${id}/aprovar`, undefined, { aprovado }),
    onSettled: () => Promise.all(["pedidos", "dashboard"].map((k) => qc.invalidateQueries({ queryKey: [k] }))),
  })
}
