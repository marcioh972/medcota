import { useQuery } from "@tanstack/react-query"

import { ErrorState } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { moeda } from "@/lib/format"
import type { Dashboard } from "@/lib/types"

function Indicador({ titulo, valor, nota }: { titulo: string; valor: string; nota?: string }) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{titulo}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">{valor}</CardTitle>
      </CardHeader>
      {nota && <CardContent className="text-xs text-muted-foreground">{nota}</CardContent>}
    </Card>
  )
}

export function Component() {
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: ({ signal }) => api.get<Dashboard>("/dashboard", undefined, signal),
  })

  return (
    <>
      <PageHeader title="Painel" description="Visão geral das compras de hoje." />
      {isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" role="status" aria-label="Carregando">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Indicador titulo="Itens em falta hoje" valor={String(data.itens_em_falta)} />
          <Indicador titulo="Taxa de atendimento" valor={`${data.taxa_atendimento.toLocaleString("pt-BR")}%`} nota="Faltas já compradas" />
          <Indicador titulo="Pedidos" valor={String(data.pedidos)} />
          <Indicador
            titulo="Economia gerada"
            valor={moeda(data.economia_gerada)}
            nota={data.economia_gerada === null ? "Sem permissão para ver valores" : "Sobre a média histórica"}
          />
        </div>
      )}
    </>
  )
}
