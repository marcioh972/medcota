import { describe, expect, it } from "vitest"

import { cnpjValido, formatarCnpj, normalizarCnpj } from "./cnpj"

describe("cnpj", () => {
  it.each(["11.222.333/0001-81", "11222333000181", "12.ABC.345/01DE-35", "12abc34501de35", "00.000.000/E08G-12"])(
    "aceita %s",
    (c) => expect(cnpjValido(c)).toBe(true),
  )

  it.each(["11222333000182", "00000000000000", "11111111111111", "1122233300018", "12ABC34501DE3A", "", "abc"])(
    "rejeita '%s'",
    (c) => expect(cnpjValido(c)).toBe(false),
  )

  it("normaliza e formata", () => {
    expect(normalizarCnpj(" 12.abc.345/01de-35 ")).toBe("12ABC34501DE35")
    expect(formatarCnpj("12ABC34501DE35")).toBe("12.ABC.345/01DE-35")
    expect(formatarCnpj("123")).toBe("123")
  })
})
