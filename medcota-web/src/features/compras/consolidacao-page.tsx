import { SendIcon } from "lucide-react"
import { useNavigate } from "react-router"
import { toast } from "sonner"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { UrgenciaBadge } from "@/components/status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/features/auth/use-auth"
import { mensagemDeErro } from "@/lib/api"

import { useConsolidacao, useGerarCotacoes } from "./api"

export function Component() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const { data, isPending, error, refetch } = useConsolidacao()
  const gerar = useGerarCotacoes()

  function aoGerar() {
    gerar.mutate(undefined, {
      onSuccess: (cotacoes) => {
        toast.success(`${cotacoes.length} cotação(ões) gerada(s)`)
        void navigate("/cotacoes")
      },
      onError: (e) => toast.error(mensagemDeErro(e)),
    })
  }

  const acao =
    session?.perfil === "comprador" ? (
      <Button onClick={aoGerar} disabled={gerar.isPending || !data?.length}>
        {gerar.isPending ? <Spinner /> : <SendIcon />} Gerar cotações
      </Button>
    ) : undefined

  return (
    <>
      <PageHeader title="Consolidação" description="Demanda de hoje agrupada por produto." actions={acao} />
      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Sem faltas hoje" description="Quando os vendedores lançarem faltas, a demanda aparece aqui." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Produto</TableHead>
                <TableHead>Origem</TableHead>
                <TableHead className="text-right">Demanda</TableHead>
                <TableHead className="text-right">Clientes</TableHead>
                <TableHead>Solicitantes</TableHead>
                <TableHead>Urgência</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((c) => (
                <TableRow key={c.produto_id}>
                  <TableCell>
                    <p className="font-medium">{c.produto}</p>
                    {c.ean && <p className="text-xs text-muted-foreground">{c.ean}</p>}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{c.origem}</Badge>
                  </TableCell>
                  <TableCell className="text-right font-medium tabular-nums">{c.demanda}</TableCell>
                  <TableCell className="text-right tabular-nums">{c.clientes}</TableCell>
                  <TableCell className="text-muted-foreground">{c.solicitantes.join(", ")}</TableCell>
                  <TableCell>
                    <UrgenciaBadge urgencia={c.urgencia_maxima} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  )
}
