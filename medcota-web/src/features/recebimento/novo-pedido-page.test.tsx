import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { salvarSessao } from "@/features/auth/session"
import { mockApi, polyfillsDeDom } from "@/test/mock-api"
import { renderRotas } from "@/test/render"

import { Component as NovoPedido } from "./novo-pedido-page"

const FORNECEDORES = [{ id: 1, nome: "Alfa Atacado", escopo: "Local", email: "", cnpj: "12ABC34501DE35", credenciado_72101: false }]
const PRODUTOS = [{ id: 10, nome: "Dipirona 500mg", principio_ativo: "", ean: "7896094916010", classe: "Farma", origem: "Local", controlado: false }]

const rotas = [
  { path: "/recebimento/novo", element: <NovoPedido /> },
  { path: "/recebimento/:pedidoId", element: <p>detalhe do pedido</p> },
]

async function escolherFornecedorEProduto(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("combobox", { name: /^fornecedor$/i }))
  await user.click(await screen.findByRole("option", { name: /Alfa Atacado/ }))
  await user.click(screen.getByRole("combobox", { name: /produto/i }))
  await user.click(await screen.findByText("Dipirona 500mg"))
}

describe("Registrar pedido", () => {
  beforeEach(() => {
    polyfillsDeDom()
    salvarSessao({ token: "t", nome: "Bruno", perfil: "comprador", empresa: "Empresa A" })
  })
  afterEach(() => vi.unstubAllGlobals())

  it("registra o pedido normalizando preço e frete e abre o detalhe", async () => {
    const api = mockApi({
      "GET /fornecedores": { json: FORNECEDORES },
      "GET /produtos": { json: PRODUTOS },
      "POST /recebimento/pedidos": { status: 201, json: { id: 99 } },
    })
    const user = userEvent.setup()
    renderRotas(rotas, "/recebimento/novo")
    await escolherFornecedorEProduto(user)
    await user.type(screen.getByLabelText("Quantidade"), "10")
    await user.type(screen.getByLabelText(/Preço unit/), "10,5")
    await user.type(screen.getByLabelText(/Nº do pedido no fornecedor/), "PC-77")
    expect(await screen.findByText(/R\$\s*105,00/)).toBeInTheDocument() // total estimado
    await user.click(screen.getByRole("button", { name: /registrar pedido/i }))

    expect(await screen.findByText("detalhe do pedido")).toBeInTheDocument()
    expect(api.chamou("POST", "/recebimento/pedidos")[0]!.corpo).toEqual({
      fornecedor_id: 1,
      itens: [{ produto_id: 10, quantidade: 10, preco: "10.5" }],
      frete_previsto: "0",
      numero_externo: "PC-77",
    })
  })

  it("valida os campos antes de chamar a API", async () => {
    const api = mockApi({ "GET /fornecedores": { json: FORNECEDORES }, "GET /produtos": { json: PRODUTOS } })
    const user = userEvent.setup()
    renderRotas(rotas, "/recebimento/novo")
    await user.click(screen.getByRole("button", { name: /registrar pedido/i }))
    expect(await screen.findByText("Escolha o fornecedor")).toBeInTheDocument()
    expect(screen.getByText("Selecione o produto")).toBeInTheDocument()
    expect(api.chamou("POST", "/recebimento/pedidos")).toHaveLength(0)
  })

  it("recusa o mesmo produto em duas linhas", async () => {
    const api = mockApi({ "GET /fornecedores": { json: FORNECEDORES }, "GET /produtos": { json: PRODUTOS } })
    const user = userEvent.setup()
    renderRotas(rotas, "/recebimento/novo")
    await escolherFornecedorEProduto(user)
    await user.type(screen.getByLabelText("Quantidade"), "1")
    await user.type(screen.getByLabelText(/Preço unit/), "5")
    await user.click(screen.getByRole("button", { name: /adicionar item/i }))
    const combos = screen.getAllByRole("combobox", { name: /produto/i })
    await user.click(combos[1]!)
    const opcoes = await screen.findAllByText("Dipirona 500mg")
    await user.click(opcoes[opcoes.length - 1]!)
    const quantidades = screen.getAllByLabelText("Quantidade")
    await user.type(quantidades[1]!, "2")
    await user.type(screen.getAllByLabelText(/Preço unit/)[1]!, "5")
    await user.click(screen.getByRole("button", { name: /registrar pedido/i }))
    expect(await screen.findByText(/Produto repetido/)).toBeInTheDocument()
    expect(api.chamou("POST", "/recebimento/pedidos")).toHaveLength(0)
  })

  it("mostra no campo o erro devolvido pela API", async () => {
    mockApi({
      "GET /fornecedores": { json: FORNECEDORES },
      "GET /produtos": { json: PRODUTOS },
      "POST /recebimento/pedidos": { status: 404, json: { detail: { codigo: "fornecedor_nao_encontrado", mensagem: "Fornecedor não encontrado", campo: "fornecedor_id" } } },
    })
    const user = userEvent.setup()
    renderRotas(rotas, "/recebimento/novo")
    await escolherFornecedorEProduto(user)
    await user.type(screen.getByLabelText("Quantidade"), "1")
    await user.type(screen.getByLabelText(/Preço unit/), "5")
    await user.click(screen.getByRole("button", { name: /registrar pedido/i }))
    await waitFor(() => expect(screen.getByText("Fornecedor não encontrado")).toBeInTheDocument())
  })

  it("lista fornecedores sem CNPJ com aviso", async () => {
    mockApi({ "GET /fornecedores": { json: [{ ...FORNECEDORES[0], cnpj: null }] }, "GET /produtos": { json: PRODUTOS } })
    const user = userEvent.setup()
    renderRotas(rotas, "/recebimento/novo")
    await user.click(screen.getByRole("combobox", { name: /^fornecedor$/i }))
    const opcao = await screen.findByRole("option", { name: /Alfa Atacado/ })
    expect(within(opcao).getByText(/sem CNPJ/)).toBeInTheDocument()
  })
})
