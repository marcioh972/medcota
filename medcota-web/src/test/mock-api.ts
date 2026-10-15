import { vi } from "vitest"

export interface Chamada {
  metodo: string
  caminho: string
  query: URLSearchParams
  corpo: unknown
  headers: Record<string, string>
}

type Resposta = { status?: number; json?: unknown } | undefined
type Rota = Resposta | ((c: Chamada) => Resposta)

/** Simula o backend por rota ("GET /caminho"). Rotas não mapeadas respondem 404. */
export function mockApi(rotas: Record<string, Rota>) {
  const chamadas: Chamada[] = []
  const fetchMock = vi.fn((url: URL | string, init: RequestInit = {}) => {
    const u = new URL(String(url))
    const metodo = (init.method ?? "GET").toUpperCase()
    const corpo =
      typeof init.body === "string" ? (JSON.parse(init.body) as unknown) : (init.body as FormData | URLSearchParams | undefined)
    const chamada: Chamada = { metodo, caminho: u.pathname, query: u.searchParams, corpo, headers: (init.headers ?? {}) as Record<string, string> }
    chamadas.push(chamada)
    const rota = rotas[`${metodo} ${u.pathname}`]
    const r = typeof rota === "function" ? rota(chamada) : rota
    if (r === undefined) {
      return Promise.resolve(
        new Response(JSON.stringify({ detail: { codigo: "nao_mapeada", mensagem: `Sem mock para ${metodo} ${u.pathname}` } }), { status: 404 }),
      )
    }
    const status = r.status ?? 200
    return Promise.resolve(new Response(status === 204 ? null : JSON.stringify(r.json ?? null), { status, headers: { "Content-Type": "application/json" } }))
  })
  vi.stubGlobal("fetch", fetchMock)
  return { fetchMock, chamadas, chamou: (metodo: string, caminho: string) => chamadas.filter((c) => c.metodo === metodo && c.caminho === caminho) }
}

/** O Select (Radix) e o cmdk usam APIs que o jsdom não implementa. */
export function polyfillsDeDom() {
  Element.prototype.hasPointerCapture = () => false
  Element.prototype.scrollIntoView = () => {}
  window.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}
