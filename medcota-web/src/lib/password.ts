/** Política de senha (espelha a do backend): 8+ caracteres, com maiúscula, minúscula e número. */
export const SENHA_MIN = 8
export const SENHA_MAX_BYTES = 72 // limite do bcrypt

export interface Requisito {
  id: string
  texto: string
  ok: boolean
}

export function requisitosDaSenha(senha: string): Requisito[] {
  return [
    { id: "tamanho", texto: `Pelo menos ${SENHA_MIN} caracteres`, ok: [...senha].length >= SENHA_MIN },
    { id: "maiuscula", texto: "Uma letra maiúscula", ok: /\p{Lu}/u.test(senha) },
    { id: "minuscula", texto: "Uma letra minúscula", ok: /\p{Ll}/u.test(senha) },
    { id: "numero", texto: "Um número", ok: /[0-9]/.test(senha) },
  ]
}

/** Mensagem do primeiro requisito não atendido, ou null se a senha é válida. */
export function erroDaSenha(senha: string): string | null {
  if (new TextEncoder().encode(senha).length > SENHA_MAX_BYTES) return `A senha pode ter no máximo ${SENHA_MAX_BYTES} bytes`
  const falta = requisitosDaSenha(senha).find((r) => !r.ok)
  return falta ? `A senha precisa ter: ${falta.texto.toLowerCase()}` : null
}
