import { QueryClient } from "@tanstack/react-query"

import { ApiError } from "@/lib/api"

export function criarQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // erros 4xx são definitivos (permissão, validação): não adianta repetir
        retry: (tentativas, erro) =>
          !(erro instanceof ApiError && erro.status >= 400 && erro.status < 500) && tentativas < 2,
      },
    },
  })
}
