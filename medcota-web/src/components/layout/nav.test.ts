import { describe, expect, it } from "vitest"

import { navDoPerfil } from "./nav"

const rotas = (p: Parameters<typeof navDoPerfil>[0]) => navDoPerfil(p).map((i) => i.to)

describe("navegação por perfil", () => {
  it("vendedor não tem acesso ao módulo de recebimento nem ao catálogo", () => {
    expect(rotas("vendedor")).toEqual(["/faltas"])
  })

  it("comprador vê o recebimento, mas não a equipe", () => {
    expect(rotas("comprador")).toContain("/recebimento")
    expect(rotas("comprador")).not.toContain("/equipe")
  })

  it("gestor vê o recebimento e a equipe", () => {
    expect(rotas("gestor")).toEqual(expect.arrayContaining(["/recebimento", "/equipe"]))
  })
})
