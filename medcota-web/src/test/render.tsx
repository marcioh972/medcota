import { QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router"

import { ThemeProvider } from "@/components/theme-provider"
import { criarQueryClient } from "@/app/query-client"
import { AuthProvider } from "@/features/auth/auth-provider"

/** Renderiza rotas dentro dos mesmos providers do app, em um roteador em memória. */
export function renderRotas(routes: RouteObject[], inicial: string) {
  const router = createMemoryRouter(routes, { initialEntries: [inicial] })
  const utils = render(
    <ThemeProvider>
      <QueryClientProvider client={criarQueryClient()}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>,
  )
  return { router, ...utils }
}
