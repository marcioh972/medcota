import { screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { salvarSessao } from "@/features/auth/session"
import type { EmpresaInfo } from "@/lib/types"
import { renderRotas } from "@/test/render"

import { Component as EquipePage } from "./equipe-page"

const json = (status: number, corpo: unknown) =>
  Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }))

const EMPRESA_SEM_CODIGO: EmpresaInfo = { id: 1, nome: "Distribuidora Teste", cnpj: "11222333000181", codigo_validacao: null, codigo_expira_em: null, codigo_ativo: false }
const EMPRESA_COM_CODIGO: EmpresaInfo = { ...EMPRESA_SEM_CODIGO, codigo_validacao: "ABCD-EFGH-JKLM", codigo_expira_em: "2026-12-01T12:00:00", codigo_ativo: true }
const EQUIPE = [
  { id: 1, nome: "Carla Prado", email: "carla@t.com", perfil: "gestor", ativo: true, ver_preco_custo: true },
  { id: 2, nome: "Ana Souza", email: "ana@t.com", perfil: "vendedor", ativo: true, ver_preco_custo: false },
]

describe("Equipe (gestor)", () => {
  const fetchMock = vi.fn()
  let empresa = EMPRESA_SEM_CODIGO

  beforeEach(() => {
    empresa = EMPRESA_SEM_CODIGO
    salvarSessao({ token: "t", nome: "Carla Prado", perfil: "gestor", empresa: "Distribuidora Teste" })
    fetchMock.mockImplementation((url: URL, init: RequestInit) => {
      const caminho = new URL(String(url)).pathname
      const metodo = init.method ?? "GET"
      if (caminho === "/empresa" && metodo === "GET") return json(200, empresa)
      if (caminho === "/empresa/codigo" && metodo === "POST") return json(200, (empresa = EMPRESA_COM_CODIGO))
      if (caminho === "/empresa/codigo" && metodo === "DELETE") return json(200, (empresa = EMPRESA_SEM_CODIGO))
      if (caminho === "/empresa/equipe" && metodo === "GET") return json(200, EQUIPE)
      if (caminho === "/empresa/equipe/2" && metodo === "PATCH") return json(200, { ...EQUIPE[1], ...JSON.parse(String(init.body)) })
      return json(404, { detail: { codigo: "x", mensagem: "?" } })
    })
    vi.stubGlobal("fetch", fetchMock)
  })
  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it("sem código ativo, o gestor gera o código e ele aparece formatado", async () => {
    const user = userEvent.setup()
    renderRotas([{ path: "/equipe", element: <EquipePage /> }], "/equipe")

    expect(await screen.findByText("Sem código ativo")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /gerar código/i }))
    expect(await screen.findByLabelText("Código de validação")).toHaveTextContent("ABCD-EFGH-JKLM")
    expect(screen.queryByText("Sem código ativo")).not.toBeInTheDocument()
  })

  it("gerar um novo código pede confirmação (o anterior deixa de valer)", async () => {
    empresa = EMPRESA_COM_CODIGO
    const user = userEvent.setup()
    renderRotas([{ path: "/equipe", element: <EquipePage /> }], "/equipe")

    await user.click(await screen.findByRole("button", { name: /gerar novo código/i }))
    const dialogo = await screen.findByRole("alertdialog")
    expect(dialogo).toHaveTextContent(/deixa de funcionar imediatamente/i)
    await user.click(within(dialogo).getByRole("button", { name: /confirmar/i }))
    expect(fetchMock.mock.calls.some(([u, i]) => new URL(String(u)).pathname === "/empresa/codigo" && i.method === "POST")).toBe(true)
  })

  it("lista a equipe, protege o gestor e altera permissões de um funcionário", async () => {
    const user = userEvent.setup()
    renderRotas([{ path: "/equipe", element: <EquipePage /> }], "/equipe")

    expect(await screen.findByText("Ana Souza")).toBeInTheDocument()
    expect(screen.getByLabelText("Carla Prado está ativo")).toBeDisabled() // gestor não se desativa

    await user.click(screen.getByLabelText("Ana Souza pode ver preços e custos"))
    const chamada = fetchMock.mock.calls.find(([u, i]) => new URL(String(u)).pathname === "/empresa/equipe/2" && i.method === "PATCH")!
    expect(JSON.parse(chamada[1].body)).toEqual({ ver_preco_custo: true })
  })
})
