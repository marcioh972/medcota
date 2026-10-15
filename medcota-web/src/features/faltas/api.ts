import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { Falta, FaltaIn, Produto } from "@/lib/types"

export function useFaltasHoje() {
  return useQuery({
    queryKey: ["faltas", "hoje"],
    queryFn: ({ signal }) => api.get<Falta[]>("/faltas/hoje", undefined, signal),
  })
}

export function useBuscaProdutos(q: string, enabled: boolean) {
  return useQuery({
    queryKey: ["produtos", q],
    queryFn: ({ signal }) => api.get<Produto[]>("/produtos", { q, limit: 20 }, signal),
    enabled,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  })
}

export function useLancarFalta() {
  const qc = useQueryClient()
  return useMutation({
    // `somar` = confirmação do vendedor para duplicata (RF-08)
    mutationFn: ({ dados, somar }: { dados: FaltaIn; somar: boolean }) =>
      api.post<Falta>("/faltas", dados, somar ? { somar_duplicata: true } : undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["faltas", "hoje"] }),
  })
}
