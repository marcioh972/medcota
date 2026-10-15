import type { FieldValues, Path, UseFormReturn } from "react-hook-form"

import { ApiError, mensagemDeErro } from "@/lib/api"

/**
 * Leva um erro da API para o formulário:
 * - 422 {codigo:"validacao", campos:{campo: msg}} -> erro em cada campo conhecido;
 * - 409/422 de negócio com `campo` (ex.: cnpj_em_uso, codigo_invalido) -> erro naquele campo;
 * - qualquer outro -> erro geral (`root`).
 */
export function aplicarErroDaApi<T extends FieldValues>(form: UseFormReturn<T>, erro: unknown, campos: readonly string[]) {
  if (!(erro instanceof ApiError)) {
    form.setError("root", { message: mensagemDeErro(erro) })
    return
  }
  let achou = false
  const porCampo = (erro.extra.campos ?? {}) as Record<string, string>
  for (const [campo, msg] of Object.entries(porCampo)) {
    if (campos.includes(campo)) {
      form.setError(campo as Path<T>, { message: msg })
      achou = true
    }
  }
  const campo = erro.extra.campo
  if (typeof campo === "string" && campos.includes(campo)) {
    form.setError(campo as Path<T>, { message: erro.message })
    achou = true
  }
  if (!achou) form.setError("root", { message: erro.message })
}
