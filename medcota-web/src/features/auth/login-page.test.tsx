import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { renderRotas } from "@/test/render"

import { Component as LoginPage } from "./login-page"

const resposta = (status: number, corpo: unknown) =>
  Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }))

const rotas = [
  { path: "/login", element: <LoginPage /> },
  { path: "/faltas", element: <p>tela de faltas</p> },
  { path: "/dashboard", element: <p>painel</p> },
]

describe("LoginPage", () => {
  const fetchMock = vi.fn()
  beforeEach(() => vi.stubGlobal("fetch", fetchMock))
  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it("valida campos obrigatórios sem chamar a API", async () => {
    renderRotas(rotas, "/login")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))
    expect(await screen.findByText("Informe o e-mail")).toBeInTheDocument()
    expect(screen.getByText("Informe a senha")).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("autentica e leva o vendedor para a tela de faltas", async () => {
    fetchMock.mockReturnValue(
      resposta(200, { access_token: "tok", token_type: "bearer", perfil: "vendedor", nome: "Ana", empresa: "Empresa A" }),
    )
    renderRotas(rotas, "/login")
    await userEvent.type(screen.getByLabelText("E-mail"), "ana@medcota.com.br")
    await userEvent.type(screen.getByLabelText("Senha"), "segredo")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findByText("tela de faltas")).toBeInTheDocument()
    const [, init] = fetchMock.mock.calls[0]!
    expect(String(init.body)).toContain("username=ana%40medcota.com.br")
    expect(init.headers["Content-Type"]).toBe("application/x-www-form-urlencoded")
  })

  it("mostra a mensagem da API em credenciais inválidas", async () => {
    fetchMock.mockReturnValue(
      resposta(401, { detail: { codigo: "credenciais_invalidas", mensagem: "Credenciais inválidas" } }),
    )
    renderRotas(rotas, "/login")
    await userEvent.type(screen.getByLabelText("E-mail"), "ana@medcota.com.br")
    await userEvent.type(screen.getByLabelText("Senha"), "errada")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciais inválidas")
    await waitFor(() => expect(screen.queryByText("tela de faltas")).not.toBeInTheDocument())
  })
})
