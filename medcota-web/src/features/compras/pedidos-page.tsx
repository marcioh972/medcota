import { CheckIcon, XIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { PedidoStatusBadge } from "@/components/status-badge"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/features/auth/use-auth"
import { mensagemDeErro } from "@/lib/api"
import { dataHora, moeda } from "@/lib/format"
import type { Pedido } from "@/lib/types"

import { useAprovarPedido, usePedidos } from "./api"

export function Component() {
  const { session } = useAuth()
  const { data, isPending, error, refetch } = usePedidos()
  const aprovar = useAprovarPedido()
  const [decisao, setDecisao] = useState<{ pedido: Pedido; aprovado: boolean } | null>(null)
  const ehGestor = session?.perfil === "gestor"

  function confirmar() {
    if (!decisao) return
    aprovar.mutate(
      { id: decisao.pedido.id, aprovado: decisao.aprovado },
      {
        onSuccess: () => toast.success(decisao.aprovado ? "Pedido aprovado" : "Pedido reprovado"),
        onError: (e) => toast.error(mensagemDeErro(e)),
        onSettled: () => setDecisao(null),
      },
    )
  }

  return (
    <>
      <PageHeader title="Pedidos" description="Pedidos acima da alçada precisam da aprovação do gestor." />
      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Nenhum pedido" description="Os pedidos aparecem aqui depois que a compra é fechada." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Pedido</TableHead>
                <TableHead>Criado em</TableHead>
                <TableHead className="text-right">Itens</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
                {ehGestor && <TableHead className="text-right">Ações</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">#{p.id}</TableCell>
                  <TableCell>{dataHora(p.criado_em)}</TableCell>
                  <TableCell className="text-right tabular-nums">{p.itens.length}</TableCell>
                  <TableCell className="text-right font-medium tabular-nums">{moeda(p.total)}</TableCell>
                  <TableCell>
                    <PedidoStatusBadge status={p.status} />
                  </TableCell>
                  {ehGestor && (
                    <TableCell>
                      {p.status === "aguardando_aprovacao" && (
                        <div className="flex justify-end gap-2">
                          <Button size="sm" onClick={() => setDecisao({ pedido: p, aprovado: true })}>
                            <CheckIcon /> Aprovar
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setDecisao({ pedido: p, aprovado: false })}>
                            <XIcon /> Reprovar
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <AlertDialog open={decisao !== null} onOpenChange={(o) => !o && setDecisao(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {decisao?.aprovado ? "Aprovar" : "Reprovar"} pedido #{decisao?.pedido.id}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {decisao?.aprovado
                ? `Total de ${moeda(decisao.pedido.total)}.`
                : "As faltas deste pedido voltarão como “sem oferta”. Esta ação não pode ser desfeita."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault()
                confirmar()
              }}
              disabled={aprovar.isPending}
            >
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
