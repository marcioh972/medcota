import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, api, configureApi, request } from "./api"

const json = (status: number, corpo: unknown) =>
  Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }))

describe("cliente HTTP", () => {
  const fetchMock = vi.fn()
  const onUnauthorized = vi.fn()

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock)
    configureApi({ getToken: () => "tok123", onUnauthorized })
  })
  afterEach(() => {
    fetchMock.mockReset()
    onUnauthorized.mockReset()
    vi.unstubAllGlobals()
  })

  it("envia o token Bearer e a query string", async () => {
    fetchMock.mockReturnValue(json(200, [{ id: 1 }]))
    await api.get("/produtos", { q: "dipi", limit: 20, vazio: undefined })
    const [url, init] = fetchMock.mock.calls[0]!
    expect(String(url)).toContain("/produtos?q=dipi&limit=20")
    expect(String(url)).not.toContain("vazio")
    expect(init.headers.Authorization).toBe("Bearer tok123")
  })

  it("não envia token em rotas públicas", async () => {
    fetchMock.mockReturnValue(json(200, {}))
    await request("/c/abc", { auth: false })
    expect(fetchMock.mock.calls[0]![1].headers.Authorization).toBeUndefined()
  })

  it("converte o erro de negócio da API em ApiError", async () => {
    fetchMock.mockReturnValue(
      json(409, { detail: { codigo: "duplicata", mensagem: "Já lançado.", somar_quantidade: true } }),
    )
    const erro = await api.post("/faltas", {}).catch((e: unknown) => e)
    expect(erro).toBeInstanceOf(ApiError)
    expect(erro).toMatchObject({ status: 409, codigo: "duplicata", message: "Já lançado.", extra: { somar_quantidade: true } })
  })

  it("resume erros de validação do FastAPI", async () => {
    fetchMock.mockReturnValue(
      json(422, { detail: [{ loc: ["body", "quantidade"], msg: "deve ser maior que 0" }] }),
    )
    const erro = (await api.post("/faltas", {}).catch((e: unknown) => e)) as ApiError
    expect(erro.codigo).toBe("validacao")
    expect(erro.message).toContain("quantidade: deve ser maior que 0")
  })

  it("204 devolve undefined", async () => {
    fetchMock.mockReturnValue(Promise.resolve(new Response(null, { status: 204 })))
    await expect(request("/c/x/abertura", { method: "POST", auth: false })).resolves.toBeUndefined()
  })

  it("401 com token dispara onUnauthorized", async () => {
    fetchMock.mockReturnValue(json(401, { detail: { codigo: "token_invalido", mensagem: "Token inválido" } }))
    await expect(api.get("/faltas/hoje")).rejects.toBeInstanceOf(ApiError)
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it("401 em rota pública (login) não derruba a sessão", async () => {
    fetchMock.mockReturnValue(json(401, { detail: { codigo: "credenciais_invalidas", mensagem: "Credenciais inválidas" } }))
    await expect(request("/auth/login", { method: "POST", auth: false })).rejects.toBeInstanceOf(ApiError)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it("falha de rede vira ApiError amigável", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"))
    const erro = (await api.get("/x").catch((e: unknown) => e)) as ApiError
    expect(erro).toMatchObject({ status: 0, codigo: "rede" })
  })
})

describe("upload e download", () => {
  const fetchMock = vi.fn()
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock)
    configureApi({ getToken: () => "tok123", onUnauthorized: vi.fn() })
  })
  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it("multipart: envia o FormData sem definir Content-Type", async () => {
    fetchMock.mockReturnValue(json(201, { id: 1 }))
    const fd = new FormData()
    fd.append("arquivo", new File(["<x/>"], "n.xml"))
    await request("/recebimento/pedidos/1/nfe", { method: "POST", formData: fd })
    const [, init] = fetchMock.mock.calls[0]!
    expect(init.body).toBe(fd)
    expect(init.headers["Content-Type"]).toBeUndefined()
    expect(init.headers.Authorization).toBe("Bearer tok123")
  })

  it("baixarArquivo envia o token e devolve o Blob", async () => {
    const { baixarArquivo } = await import("./api")
    fetchMock.mockReturnValue(Promise.resolve(new Response("<xml/>", { status: 200 })))
    const blob = await baixarArquivo("/recebimento/nfes/1/xml")
    expect(await blob.text()).toBe("<xml/>")
    expect(fetchMock.mock.calls[0]![1].headers.Authorization).toBe("Bearer tok123")
  })

  it("baixarArquivo converte o erro da API", async () => {
    const { baixarArquivo } = await import("./api")
    fetchMock.mockReturnValue(json(404, { detail: { codigo: "nfe_nao_encontrada", mensagem: "Nota fiscal não encontrada" } }))
    await expect(baixarArquivo("/recebimento/nfes/9/xml")).rejects.toMatchObject({ status: 404, codigo: "nfe_nao_encontrada" })
  })
})
