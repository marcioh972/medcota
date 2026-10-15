const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" })

/** Formata um Decimal vindo da API (string). `null` = sem permissão (RN-04). */
export function moeda(valor: string | null | undefined): string {
  if (valor === null || valor === undefined) return "—"
  const n = Number(valor) // apenas exibição; nenhum cálculo financeiro no front
  return Number.isFinite(n) ? brl.format(n) : "—"
}

/** A API devolve datas UTC sem fuso ("2026-10-02T13:00:00"); sem o "Z" o JS leria como local. */
export function parseUtc(iso: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`)
}

export function dataHora(iso: string): string {
  return parseUtc(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
}

/** Aceita "12,5" ou "12.5" e devolve o número, ou NaN. */
export function numeroBR(texto: string): number {
  return Number(texto.trim().replace(",", "."))
}
