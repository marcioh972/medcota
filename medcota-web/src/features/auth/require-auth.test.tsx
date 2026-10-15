import { screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { renderRotas } from "@/test/render"

import { RequireAuth } from "./require-auth"
import { salvarSessao } from "./session"

const rotas = [
  { path: "/login", element: <p>tela de login</p> },
  { path: "/faltas", element: <p>tela de faltas</p> },
  {
    element: <RequireAuth roles={["comprador", "gestor"]} />,
    children: [{ path: "/dashboard", element: <p>painel de compras</p> }],
  },
]

describe("RequireAuth", () => {
  it("sem sessão, redireciona para o login", async () => {
    renderRotas(rotas, "/dashboard")
    expect(await screen.findByText("tela de login")).toBeInTheDocument()
  })

  it("perfil sem permissão volta para a tela do próprio perfil", async () => {
    salvarSessao({ token: "t", nome: "Ana", perfil: "vendedor", empresa: "Empresa A" })
    renderRotas(rotas, "/dashboard")
    expect(await screen.findByText("tela de faltas")).toBeInTheDocument()
  })

  it("perfil permitido acessa a rota", async () => {
    salvarSessao({ token: "t", nome: "Bruno", perfil: "comprador", empresa: "Empresa A" })
    renderRotas(rotas, "/dashboard")
    expect(await screen.findByText("painel de compras")).toBeInTheDocument()
  })
})
