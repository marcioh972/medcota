import { PlusIcon, SettingsIcon } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { PedidoStatusBadge, RecebimentoBadge, ResultadoNFeBadge } from "@/components/status-badge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { dataHora, moeda } from "@/lib/format"
import type { StatusRecebimento } from "@/lib/types"

import { usePedidosRecebimento } from "./api"

const ABAS: { valor: "todos" | StatusRecebimento; rotulo: string }[] = [
  { valor: "todos", rotulo: "Todos" },
  { valor: "aguardando_nfe", rotulo: "Aguardando nota" },
  { valor: "em_conferencia", rotulo: "Em conferência" },
  { valor: "recebido", rotulo: "Recebidos" },
]

export function Component() {
  const [aba, setAba] = useState<"todos" | StatusRecebimento>("todos")
  const { data, isPending, error, refetch } = usePedidosRecebimento(aba === "todos" ? undefined : aba)

  const novo = (
    <Button asChild>
      <Link to="/recebimento/novo">
        <PlusIcon /> Registrar pedido
      </Link>
    </Button>
  )

  return (
    <>
      <PageHeader
        title="Recebimento"
        description="Registre o pedido e, quando a mercadoria chegar, envie o XML da nota para a conferência fiscal."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link to="/recebimento/parametros">
                <SettingsIcon /> Parâmetros fiscais
              </Link>
            </Button>
            {novo}
          </>
        }
      />

      <Tabs value={aba} onValueChange={(v) => setAba(v as typeof aba)} className="mb-4">
        <TabsList>
          {ABAS.map((a) => (
            <TabsTrigger key={a.valor} value={a.valor}>
              {a.rotulo}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState
          title="Nenhum pedido nesta situação"
          description="Registre um pedido de compra para acompanhar o recebimento."
          action={novo}
        />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Pedido</TableHead>
                <TableHead>Fornecedor</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Recebimento</TableHead>
                <TableHead>Última nota</TableHead>
                <TableHead className="text-right">Ação</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((p) => {
                const ultima = p.nfes[0]
                return (
                  <TableRow key={p.id}>
                    <TableCell>
                      <p className="font-medium">#{p.id}</p>
                      <p className="text-xs text-muted-foreground">{dataHora(p.criado_em)}</p>
                    </TableCell>
                    <TableCell>
                      {p.fornecedores.map((f) => f.nome).join(", ")}
                      {p.origem === "manual" && (
                        <Badge variant="outline" className="ml-2">
                          Manual
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{moeda(p.total)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        <RecebimentoBadge status={p.recebimento} />
                        {p.status !== "aprovado" && <PedidoStatusBadge status={p.status} />}
                      </div>
                    </TableCell>
                    <TableCell>{ultima ? <ResultadoNFeBadge resultado={ultima.resultado} /> : <span className="text-muted-foreground">—</span>}</TableCell>
                    <TableCell className="text-right">
                      <Button size="sm" variant="outline" asChild>
                        <Link to={`/recebimento/${p.id}`}>{p.recebimento === "recebido" ? "Ver" : "Conferir nota"}</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  )
}
