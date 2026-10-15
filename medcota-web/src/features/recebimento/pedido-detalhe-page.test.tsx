import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { salvarSessao } from "@/features/auth/session"
import type { NFeDetalhe, PedidoRecebimento } from "@/lib/types"
import { mockApi, polyfillsDeDom } from "@/test/mock-api"
import { renderRotas } from "@/test/render"

import { Component as PedidoDetalhe } from "./pedido-detalhe-page"

const PEDIDO: PedidoRecebimento = {
  id: 7,
  criado_em: "2026-10-05T12:00:00",
  origem: "manual",
  status: "aprovado",
  recebimento: "aguardando_nfe",
  total: "100.00",
  frete_previsto: "0.00",
  numero_externo: "PC-1",
  observacao: "",
  fornecedores: [{ id: 1, nome: "Alfa Atacado", cnpj: "12ABC34501DE35", credenciado_72101: true }],
  itens: [{ produto_id: 1, produto: "Dipirona 500mg", ean: "7896094916010", fornecedor_id: 1, quantidade: 10, preco: "10.0000" }],
  nfes: [],
}

const NFE: NFeDetalhe = {
  id: 55,
  pedido_id: 7,
  chave_acesso: "27261012ABC34501DE35550010000012341000000019",
  numero: "1234",
  serie: "1",
  emitente_nome: "Alfa Atacado",
  emitente_cnpj: "12ABC34501DE35",
  data_emissao: "2026-10-05T13:00:00",
  valor_total: "150.00",
  valor_frete: "50.00",
  resultado: "reprovada",
  decisao: "pendente",
  importada_em: "2026-10-05T13:05:00",
  erros: 1,
  alertas: 0,
  infos: 1,
  fornecedor_id: 1,
  protocolo_status: "100",
  justificativa: "",
  decisao_em: null,
  versao_regras: "2026.10.1",
  apontamentos: [
    { severidade: "erro", codigo: "FRETE_INDEVIDO", mensagem: "Fornecedor de Maceió/AL não cobra frete na nota, mas a nota traz frete de R$ 50,00.", item_numero: null, campo: "total/vFrete", esperado: "0,00", encontrado: "50.00", base_legal: "Regra da empresa" },
    { severidade: "info", codigo: "SEFAZ_NAO_CONSULTADA", mensagem: "A situação atual da nota não foi consultada na SEFAZ.", item_numero: null, campo: null, esperado: null, encontrado: null, base_legal: null },
  ],
}

const rota = [{ path: "/recebimento/:pedidoId", element: <PedidoDetalhe /> }]

describe("Detalhe do pedido (recebimento)", () => {
  beforeEach(() => polyfillsDeDom())
  afterEach(() => vi.unstubAllGlobals())

  it("sem nota, mostra o resumo e o envio do XML (fornecedor sem CNPJ é sinalizado)", async () => {
    salvarSessao({ token: "t", nome: "Bruno", perfil: "comprador", empresa: "Empresa A" })
    mockApi({ "GET /recebimento/pedidos/7": { json: { ...PEDIDO, fornecedores: [{ ...PEDIDO.fornecedores[0]!, cnpj: null, credenciado_72101: false }] } } })
    renderRotas(rota, "/recebimento/7")
    expect(await screen.findByText("Pedido #7")).toBeInTheDocument()
    expect(screen.getByText("Dipirona 500mg")).toBeInTheDocument()
    expect(screen.getByText(/sem CNPJ cadastrado/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Arquivo XML/)).toBeInTheDocument()
  })

  it("envia o XML como multipart (sem Content-Type manual) e mostra o resultado da conferência", async () => {
    salvarSessao({ token: "t", nome: "Bruno", perfil: "comprador", empresa: "Empresa A" })
    let enviada = false
    const api = mockApi({
      "GET /recebimento/pedidos/7": () => ({ json: { ...PEDIDO, nfes: enviada ? [NFE] : [] } }),
      "POST /recebimento/pedidos/7/nfe": () => {
        enviada = true
        return { status: 201, json: NFE }
      },
      "GET /recebimento/nfes/55": { json: NFE },
    })
    const user = userEvent.setup()
    renderRotas(rota, "/recebimento/7")

    const arquivo = new File(["<nfeProc/>"], "nota.xml", { type: "text/xml" })
    await user.upload(await screen.findByLabelText(/Arquivo XML/), arquivo)
    await user.click(screen.getByRole("button", { name: /enviar e conferir/i }))

    expect(await screen.findByText(/não cobra frete na nota/)).toBeInTheDocument()
    expect(screen.getByText("Com erros")).toBeInTheDocument()
    const [envio] = api.chamou("POST", "/recebimento/pedidos/7/nfe")
    expect(envio!.corpo).toBeInstanceOf(FormData)
    expect((envio!.corpo as FormData).get("arquivo")).toBeInstanceOf(File)
    expect(envio!.headers["Content-Type"]).toBeUndefined() // o navegador define o boundary
    expect(envio!.headers.Authorization).toBe("Bearer t")
  })

  it("mostra o motivo quando o XML é recusado pelo servidor", async () => {
    salvarSessao({ token: "t", nome: "Bruno", perfil: "comprador", empresa: "Empresa A" })
    mockApi({
      "GET /recebimento/pedidos/7": { json: PEDIDO },
      "POST /recebimento/pedidos/7/nfe": { status: 409, json: { detail: { codigo: "nfe_duplicada", mensagem: "Esta nota fiscal já foi enviada.", nfe_id: 3 } } },
    })
    const user = userEvent.setup()
    renderRotas(rota, "/recebimento/7")
    await user.upload(await screen.findByLabelText(/Arquivo XML/), new File(["<x/>"], "n.xml", { type: "text/xml" }))
    await user.click(screen.getByRole("button", { name: /enviar e conferir/i }))
    const alerta = await screen.findByRole("alert")
    expect(alerta).toHaveTextContent("Nota já enviada")
    expect(alerta).toHaveTextContent("Esta nota fiscal já foi enviada.")
  })

  it("pedido aguardando aprovação não aceita nota", async () => {
    salvarSessao({ token: "t", nome: "Bruno", perfil: "comprador", empresa: "Empresa A" })
    mockApi({ "GET /recebimento/pedidos/7": { json: { ...PEDIDO, status: "aguardando_aprovacao" } } })
    renderRotas(rota, "/recebimento/7")
    expect(await screen.findByText(/aguarda a aprovação do gestor/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/Arquivo XML/)).not.toBeInTheDocument()
  })

  describe("decisão sobre nota com erros", () => {
    const montar = (perfil: "comprador" | "gestor") => {
      salvarSessao({ token: "t", nome: "Fulano", perfil, empresa: "Empresa A" })
      const api = mockApi({
        "GET /recebimento/pedidos/7": { json: { ...PEDIDO, recebimento: "em_conferencia", nfes: [NFE] } },
        "GET /recebimento/nfes/55": { json: NFE },
        "POST /recebimento/nfes/55/decisao": (c) => ({ json: { ...NFE, decisao: (c.corpo as { decisao: string }).decisao } }),
      })
      renderRotas(rota, "/recebimento/7")
      return api
    }

    it("o comprador não pode aceitar, só recusar", async () => {
      montar("comprador")
      expect(await screen.findByRole("button", { name: /aceitar nota/i })).toBeDisabled()
      expect(screen.getByText(/apenas o gestor pode aceitá-la/i)).toBeInTheDocument()
      expect(screen.getByRole("button", { name: /recusar nota/i })).toBeEnabled()
    })

    it("o gestor só confirma o aceite depois de justificar (mín. 10 caracteres)", async () => {
      const api = montar("gestor")
      const user = userEvent.setup()
      await user.click(await screen.findByRole("button", { name: /aceitar nota/i }))
      const dialogo = await screen.findByRole("alertdialog")
      const confirmar = within(dialogo).getByRole("button", { name: /aceitar nota/i })
      expect(confirmar).toBeDisabled()
      await user.type(within(dialogo).getByLabelText(/justificativa/i), "curto")
      expect(confirmar).toBeDisabled()
      await user.type(within(dialogo).getByLabelText(/justificativa/i), " — reajuste autorizado")
      expect(confirmar).toBeEnabled()
      await user.click(confirmar)
      await waitFor(() => expect(api.chamou("POST", "/recebimento/nfes/55/decisao")).toHaveLength(1))
      expect(api.chamou("POST", "/recebimento/nfes/55/decisao")[0]!.corpo).toEqual({
        decisao: "aceita",
        justificativa: "curto — reajuste autorizado",
      })
    })

    it("recusar exige o motivo", async () => {
      montar("comprador")
      const user = userEvent.setup()
      await user.click(await screen.findByRole("button", { name: /recusar nota/i }))
      const dialogo = await screen.findByRole("alertdialog")
      expect(within(dialogo).getByRole("button", { name: /recusar nota/i })).toBeDisabled()
    })
  })
})
