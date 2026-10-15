import { PlusIcon } from "lucide-react"
import { useState } from "react"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { FaltaStatusBadge, UrgenciaBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { useFaltasHoje } from "./api"
import { FaltaDialog } from "./falta-dialog"

export function Component() {
  const [aberto, setAberto] = useState(false)
  const { data, isPending, error, refetch } = useFaltasHoje()

  const botao = (
    <Button onClick={() => setAberto(true)}>
      <PlusIcon /> Lançar falta
    </Button>
  )

  return (
    <>
      <PageHeader title="Minhas faltas" description="Itens que faltaram hoje para seus clientes." actions={botao} />

      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Nenhuma falta lançada hoje" description="Quando um cliente pedir algo que você não tem, registre aqui." action={botao} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Produto</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead className="text-right">Qtd</TableHead>
                <TableHead>Urgência</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Detalhe</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((f) => (
                <TableRow key={f.id}>
                  <TableCell>
                    <p className="font-medium">{f.produto}</p>
                    {f.ean && <p className="text-xs text-muted-foreground">{f.ean}</p>}
                  </TableCell>
                  <TableCell>{f.cliente}</TableCell>
                  <TableCell className="text-right tabular-nums">{f.quantidade}</TableCell>
                  <TableCell>
                    <UrgenciaBadge urgencia={f.urgencia} />
                  </TableCell>
                  <TableCell>
                    <FaltaStatusBadge status={f.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">{f.detalhe || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <FaltaDialog open={aberto} onOpenChange={setAberto} />
    </>
  )
}
