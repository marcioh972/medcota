import { isRouteErrorResponse, Link, useRouteError } from "react-router"

import { Button } from "@/components/ui/button"

export function RouteError() {
  const error = useRouteError()
  const mensagem = isRouteErrorResponse(error)
    ? `${error.status} — ${error.statusText}`
    : "Algo deu errado ao abrir esta página."

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Ops!</h1>
      <p className="text-muted-foreground">{mensagem}</p>
      <Button asChild>
        <Link to="/">Voltar ao início</Link>
      </Button>
    </div>
  )
}
