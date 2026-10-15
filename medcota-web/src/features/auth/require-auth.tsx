import { Navigate, Outlet, useLocation } from "react-router"

import type { Perfil } from "@/lib/types"

import { homeDoPerfil } from "./session"
import { useAuth } from "./use-auth"

/** Protege um grupo de rotas: exige login e, opcionalmente, um dos perfis informados. */
export function RequireAuth({ roles }: { roles?: Perfil[] }) {
  const { session } = useAuth()
  const location = useLocation()

  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(session.perfil)) {
    return <Navigate to={homeDoPerfil(session.perfil)} replace />
  }
  return <Outlet />
}
