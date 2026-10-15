import type { Perfil } from "@/lib/types"

export interface Session {
  token: string
  nome: string
  perfil: Perfil
  empresa: string
}

// sessionStorage: some ao fechar a aba (menor janela de exposição do token que o localStorage).
const KEY = "medcota.session"

export function lerSessao(): Session | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    const s = JSON.parse(raw) as Partial<Session>
    return s.token && s.nome && s.perfil && s.empresa ? (s as Session) : null
  } catch {
    return null
  }
}

export function salvarSessao(s: Session | null) {
  try {
    if (s) sessionStorage.setItem(KEY, JSON.stringify(s))
    else sessionStorage.removeItem(KEY)
  } catch {
    /* storage indisponível */
  }
}

/** Primeira tela de cada perfil. */
export function homeDoPerfil(perfil: Perfil): string {
  return perfil === "vendedor" ? "/faltas" : "/dashboard"
}
