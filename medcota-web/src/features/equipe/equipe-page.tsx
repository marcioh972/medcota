import { toast } from "sonner"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { mensagemDeErro } from "@/lib/api"

import { useAtualizarMembro, useEquipe } from "./api"
import { CodigoCard } from "./codigo-card"

const PERFIL = { vendedor: "Vendedor", comprador: "Comprador", gestor: "Gestor" } as const

export function Component() {
  const { data, isPending, error, refetch } = useEquipe()
  const atualizar = useAtualizarMembro()

  return (
    <>
      <PageHeader title="Equipe" description="Convide funcionários com o código da empresa e gerencie os acessos." />
      <div className="space-y-8">
        <CodigoCard />

        <section aria-labelledby="titulo-membros" className="space-y-3">
          <h2 id="titulo-membros" className="text-lg font-semibold tracking-tight">
            Membros
          </h2>
          {isPending ? (
            <TableSkeleton rows={3} />
          ) : error ? (
            <ErrorState error={error} onRetry={() => void refetch()} />
          ) : data.length === 0 ? (
            <EmptyState title="Nenhum membro" />
          ) : (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>E-mail</TableHead>
                    <TableHead>Perfil</TableHead>
                    <TableHead>Vê preços</TableHead>
                    <TableHead>Ativo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.map((m) => {
                    // o gestor nasce com a empresa e não pode desativar a própria conta (a API também recusa)
                    const protegido = m.perfil === "gestor"
                    const mudar = (campos: { ativo?: boolean; ver_preco_custo?: boolean }) =>
                      atualizar.mutate(
                        { id: m.id, ...campos },
                        { onError: (e) => toast.error(mensagemDeErro(e)) },
                      )
                    return (
                      <TableRow key={m.id} className={m.ativo ? undefined : "text-muted-foreground"}>
                        <TableCell className="font-medium">{m.nome}</TableCell>
                        <TableCell>{m.email}</TableCell>
                        <TableCell>
                          <Badge variant={m.perfil === "gestor" ? "default" : "secondary"}>{PERFIL[m.perfil]}</Badge>
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={m.ver_preco_custo}
                            onCheckedChange={(v) => mudar({ ver_preco_custo: v })}
                            disabled={atualizar.isPending}
                            aria-label={`${m.nome} pode ver preços e custos`}
                          />
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={m.ativo}
                            onCheckedChange={(v) => mudar({ ativo: v })}
                            disabled={atualizar.isPending || protegido}
                            aria-label={`${m.nome} está ativo`}
                          />
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </section>
      </div>
    </>
  )
}
