import { ShoppingCartIcon, TriangleAlertIcon } from "lucide-react"
import { useState } from "react"
import { useNavigate } from "react-router"
import { toast } from "sonner"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
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
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/features/auth/use-auth"
import { mensagemDeErro } from "@/lib/api"
import { moeda } from "@/lib/format"
import { PAGAMENTO } from "@/lib/labels"
import { cn } from "@/lib/utils"

import { useComparativo, useFecharCompra } from "./api"

export function Component() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const { data, isPending, error, refetch } = useComparativo()
  const fechar = useFecharCompra()
  const [confirmar, setConfirmar] = useState(false)
  const ehComprador = session?.perfil === "comprador"

  function aoFechar() {
    fechar.mutate(undefined, {
      onSuccess: (pedido) => {
        toast.success(
          pedido.status === "aguardando_aprovacao"
            ? `Pedido #${pedido.id} criado e enviado para aprovação do gestor`
            : `Pedido #${pedido.id} criado`,
        )
        void navigate("/pedidos")
      },
      onError: (e) => toast.error(mensagemDeErro(e)),
      onSettled: () => setConfirmar(false),
    })
  }

  return (
    <>
      <PageHeader
        title="Comparativo"
        description="Menor custo final por produto: preço, desconto financeiro e frete rateado."
        actions={
          ehComprador && (
            <Button onClick={() => setConfirmar(true)} disabled={!data?.length}>
              <ShoppingCartIcon /> Fechar compra
            </Button>
          )
        }
      />

      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Sem respostas para comparar" description="Assim que os fornecedores responderem, as ofertas aparecem aqui." />
      ) : (
        <div className="space-y-6">
          {data.map((item) => (
            <Card key={item.produto_id}>
              <CardHeader>
                <CardTitle>{item.produto}</CardTitle>
                <CardDescription>
                  Demanda: {item.demanda} un
                  {item.media_historica !== null && <> · Média histórica: {moeda(item.media_historica)}</>}
                </CardDescription>
                {item.sem_oferta_valida && (
                  <p className="flex items-center gap-2 text-sm text-destructive">
                    <TriangleAlertIcon className="size-4" /> Nenhuma oferta cobre a demanda.
                  </p>
                )}
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fornecedor</TableHead>
                      <TableHead className="text-right">Preço</TableHead>
                      <TableHead className="text-right">Qtd</TableHead>
                      <TableHead>Pagamento</TableHead>
                      <TableHead className="text-right">Prazo</TableHead>
                      <TableHead className="text-right">Custo final</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {item.ofertas.map((o) => (
                      <TableRow key={o.fornecedor} className={cn(o.vencedor && "bg-success/10")}>
                        <TableCell className="font-medium">{o.fornecedor}</TableCell>
                        <TableCell className="text-right tabular-nums">{moeda(o.preco)}</TableCell>
                        <TableCell className="text-right tabular-nums">{o.quantidade}</TableCell>
                        <TableCell>{PAGAMENTO[o.pagamento]}</TableCell>
                        <TableCell className="text-right tabular-nums">{o.prazo_dias} d</TableCell>
                        <TableCell className="text-right font-medium tabular-nums">{moeda(o.custo_final)}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap justify-end gap-1">
                            {o.vencedor && <Badge className="border-transparent bg-success text-success-foreground">Melhor oferta</Badge>}
                            {o.acima_da_media && <Badge variant="destructive">Acima da média</Badge>}
                            {o.quantidade < item.demanda && <Badge variant="outline">Qtd insuficiente</Badge>}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={confirmar} onOpenChange={setConfirmar}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Fechar compra?</AlertDialogTitle>
            <AlertDialogDescription>
              Será criado um pedido com a melhor oferta de cada produto. Pedidos acima da alçada aguardam a aprovação do gestor.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault() // mantém o diálogo aberto até a resposta da API
                aoFechar()
              }}
              disabled={fechar.isPending}
            >
              {fechar.isPending && <Spinner />} Fechar compra
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
