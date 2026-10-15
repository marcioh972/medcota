import { useQueryClient } from "@tanstack/react-query"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"

import { configureApi, request } from "@/lib/api"
import type { LoginOut } from "@/lib/types"

import { AuthContext } from "./auth-context"
import { lerSessao, salvarSessao, type Session } from "./session"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSession] = useState<Session | null>(lerSessao)
  const tokenRef = useRef(session?.token ?? null)

  const logout = useCallback(() => {
    tokenRef.current = null
    salvarSessao(null)
    setSession(null)
    queryClient.clear() // nada da sessão anterior pode vazar para o próximo usuário
  }, [queryClient])

  useEffect(() => {
    configureApi({
      getToken: () => tokenRef.current,
      onUnauthorized: () => {
        logout()
        toast.error("Sua sessão expirou. Entre novamente.")
      },
    })
  }, [logout])

  const iniciarSessao = useCallback((r: LoginOut) => {
    const nova: Session = { token: r.access_token, nome: r.nome, perfil: r.perfil, empresa: r.empresa }
    tokenRef.current = nova.token
    salvarSessao(nova)
    setSession(nova)
    return nova
  }, [])

  const login = useCallback(
    async (email: string, senha: string) => {
      const r = await request<LoginOut>("/auth/login", {
        method: "POST",
        form: { username: email, password: senha },
        auth: false,
      })
      return iniciarSessao(r)
    },
    [iniciarSessao],
  )

  const value = useMemo(() => ({ session, login, iniciarSessao, logout }), [session, login, iniciarSessao, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
