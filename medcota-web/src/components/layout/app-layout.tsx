import { MenuIcon } from "lucide-react"
import { useState } from "react"
import { NavLink, Outlet } from "react-router"

import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { useAuth } from "@/features/auth/use-auth"
import { cn } from "@/lib/utils"

import { navDoPerfil } from "./nav"
import { UserMenu } from "./user-menu"

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
    isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground",
  )

export function AppLayout() {
  const { session } = useAuth()
  const [menuAberto, setMenuAberto] = useState(false)
  const itens = session ? navDoPerfil(session.perfil) : []

  return (
    <div className="min-h-svh">
      <a
        href="#conteudo"
        className="sr-only z-50 rounded-md bg-background px-3 py-2 focus:not-sr-only focus:absolute focus:left-4 focus:top-4"
      >
        Pular para o conteúdo
      </a>

      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          <Sheet open={menuAberto} onOpenChange={setMenuAberto}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden" aria-label="Abrir menu">
                <MenuIcon />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64">
              <SheetHeader>
                <SheetTitle>MedCota</SheetTitle>
                <SheetDescription className="sr-only">Navegação principal</SheetDescription>
              </SheetHeader>
              <nav className="flex flex-col gap-1 px-4" aria-label="Principal">
                {itens.map(({ to, label, icon: Icon }) => (
                  <NavLink key={to} to={to} className={linkClass} onClick={() => setMenuAberto(false)}>
                    <Icon className="size-4" /> {label}
                  </NavLink>
                ))}
              </nav>
            </SheetContent>
          </Sheet>

          <span className="text-base font-semibold tracking-tight">MedCota</span>
          {session && (
            <span className="hidden max-w-48 truncate text-sm text-muted-foreground lg:inline" title={session.empresa}>
              · {session.empresa}
            </span>
          )}

          <nav className="hidden items-center gap-1 md:flex" aria-label="Principal">
            {itens.map(({ to, label }) => (
              <NavLink key={to} to={to} className={linkClass}>
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto">
            <UserMenu />
          </div>
        </div>
      </header>

      <main id="conteudo" className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
