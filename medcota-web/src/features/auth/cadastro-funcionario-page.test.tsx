import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { renderRotas } from "@/test/render"

import { Component as CadastroFuncionario } from "./cadastro-funcionario-page"

const resposta = (status: number, corpo: unknown) =>
  Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }))

const rotas = [
  { path: "/cadastro/funcionario", element: <CadastroFuncionario /> },
  { path: "/faltas", element: <p>tela de faltas</p> },
]

async function preencher(user: ReturnType<typeof userEvent.setup>, codigo: string) {
  if (codigo) await user.type(screen.getByLabelText("Código de validação"), codigo)
  await user.click(screen.getByRole("combobox", { name: /perfil/i }))
  await user.click(await screen.findByRole("option", { name: "Vendedor" }))
  await user.type(screen.getByLabelText("Seu nome"), "Ana Souza")
  await user.type(screen.getByLabelText("E-mail"), "Ana@Teste.com")
  await user.type(screen.getAllByLabelText(/senha/i, { selector: "input" })[0]!, "Senha-forte-1")
  await user.type(screen.getByLabelText("Confirme a senha"), "Senha-forte-1")
}

describe("Cadastro de funcionário", () => {
  const fetchMock = vi.fn()
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock)
    // jsdom não implementa estes métodos usados pelo Select (Radix)
    Element.prototype.hasPointerCapture = () => false
    Element.prototype.scrollIntoView = () => {}
  })
  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it("cadastra com o código (normalizado em maiúsculas) e vai para a tela do perfil", async () => {
    fetchMock.mockReturnValue(
      resposta(201, { access_token: "tok", token_type: "bearer", perfil: "vendedor", nome: "Ana Souza", empresa: "Distribuidora Teste" }),
    )
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/funcionario")
    await preencher(user, "abcd-efgh-jklm")
    await user.click(screen.getByRole("button", { name: /criar conta/i }))

    expect(await screen.findByText("tela de faltas")).toBeInTheDocument()
    const [url, init] = fetchMock.mock.calls[0]!
    expect(String(url)).toContain("/cadastro/funcionario")
    expect(JSON.parse(init.body)).toMatchObject({ codigo: "ABCD-EFGH-JKLM", perfil: "vendedor", nome: "Ana Souza", senha: "Senha-forte-1" })
  })

  it("preenche o código pelo link ?codigo=", async () => {
    renderRotas(rotas, "/cadastro/funcionario?codigo=ABCD-EFGH-JKLM")
    expect(screen.getByLabelText("Código de validação")).toHaveValue("ABCD-EFGH-JKLM")
  })

  it("exige o código antes de chamar a API", async () => {
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/funcionario")
    await preencher(user, "")
    await user.click(screen.getByRole("button", { name: /criar conta/i }))
    expect(await screen.findByText("Informe o código da empresa")).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("mostra no campo o erro de código inválido ou expirado", async () => {
    fetchMock.mockReturnValue(
      resposta(422, { detail: { codigo: "codigo_invalido", mensagem: "Código de validação inválido ou expirado. Peça um novo ao gestor.", campo: "codigo" } }),
    )
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/funcionario")
    await preencher(user, "ZZZZ-ZZZZ-ZZZZ")
    await user.click(screen.getByRole("button", { name: /criar conta/i }))
    expect(await screen.findByText(/inválido ou expirado/i)).toBeInTheDocument()
  })
})
