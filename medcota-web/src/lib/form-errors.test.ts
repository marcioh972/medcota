import { act, renderHook } from "@testing-library/react"
import { useForm } from "react-hook-form"
import { describe, expect, it } from "vitest"

import { ApiError } from "./api"
import { aplicarErroDaApi } from "./form-errors"

const CAMPOS = ["email", "senha"] as const

function setup() {
  const { result } = renderHook(() => {
    const form = useForm<{ email: string; senha: string }>()
    void form.formState.errors // assina o formState para o hook re-renderizar quando houver erro
    return form
  })
  return result
}

describe("aplicarErroDaApi", () => {
  it("mapeia erros de validação por campo", () => {
    const form = setup()
    act(() =>
      aplicarErroDaApi(
        form.current,
        new ApiError(422, "validacao", "Dados inválidos", { campos: { senha: "fraca", outro: "x" } }),
        CAMPOS,
      ),
    )
    expect(form.current.formState.errors.senha?.message).toBe("fraca")
    expect(form.current.formState.errors.root).toBeUndefined()
  })

  it("mapeia erro de negócio que aponta um campo (ex.: e-mail em uso)", () => {
    const form = setup()
    act(() =>
      aplicarErroDaApi(
        form.current,
        new ApiError(409, "email_em_uso", "Este e-mail já está cadastrado.", { campo: "email" }),
        CAMPOS,
      ),
    )
    expect(form.current.formState.errors.email?.message).toBe("Este e-mail já está cadastrado.")
  })

  it("sem campo conhecido vira erro geral", () => {
    const form = setup()
    act(() => aplicarErroDaApi(form.current, new ApiError(429, "limite_requisicoes", "Muitas requisições."), CAMPOS))
    expect(form.current.formState.errors.root?.message).toBe("Muitas requisições.")
  })

  it("erro desconhecido vira mensagem genérica", () => {
    const form = setup()
    act(() => aplicarErroDaApi(form.current, new Error("boom"), CAMPOS))
    expect(form.current.formState.errors.root?.message).toBe("Ocorreu um erro inesperado.")
  })
})
