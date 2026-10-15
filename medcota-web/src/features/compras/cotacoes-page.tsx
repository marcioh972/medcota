import { CopyIcon, ExternalLinkIcon, RefreshCwIcon } from "lucide-react"
import { Link } from "react-router"
import { toast } from "sonner"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/features/auth/use-auth"
import { mensagemDeErro } from "@/lib/api"
import { dataHora, parseUtc } from "@/lib/format"

import { useCotacoes, useSegundaRodada } from "./api"

const linkPublico = (token: string) => `${window.location.origin}/c/${token}`

export function Component() {
  const { session } = useAuth()
  const { data, isPending, error, refetch, dataUpdatedAt } = useCotacoes()
  const segunda = useSegundaRodada()
  const ehComprador = session?.perfil === "comprador"

  async function copiar(token: string) {
    try {
      await navigator.clipboard.writeText(linkPublico(token))
      toast.success("Link copiado")
    } catch {
      toast.error("Não foi possível copiar. Copie o link manualmente.")
    }
  }

  return (
    <>
      <PageHeader
        title="Cotações"
        description="Uma lista por fornecedor, enviada por link."
        actions={
          ehComprador && (
            <Button variant="outline" asChild>
              <Link to="/consolidacao">Gerar a partir da consolidação</Link>
            </Button>
          )
        }
      />
      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Nenhuma cotação gerada" description="Gere cotações a partir da consolidação do dia." />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fornecedor</TableHead>
                <TableHead>Escopo</TableHead>
                <TableHead className="text-right">Respostas</TableHead>
                <TableHead className="text-right">Rodada</TableHead>
                <TableHead className="text-right">Aberturas</TableHead>
                <TableHead>Expira em</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((c) => {
                const expirada = parseUtc(c.expira_em).getTime() < dataUpdatedAt // referência: última atualização dos dados
                return (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.fornecedor}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{c.escopo}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {c.respostas}/{c.itens}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{c.rodada}</TableCell>
                    <TableCell className="text-right tabular-nums">{c.aberturas}</TableCell>
                    <TableCell>
                      {dataHora(c.expira_em)} {expirada && <Badge variant="destructive">Expirada</Badge>}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" aria-label={`Copiar link de ${c.fornecedor}`} onClick={() => void copiar(c.token)}>
                          <CopyIcon />
                        </Button>
                        <Button variant="ghost" size="icon" asChild>
                          <a href={linkPublico(c.token)} target="_blank" rel="noreferrer" aria-label={`Abrir link de ${c.fornecedor}`}>
                            <ExternalLinkIcon />
                          </a>
                        </Button>
                        {ehComprador && (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={segunda.isPending}
                            onClick={() =>
                              segunda.mutate(c.id, {
                                onSuccess: () => toast.success("2ª rodada aberta e link renovado"),
                                onError: (e) => toast.error(mensagemDeErro(e)),
                              })
                            }
                          >
                            <RefreshCwIcon /> 2ª rodada
                          </Button>
                        )}
                      </div>
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
