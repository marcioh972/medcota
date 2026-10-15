import { render, screen, within } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import type { Apontamento } from "@/lib/types"

import { ApontamentosLista } from "./apontamentos-lista"

const ap = (p: Partial<Apontamento>): Apontamento => ({
  severidade: "erro",
  codigo: "X",
  mensagem: "mensagem",
  item_numero: null,
  campo: null,
  esperado: null,
  encontrado: null,
  base_legal: null,
  ...p,
})

describe("ApontamentosLista", () => {
  it("separa erros, alertas e informações, mostrando esperado × encontrado e a base normativa", () => {
    render(
      <ApontamentosLista
        apontamentos={[
          ap({ codigo: "FRETE_INDEVIDO", mensagem: "Fornecedor de Maceió/AL não cobra frete.", esperado: "0,00", encontrado: "50.00", campo: "total/vFrete", base_legal: "Regra da empresa" }),
          ap({ severidade: "alerta", codigo: "ENTREGA_PARCIAL", mensagem: "6 de 10 un.", item_numero: 2 }),
          ap({ severidade: "info", codigo: "SEFAZ_NAO_CONSULTADA", mensagem: "Situação não consultada na SEFAZ." }),
        ]}
      />,
    )
    const erros = screen.getByRole("region", { name: "Erros" })
    expect(within(erros).getByText(/não cobra frete/)).toBeInTheDocument()
    expect(erros).toHaveTextContent("esperado: 0,00")
    expect(erros).toHaveTextContent("encontrado: 50.00")
    expect(erros).toHaveTextContent("Base: Regra da empresa")
    expect(within(screen.getByRole("region", { name: "Alertas" })).getByText(/6 de 10/)).toBeInTheDocument()
    expect(screen.getByText(/Informações e limites da conferência \(1\)/)).toBeInTheDocument()
  })

  it("sem erro nem alerta, informa que tudo confere", () => {
    render(<ApontamentosLista apontamentos={[ap({ severidade: "info", mensagem: "só informação" })]} />)
    expect(screen.getByText(/preços, quantidades, frete, impostos e totais conferem/)).toBeInTheDocument()
  })

  it("lista vazia", () => {
    render(<ApontamentosLista apontamentos={[]} />)
    expect(screen.getByText("Nenhum apontamento.")).toBeInTheDocument()
  })
})
