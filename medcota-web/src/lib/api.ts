const BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "")

/** Erro padronizado da API: {"detail": {"codigo", "mensagem", ...}} (ou validação do FastAPI). */
export class ApiError extends Error {
  readonly status: number
  readonly codigo: string
  readonly extra: Record<string, unknown>

  constructor(status: number, codigo: string, mensagem: string, extra: Record<string, unknown> = {}) {
    super(mensagem)
    this.name = "ApiError"
    this.status = status
    this.codigo = codigo
    this.extra = extra
  }
}

type Hooks = {
  getToken: () => string | null
  onUnauthorized: () => void
}

let hooks: Hooks = { getToken: () => null, onUnauthorized: () => {} }

/** Liga o cliente HTTP à sessão (chamado uma vez pelo AuthProvider). */
export function configureApi(next: Hooks) {
  hooks = next
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
  body?: unknown
  form?: Record<string, string>
  /** Upload multipart: o navegador define o Content-Type (com o boundary). */
  formData?: FormData
  query?: Record<string, string | number | boolean | undefined>
  /** false para rotas públicas (login e link do fornecedor). */
  auth?: boolean
  signal?: AbortSignal
}

function parseErro(status: number, corpo: unknown): ApiError {
  const detail = (corpo as { detail?: unknown } | null)?.detail

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const { codigo, mensagem, ...extra } = detail as Record<string, unknown>
    return new ApiError(status, String(codigo ?? "erro"), String(mensagem ?? "Erro inesperado"), extra)
  }
  if (Array.isArray(detail)) {
    // validação do FastAPI/Pydantic: [{loc, msg}, ...]
    const msgs = detail.map((d: { loc?: unknown[]; msg?: string }) => {
      const campo = d.loc?.filter((p) => p !== "body" && p !== "query").join(".")
      return campo ? `${campo}: ${d.msg}` : (d.msg ?? "inválido")
    })
    return new ApiError(status, "validacao", `Dados inválidos — ${msgs.join("; ")}`)
  }
  if (typeof detail === "string") return new ApiError(status, "erro", detail)
  return new ApiError(status, "erro", `Erro ${status} ao falar com o servidor`)
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, form, formData, query, auth = true, signal } = opts

  const url = new URL(`${BASE_URL}${path}`)
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== "") url.searchParams.set(k, String(v))
  }

  const headers: Record<string, string> = { Accept: "application/json" }
  const token = auth ? hooks.getToken() : null
  if (token) headers.Authorization = `Bearer ${token}`

  let payload: BodyInit | undefined
  if (formData) {
    payload = formData
  } else if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    payload = new URLSearchParams(form)
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json"
    payload = JSON.stringify(body)
  }

  let res: Response
  try {
    res = await fetch(url, { method, headers, body: payload, signal })
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e
    throw new ApiError(0, "rede", "Não foi possível conectar à API. Verifique sua conexão.")
  }

  if (res.status === 204) return undefined as T

  const corpo: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const erro = parseErro(res.status, corpo)
    if (res.status === 401 && token) hooks.onUnauthorized() // sessão expirada/inválida
    throw erro
  }
  return corpo as T
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"], signal?: AbortSignal) =>
    request<T>(path, { query, signal }),
  post: <T>(path: string, body?: unknown, query?: RequestOptions["query"]) =>
    request<T>(path, { method: "POST", body, query }),
}

/** Mensagem amigável para qualquer erro capturado. */
export function mensagemDeErro(e: unknown): string {
  return e instanceof ApiError ? e.message : "Ocorreu um erro inesperado."
}

/** Baixa um arquivo protegido (precisa do Bearer, então não dá para usar um <a href>). */
export async function baixarArquivo(path: string): Promise<Blob> {
  const token = hooks.getToken()
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  } catch {
    throw new ApiError(0, "rede", "Não foi possível conectar à API. Verifique sua conexão.")
  }
  if (!res.ok) {
    if (res.status === 401 && token) hooks.onUnauthorized()
    throw parseErro(res.status, await res.json().catch(() => null))
  }
  return res.blob()
}
