/** CNPJ numérico e alfanumérico (formato vigente desde jul/2026). Espelha a validação do backend. */
const PESOS_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
const PESOS_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

/** Remove máscara/espaços e põe em maiúsculas. */
export function normalizarCnpj(valor: string): string {
  return valor.replace(/[.\-/\s]/g, "").toUpperCase()
}

function digito(base: string, pesos: number[]): number {
  const soma = [...base].reduce((acc, c, i) => acc + (c.charCodeAt(0) - 48) * pesos[i]!, 0)
  const resto = soma % 11
  return resto < 2 ? 0 : 11 - resto
}

export function cnpjValido(valor: string): boolean {
  const n = normalizarCnpj(valor)
  if (!/^[0-9A-Z]{12}[0-9]{2}$/.test(n) || new Set(n).size === 1) return false
  const dv1 = digito(n.slice(0, 12), PESOS_1)
  const dv2 = digito(n.slice(0, 12) + dv1, PESOS_2)
  return n.slice(12) === `${dv1}${dv2}`
}

/** Máscara de exibição: 12.ABC.345/01DE-35 */
export function formatarCnpj(valor: string): string {
  const n = normalizarCnpj(valor)
  if (n.length !== 14) return valor
  return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12)}`
}
