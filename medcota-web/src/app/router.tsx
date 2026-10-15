import { createBrowserRouter, Navigate } from "react-router"

import { AppLayout } from "@/components/layout/app-layout"
import { RouteError } from "@/components/route-error"
import { RequireAuth } from "@/features/auth/require-auth"
import { homeDoPerfil } from "@/features/auth/session"
import { useAuth } from "@/features/auth/use-auth"

function Inicio() {
  const { session } = useAuth()
  return <Navigate to={session ? homeDoPerfil(session.perfil) : "/login"} replace />
}

// Cada página é um módulo com `export function Component` e carrega sob demanda (code splitting).
export const router = createBrowserRouter([
  { path: "/", element: <Inicio />, errorElement: <RouteError /> },
  { path: "/login", lazy: () => import("@/features/auth/login-page"), errorElement: <RouteError /> },
  // cadastros públicos: empresa (gestor) e funcionário (com o código de validação da empresa)
  { path: "/cadastro/empresa", lazy: () => import("@/features/auth/cadastro-empresa-page"), errorElement: <RouteError /> },
  { path: "/cadastro/funcionario", lazy: () => import("@/features/auth/cadastro-funcionario-page"), errorElement: <RouteError /> },
  // link público do fornecedor (RF-16): sem login
  { path: "/c/:token", lazy: () => import("@/features/fornecedor/cotacao-publica-page"), errorElement: <RouteError /> },
  {
    element: <RequireAuth />,
    errorElement: <RouteError />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            element: <RequireAuth roles={["vendedor"]} />,
            children: [{ path: "faltas", lazy: () => import("@/features/faltas/faltas-page") }],
          },
          {
            element: <RequireAuth roles={["comprador", "gestor"]} />,
            children: [
              { path: "dashboard", lazy: () => import("@/features/dashboard/dashboard-page") },
              { path: "consolidacao", lazy: () => import("@/features/compras/consolidacao-page") },
              { path: "cotacoes", lazy: () => import("@/features/compras/cotacoes-page") },
              { path: "comparativo", lazy: () => import("@/features/compras/comparativo-page") },
              { path: "pedidos", lazy: () => import("@/features/compras/pedidos-page") },
              { path: "cadastros", lazy: () => import("@/features/catalogo/catalogo-page") },
              { path: "recebimento", lazy: () => import("@/features/recebimento/recebimento-page") },
              { path: "recebimento/novo", lazy: () => import("@/features/recebimento/novo-pedido-page") },
              { path: "recebimento/parametros", lazy: () => import("@/features/recebimento/parametros-fiscais-page") },
              { path: "recebimento/:pedidoId", lazy: () => import("@/features/recebimento/pedido-detalhe-page") },
            ],
          },
          {
            element: <RequireAuth roles={["gestor"]} />,
            children: [{ path: "equipe", lazy: () => import("@/features/equipe/equipe-page") }],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Inicio /> },
])
