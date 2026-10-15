import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import { request } from "@/lib/api"
import type { Fornecedor, FornecedorIn, FornecedorPatch, Produto, ProdutoIn } from "@/lib/types"

export const useProdutos = () =>
  useQuery({
    queryKey: ["catalogo", "produtos"],
    queryFn: ({ signal }) => api.get<Produto[]>("/produtos", { limit: 50 }, signal),
  })

export const useFornecedores = () =>
  useQuery({
    queryKey: ["catalogo", "fornecedores"],
    queryFn: ({ signal }) => api.get<Fornecedor[]>("/fornecedores", undefined, signal),
  })

export function useCriarProduto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (dados: ProdutoIn) => api.post<Produto>("/produtos", dados),
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["catalogo", "produtos"] }),
        qc.invalidateQueries({ queryKey: ["produtos"] }), // autocomplete do lançamento de faltas
      ]),
  })
}

export function useCriarFornecedor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (dados: FornecedorIn) => api.post<Fornecedor>("/fornecedores", dados),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["catalogo", "fornecedores"] }),
  })
}

export function useAtualizarFornecedor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...dados }: FornecedorPatch & { id: number }) =>
      request<Fornecedor>(`/fornecedores/${id}`, { method: "PATCH", body: dados }),
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["catalogo", "fornecedores"] }),
        qc.invalidateQueries({ queryKey: ["recebimento"] }), // o detalhe do pedido mostra o CNPJ
      ]),
  })
}
