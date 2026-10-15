import { createContext } from "react"

import type { LoginOut } from "@/lib/types"

import type { Session } from "./session"

export interface AuthContextValue {
  session: Session | null
  login: (email: string, senha: string) => Promise<Session>
  /** Cadastro de empresa/funcionário já devolve a sessão (login automático). */
  iniciarSessao: (r: LoginOut) => Session
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
