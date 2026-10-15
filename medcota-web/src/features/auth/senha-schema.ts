import { z } from "zod"

import { erroDaSenha } from "@/lib/password"

/** Campo de senha validado pela política (8+, maiúscula, minúscula, número). Não faz trim. */
export const senhaSchema = z.string().superRefine((s, ctx) => {
  const erro = erroDaSenha(s)
  if (erro) ctx.addIssue({ code: z.ZodIssueCode.custom, message: erro })
})
