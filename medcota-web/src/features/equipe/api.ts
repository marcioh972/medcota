import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api, request } from "@/lib/api"
import type { EmpresaInfo, Membro } from "@/lib/types"

export const useEmpresa = () =>
  useQuery({ queryKey: ["empresa"], queryFn: ({ signal }) => api.get<EmpresaInfo>("/empresa", undefined, signal) })

export const useEquipe = () =>
  useQuery({ queryKey: ["equipe"], queryFn: ({ signal }) => api.get<Membro[]>("/empresa/equipe", undefined, signal) })

export function useGerarCodigo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<EmpresaInfo>("/empresa/codigo"),
    onSuccess: (empresa) => qc.setQueryData(["empresa"], empresa),
  })
}

export function useRevogarCodigo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => request<EmpresaInfo>("/empresa/codigo", { method: "DELETE" }),
    onSuccess: (empresa) => qc.setQueryData(["empresa"], empresa),
  })
}

export function useAtualizarMembro() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...campos }: { id: number; ativo?: boolean; ver_preco_custo?: boolean }) =>
      request<Membro>(`/empresa/equipe/${id}`, { method: "PATCH", body: campos }),
    onSuccess: (membro) =>
      qc.setQueryData<Membro[]>(["equipe"], (lista) => lista?.map((m) => (m.id === membro.id ? membro : m))),
  })
}
