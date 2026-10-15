import { describe, expect, it } from "vitest"

import { dataHora, moeda, numeroBR, parseUtc } from "./format"

describe("moeda", () => {
  it("formata Decimal em string como BRL", () => {
    expect(moeda("138.58").replace(/\s/g, " ")).toBe("R$ 138,58")
  })
  it("null (sem permissão) vira traço", () => {
    expect(moeda(null)).toBe("—")
    expect(moeda(undefined)).toBe("—")
  })
  it("valor inválido vira traço", () => {
    expect(moeda("abc")).toBe("—")
  })
})

describe("parseUtc", () => {
  it("trata data sem fuso como UTC", () => {
    expect(parseUtc("2026-10-02T13:00:00").toISOString()).toBe("2026-10-02T13:00:00.000Z")
  })
  it("respeita fuso explícito", () => {
    expect(parseUtc("2026-10-02T13:00:00Z").toISOString()).toBe("2026-10-02T13:00:00.000Z")
    expect(parseUtc("2026-10-02T10:00:00-03:00").toISOString()).toBe("2026-10-02T13:00:00.000Z")
  })
  it("dataHora devolve texto em pt-BR", () => {
    expect(dataHora("2026-10-02T13:00:00")).toMatch(/\d{2}\/\d{2}\/\d{2,4}/)
  })
})

describe("numeroBR", () => {
  it("aceita vírgula e ponto", () => {
    expect(numeroBR("12,5")).toBe(12.5)
    expect(numeroBR(" 12.5 ")).toBe(12.5)
    expect(numeroBR("x")).toBeNaN()
  })
})
