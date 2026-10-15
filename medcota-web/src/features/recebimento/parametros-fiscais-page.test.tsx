import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { salvarSessao } from "@/features/auth/session"
import { mockApi, polyfillsDeDom } from "@/test/mock-api"
import { renderRotas } from "@/test/render"

import { Component as Parametros } from "./parametros-fiscais-page"

const CONFIG = { aliquota_interna_icms: null, tolerancia_preco_pct: "0.00", frete_zero_municipios: ["2704302"], exigir_protocolo: true, atualizada_em: null }
const rotas = [{ path: "/recebimento/parametros", element: <Parametros /> }]

describe("Parâmetros fiscais", () => {
  beforeEach(() => polyfillsDeDom())
  afterEach(() => vi.unstubAllGlobals())

  it("o gestor salva a alíquota e os municípios (vírgula decimal e lista normalizadas)", async () => {
    salvarSessao({ token: "t", nome: "Carla", perfil: "gestor", empresa: "Empresa A" })
    const api = mockApi({
      "GET /fiscal/configuracao": { json: CONFIG },
      "PUT /fiscal/configuracao": (c) => ({ json: { ...(c.corpo as object), atualizada_em: "2026-10-06T10:00:00" } }),
    })
    const user = userEvent.setup()
    renderRotas(rotas, "/recebimento/parametros")

    const aliquota = await screen.findByLabelText(/Alíquota interna/)
    await user.type(aliquota, "19,5")
    const municipios = screen.getByLabelText(/Códigos IBGE/)
    await user.clear(municipios)
    await user.type(municipios, "2704302; 2611606")
    await user.click(screen.getByRole("button", { name: /salvar parâmetros/i }))

    await vi.waitFor(() => expect(api.chamou("PUT", "/fiscal/configuracao")).toHaveLength(1))
    expect(api.chamou("PUT", "/fiscal/configuracao")[0]!.corpo).toEqual({
      aliquota_interna_icms: "19.5",
      tolerancia_preco_pct: "0.00",
      frete_zero_municipios: ["2704302", "2611606"],
      exigir_protocolo: true,
    })
  })

  it("valida código IBGE e percentuais antes de enviar", async () => {
    salvarSessao({ token: "t", nome: "Carla", perfil: "gestor", empresa: "Empresa A" })
    const api = mockApi({ "GET /fiscal/configuracao": { json: CONFIG } })
    const user = userEvent.setup()
    renderRotas(rotas, "/recebimento/parametros")
    await user.type(await screen.findByLabelText(/Alíquota interna/), "150")
    const municipios = screen.getByLabelText(/Códigos IBGE/)
    await user.clear(municipios)
    await user.type(municipios, "123")
    await user.click(screen.getByRole("button", { name: /salvar parâmetros/i }))
    expect(await screen.findByText("Entre 0 e 100")).toBeInTheDocument()
    expect(screen.getByText("Cada código IBGE tem 7 dígitos")).toBeInTheDocument()
    expect(api.chamou("PUT", "/fiscal/configuracao")).toHaveLength(0)
  })

  it("o comprador vê os valores, mas não pode alterá-los", async () => {
    salvarSessao({ token: "t", nome: "Bruno", perfil: "comprador", empresa: "Empresa A" })
    mockApi({ "GET /fiscal/configuracao": { json: { ...CONFIG, aliquota_interna_icms: "19.00" } } })
    renderRotas(rotas, "/recebimento/parametros")
    const aliquota = await screen.findByLabelText(/Alíquota interna/)
    expect(aliquota).toBeDisabled()
    expect(aliquota).toHaveValue("19.00")
    expect(screen.queryByRole("button", { name: /salvar parâmetros/i })).not.toBeInTheDocument()
    expect(screen.getByText(/Somente o gestor pode alterar/)).toBeInTheDocument()
  })

  it("explica o alcance do Decreto 72.101/2020", async () => {
    salvarSessao({ token: "t", nome: "Carla", perfil: "gestor", empresa: "Empresa A" })
    mockApi({ "GET /fiscal/configuracao": { json: CONFIG } })
    renderRotas(rotas, "/recebimento/parametros")
    expect(await screen.findByText(/Decreto nº 72.101\/2020/)).toBeInTheDocument()
    expect(screen.getByText(/apurado mensalmente pelo fornecedor/)).toBeInTheDocument()
  })
})
