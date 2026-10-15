import { CheckIcon, DownloadIcon, RefreshCwIcon, XIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { ErrorState } from "@/components/data-states"
import { DecisaoBadge, ResultadoNFeBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { useAuth } from "@/features/auth/use-auth"
import { baixarArquivo, mensagemDeErro } from "@/lib/api"
import { dataHora, moeda } from "@/lib/format"
import type { NFeResumo } from "@/lib/types"

import { useNfe, useReanalisarNfe } from "./api"
import { ApontamentosLista } from "./apontamentos-lista"
import { DecisaoDialog, type TipoDecisao } from "./decisao-dialog"

export function NfeCard({ resumo }: { resumo: NFeResumo }) {
  const { session } = useAuth()
  const { data: nfe, isPending, error, refetch } = useNfe(resumo.id)
  const reanalisar = useReanalisarNfe()
  const [decisao, setDecisao] = useState<TipoDecisao | null>(null)
  const [baixando, setBaixando] = useState(false)

  const pendente = resumo.decisao === "pendente"
  const ehGestor = session?.perfil === "gestor"
  const comErro = resumo.resultado === "reprovada"
  const bloqueadoParaComprador = comErro && !ehGestor

  async function baixarXml() {
    setBaixando(true)
    try {
      const blob = await baixarArquivo(`/recebimento/nfes/${resumo.id}/xml`)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `NFe${resumo.chave_acesso}.xml`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast.error(mensagemDeErro(e))
    } finally {
      setBaixando(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-base">
              NF-e {resumo.numero ?? "—"}
              {resumo.serie ? ` · série ${resumo.serie}` : ""}
            </CardTitle>
            <CardDescription>
              {resumo.emitente_nome ?? "Emitente não informado"}
              {resumo.emitente_cnpj ? ` · ${resumo.emitente_cnpj}` : ""}
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <ResultadoNFeBadge resultado={resumo.resultado} />
            <DecisaoBadge decisao={resumo.decisao} />
          </div>
        </div>
        <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs text-muted-foreground">Emissão</dt>
            <dd>{resumo.data_emissao ? dataHora(resumo.data_emissao) : "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Valor da nota</dt>
            <dd className="font-medium tabular-nums">{moeda(resumo.valor_total)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Frete na nota</dt>
            <dd className="tabular-nums">{moeda(resumo.valor_frete)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Chave de acesso</dt>
            <dd className="break-all font-mono text-xs">{resumo.chave_acesso}</dd>
          </div>
        </dl>
      </CardHeader>

      <CardContent className="space-y-4">
        {isPending ? (
          <Skeleton className="h-24" role="status" aria-label="Carregando apontamentos" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : (
          <>
            <ApontamentosLista apontamentos={nfe.apontamentos} />
            {nfe.justificativa && (
              <p className="rounded-md border bg-muted/40 p-3 text-sm">
                <span className="font-medium">Justificativa:</span> {nfe.justificativa}
              </p>
            )}
          </>
        )}

        <div className="flex flex-wrap gap-2">
          {pendente && (
            <>
              <Button onClick={() => setDecisao("aceita")} disabled={bloqueadoParaComprador}>
                <CheckIcon /> Aceitar nota
              </Button>
              <Button variant="outline" onClick={() => setDecisao("recusada")}>
                <XIcon /> Recusar nota
              </Button>
              <Button
                variant="ghost"
                disabled={reanalisar.isPending}
                onClick={() =>
                  reanalisar.mutate(resumo.id, {
                    onSuccess: () => toast.success("Nota reanalisada"),
                    onError: (e) => toast.error(mensagemDeErro(e)),
                  })
                }
              >
                {reanalisar.isPending ? <Spinner /> : <RefreshCwIcon />} Reanalisar
              </Button>
            </>
          )}
          <Button variant="ghost" onClick={() => void baixarXml()} disabled={baixando}>
            <DownloadIcon /> Baixar XML
          </Button>
        </div>
        {pendente && bloqueadoParaComprador && (
          <p className="text-xs text-muted-foreground">
            Nota com erros: apenas o gestor pode aceitá-la (com justificativa). Você pode recusá-la ou corrigir o
            cadastro e reanalisar.
          </p>
        )}
        <p className="text-xs text-muted-foreground">
          Enviada em {dataHora(resumo.importada_em)}. Conferência automática: não substitui a análise do contador nem
          consulta a situação da nota na SEFAZ.
        </p>
      </CardContent>

      <DecisaoDialog nfe={resumo} tipo={decisao} onClose={() => setDecisao(null)} />
    </Card>
  )
}
