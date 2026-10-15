import { describe, expect, it } from "vitest"

import { erroDaSenha, requisitosDaSenha } from "./password"

describe("política de senha", () => {
  it.each(["Abcdef1x", "Senha-teste-123", "ÁguaClara9"])("aceita %s", (s) => {
    expect(erroDaSenha(s)).toBeNull()
  })

  it.each([
    ["Ab1", "pelo menos 8 caracteres"],
    ["abcdefg1", "uma letra maiúscula"],
    ["ABCDEFG1", "uma letra minúscula"],
    ["Abcdefgh", "um número"],
  ])("rejeita %s e diz o que falta", (senha, falta) => {
    expect(erroDaSenha(senha)).toContain(falta)
  })

  it("rejeita senha acima do limite do bcrypt (72 bytes)", () => {
    expect(erroDaSenha("A1" + "b".repeat(80))).toContain("72 bytes")
  })

  it("marca cada requisito individualmente (checklist ao vivo)", () => {
    const r = Object.fromEntries(requisitosDaSenha("abc").map((q) => [q.id, q.ok]))
    expect(r).toEqual({ tamanho: false, maiuscula: false, minuscula: true, numero: false })
  })
})
