import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { renderRotas } from "@/test/render"

import { Component as CadastroEmpresa } from "./cadastro-empresa-page"

const resposta = (status: number, corpo: unknown) =>
  Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }))

const rotas = [
  { path: "/cadastro/empresa", element: <CadastroEmpresa /> },
  { path: "/equipe", element: <p>tela de equipe</p> },
]

async function preencher(user: ReturnType<typeof userEvent.setup>, senha = "Senha-forte-1") {
  await user.type(screen.getByLabelText("Nome da empresa"), "Distribuidora Teste")
  await user.type(screen.getByLabelText("CNPJ"), "11.222.333/0001-81")
  await user.type(screen.getByLabelText("Seu nome"), "Carla Prado")
  await user.type(screen.getByLabelText("E-mail"), "carla@teste.com")
  await user.type(screen.getAllByLabelText(/senha/i, { selector: "input" })[0]!, senha)
  await user.type(screen.getByLabelText("Confirme a senha"), senha)
}

describe("Cadastro de empresa", () => {
  const fetchMock = vi.fn()
  beforeEach(() => vi.stubGlobal("fetch", fetchMock))
  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it("cadastra, normaliza o CNPJ, entra automaticamente e vai para a Equipe", async () => {
    fetchMock.mockReturnValue(
      resposta(201, { access_token: "tok", token_type: "bearer", perfil: "gestor", nome: "Carla Prado", empresa: "Distribuidora Teste" }),
    )
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/empresa")
    await preencher(user)
    await user.click(screen.getByRole("button", { name: /cadastrar empresa/i }))

    expect(await screen.findByText("tela de equipe")).toBeInTheDocument()
    const [url, init] = fetchMock.mock.calls[0]!
    expect(String(url)).toContain("/cadastro/empresa")
    expect(JSON.parse(init.body)).toEqual({
      empresa_nome: "Distribuidora Teste",
      cnpj: "11222333000181",
      gestor_nome: "Carla Prado",
      email: "carla@teste.com",
      senha: "Senha-forte-1",
    })
    expect(JSON.parse(init.body)).not.toHaveProperty("confirmar")
  })

  it("mostra o checklist da senha e bloqueia senha fraca sem chamar a API", async () => {
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/empresa")
    await preencher(user, "abc")
    const lista = screen.getByRole("list", { name: /requisitos da senha/i })
    expect(lista).toHaveTextContent("Uma letra minúscula")
    await user.click(screen.getByRole("button", { name: /cadastrar empresa/i }))

    expect(await screen.findByText(/a senha precisa ter/i)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("valida CNPJ e confirmação de senha no cliente", async () => {
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/empresa")
    await user.type(screen.getByLabelText("CNPJ"), "11.222.333/0001-80")
    await user.type(screen.getAllByLabelText(/senha/i, { selector: "input" })[0]!, "Senha-forte-1")
    await user.type(screen.getByLabelText("Confirme a senha"), "Senha-forte-2")
    await user.click(screen.getByRole("button", { name: /cadastrar empresa/i }))

    expect(await screen.findByText("CNPJ inválido")).toBeInTheDocument()
    expect(screen.getByText("As senhas não conferem")).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("mostra no campo o erro devolvido pela API (CNPJ já cadastrado)", async () => {
    fetchMock.mockReturnValue(
      resposta(409, { detail: { codigo: "cnpj_em_uso", mensagem: "Já existe uma empresa cadastrada com este CNPJ.", campo: "cnpj" } }),
    )
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/empresa")
    await preencher(user)
    await user.click(screen.getByRole("button", { name: /cadastrar empresa/i }))

    expect(await screen.findByText("Já existe uma empresa cadastrada com este CNPJ.")).toBeInTheDocument()
    expect(screen.queryByText("tela de equipe")).not.toBeInTheDocument()
  })

  it("o botão de olho alterna a visibilidade da senha", async () => {
    const user = userEvent.setup()
    renderRotas(rotas, "/cadastro/empresa")
    const campo = screen.getAllByLabelText(/senha/i, { selector: "input" })[0]!
    expect(campo).toHaveAttribute("type", "password")
    await user.click(screen.getAllByRole("button", { name: /mostrar senha/i })[0]!)
    expect(campo).toHaveAttribute("type", "text")
  })
})
