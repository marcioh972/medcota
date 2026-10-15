import {
  BarChart3Icon,
  BoxesIcon,
  ClipboardListIcon,
  LayersIcon,
  PackageCheckIcon,
  PackageXIcon,
  ScaleIcon,
  SendIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react"

import type { Perfil } from "@/lib/types"

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

const VENDEDOR: NavItem[] = [{ to: "/faltas", label: "Minhas faltas", icon: PackageXIcon }]

const COMPRAS: NavItem[] = [
  { to: "/dashboard", label: "Painel", icon: BarChart3Icon },
  { to: "/consolidacao", label: "Consolidação", icon: LayersIcon },
  { to: "/cotacoes", label: "Cotações", icon: SendIcon },
  { to: "/comparativo", label: "Comparativo", icon: ScaleIcon },
  { to: "/pedidos", label: "Pedidos", icon: ClipboardListIcon },
  { to: "/recebimento", label: "Recebimento", icon: PackageCheckIcon },
  { to: "/cadastros", label: "Cadastros", icon: BoxesIcon },
]

const GESTOR_EXTRA: NavItem[] = [{ to: "/equipe", label: "Equipe", icon: UsersIcon }]

export function navDoPerfil(perfil: Perfil): NavItem[] {
  if (perfil === "vendedor") return VENDEDOR
  return perfil === "gestor" ? [...COMPRAS, ...GESTOR_EXTRA] : COMPRAS
}
