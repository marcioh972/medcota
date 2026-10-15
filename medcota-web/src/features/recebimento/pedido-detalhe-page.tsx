import { ArrowLeftIcon } from "lucide-react"
import { Link, useParams } from "react-router"

import { ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { PedidoStatusBadge, RecebimentoBadge } from "@/components/status-badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { dataHora, moeda } from "@/lib/format"

import { usePedidoRecebimento } from "./api"
import { EnviarNfeCard } from "./enviar-nfe-card"
import { NfeCard } from "./nfe-card"

export function Component() {
  const id = Number(useParams().pedidoId)
  const { data: pedido, isPending, error, refetch } = usePedidoRecebimento(id)

  if (isPending) return <TableSkeleton />
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />

  return (
    <>
      <PageHeader
        title={`Pedido #${pedido.id}`}
        description={`Criado em ${dataHora(pedido.criado_em)}${pedido.numero_externo ? ` · Nº do fornecedor: ${pedido.numero_externo}` : ""}`}
        actions={
          <Button variant="outline" asChild>
            <Link to="/recebimento">
              <ArrowLeftIcon /> Recebimento
            </Link>
          </Button>
        }
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-base">Resumo</CardTitle>
              <RecebimentoBadge status={pedido.recebimento} />
              <PedidoStatusBadge status={pedido.status} />
              <Badge variant="outline">{pedido.origem === "manual" ? "Registrado na tela" : "Das cotações"}</Badge>
            </div>
            <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted-foreground">Total</dt>
                <dd className="font-medium tabular-nums">{moeda(pedido.total)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Frete previsto</dt>
                <dd className="tabular-nums">{moeda(pedido.frete_previsto)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Fornecedor(es)</dt>
                <dd className="space-y-0.5">
                  {pedido.fornecedores.map((f) => (
                    <p key={f.id}>
                      {f.nome}
                      {f.cnpj ? <span className="text-muted-foreground"> · {f.cnpj}</span> : <span className="text-amber-600 dark:text-amber-400"> · sem CNPJ cadastrado</span>}
                      {f.credenciado_72101 && <Badge variant="secondary" className="ml-2">Credenciado 72.101</Badge>}
                    </p>
                  ))}
                </dd>
              </div>
            </dl>
            {pedido.observacao && <p className="text-sm text-muted-foreground">{pedido.observacao}</p>}
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Produto</TableHead>
                  <TableHead className="text-right">Quantidade</TableHead>
                  <TableHead className="text-right">Preço unitário</TableHead>
                  <TableHead className="text-right">Subtotal</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pedido.itens.map((i) => (
                  <TableRow key={i.produto_id}>
                    <TableCell>
                      <p className="font-medium">{i.produto}</p>
                      {i.ean && <p className="text-xs text-muted-foreground">{i.ean}</p>}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{i.quantidade}</TableCell>
                    <TableCell className="text-right tabular-nums">{moeda(i.preco)}</TableCell>
                    <TableCell className="text-right tabular-nums">{moeda(String(Number(i.preco) * i.quantidade))}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {pedido.status === "aprovado" ? (
          <EnviarNfeCard pedidoId={pedido.id} />
        ) : (
          <Alert>
            <AlertDescription>
              Este pedido ainda aguarda a aprovação do gestor. Depois de aprovado, será possível enviar a nota fiscal.
            </AlertDescription>
          </Alert>
        )}

        {pedido.nfes.length > 0 && (
          <section aria-labelledby="titulo-notas" className="space-y-4">
            <h2 id="titulo-notas" className="text-lg font-semibold tracking-tight">
              Notas fiscais deste pedido
            </h2>
            {pedido.nfes.map((n) => (
              <NfeCard key={n.id} resumo={n} />
            ))}
          </section>
        )}
      </div>
    </>
  )
}
