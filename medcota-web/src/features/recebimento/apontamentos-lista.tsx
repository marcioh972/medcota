import { AlertTriangleIcon, CircleXIcon, InfoIcon } from "lucide-react"

import { SEVERIDADE } from "@/lib/labels"
import type { Apontamento, Severidade } from "@/lib/types"
import { cn } from "@/lib/utils"

const ESTILO: Record<Severidade, { icone: typeof InfoIcon; cor: string }> = {
  erro: { icone: CircleXIcon, cor: "text-destructive" },
  alerta: { icone: AlertTriangleIcon, cor: "text-amber-600 dark:text-amber-400" },
  info: { icone: InfoIcon, cor: "text-muted-foreground" },
}

function Linha({ a }: { a: Apontamento }) {
  const { icone: Icone, cor } = ESTILO[a.severidade]
  const detalhes = [
    a.item_numero !== null && `Item ${a.item_numero}`,
    a.campo,
    a.esperado !== null && `esperado: ${a.esperado}`,
    a.encontrado !== null && `encontrado: ${a.encontrado}`,
  ].filter(Boolean)
  return (
    <li className="flex gap-3 py-2">
      <Icone className={cn("mt-0.5 size-4 shrink-0", cor)} aria-hidden />
      <div className="min-w-0 space-y-1">
        <p className="text-sm">
          <span className="sr-only">{SEVERIDADE[a.severidade]}: </span>
          {a.mensagem}
        </p>
        {detalhes.length > 0 && <p className="text-xs text-muted-foreground">{detalhes.join(" · ")}</p>}
        {a.base_legal && <p className="text-xs text-muted-foreground">Base: {a.base_legal}</p>}
      </div>
    </li>
  )
}

function Grupo({ titulo, itens }: { titulo: string; itens: Apontamento[] }) {
  return (
    <section aria-label={titulo}>
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {titulo} ({itens.length})
      </h4>
      <ul className="divide-y">
        {itens.map((a, i) => (
          <Linha key={`${a.codigo}-${a.item_numero ?? "n"}-${i}`} a={a} />
        ))}
      </ul>
    </section>
  )
}

/** Apontamentos da conferência: erros e alertas abertos; informações recolhidas. */
export function ApontamentosLista({ apontamentos }: { apontamentos: Apontamento[] }) {
  const por = (s: Severidade) => apontamentos.filter((a) => a.severidade === s)
  const erros = por("erro")
  const alertas = por("alerta")
  const infos = por("info")

  if (apontamentos.length === 0) return <p className="text-sm text-muted-foreground">Nenhum apontamento.</p>

  return (
    <div className="space-y-4">
      {erros.length > 0 && <Grupo titulo="Erros" itens={erros} />}
      {alertas.length > 0 && <Grupo titulo="Alertas" itens={alertas} />}
      {erros.length === 0 && alertas.length === 0 && (
        <p className="text-sm text-success">Nenhum erro ou alerta: preços, quantidades, frete, impostos e totais conferem.</p>
      )}
      {infos.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Informações e limites da conferência ({infos.length})
          </summary>
          <div className="mt-2">
            <ul className="divide-y">
              {infos.map((a, i) => (
                <Linha key={`${a.codigo}-${i}`} a={a} />
              ))}
            </ul>
          </div>
        </details>
      )}
    </div>
  )
}
