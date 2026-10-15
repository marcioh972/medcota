import { CopyIcon, KeyRoundIcon, RefreshCwIcon, ShieldOffIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { ErrorState } from "@/components/data-states"
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
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { mensagemDeErro } from "@/lib/api"
import { dataHora } from "@/lib/format"

import { useEmpresa, useGerarCodigo, useRevogarCodigo } from "./api"

async function copiar(texto: string, mensagem: string) {
  try {
    await navigator.clipboard.writeText(texto)
    toast.success(mensagem)
  } catch {
    toast.error("Não foi possível copiar. Selecione e copie manualmente.")
  }
}

type Acao = "gerar" | "revogar" | null

export function CodigoCard() {
  const { data: empresa, isPending, error, refetch } = useEmpresa()
  const gerar = useGerarCodigo()
  const revogar = useRevogarCodigo()
  const [confirmando, setConfirmando] = useState<Acao>(null)

  if (isPending) return <Skeleton className="h-44" role="status" aria-label="Carregando" />
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />

  const link = empresa.codigo_ativo && empresa.codigo_validacao
    ? `${window.location.origin}/cadastro/funcionario?codigo=${empresa.codigo_validacao}`
    : null

  function executar(acao: Exclude<Acao, null>) {
    const mutacao = acao === "gerar" ? gerar : revogar
    mutacao.mutate(undefined, {
      onSuccess: () => toast.success(acao === "gerar" ? "Novo código gerado" : "Código revogado"),
      onError: (e) => toast.error(mensagemDeErro(e)),
      onSettled: () => setConfirmando(null),
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRoundIcon className="size-4" /> Código de validação
          {empresa.codigo_ativo ? <Badge className="border-transparent bg-success text-success-foreground">Ativo</Badge> : <Badge variant="outline">Sem código ativo</Badge>}
        </CardTitle>
        <CardDescription>
          Compartilhe o código com seus funcionários. Com ele, vendedores e compradores criam a própria conta e senha
          dentro da <strong>{empresa.nome}</strong>. O código é único da sua empresa.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {empresa.codigo_ativo && empresa.codigo_validacao ? (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <code
                className="rounded-md border bg-muted px-4 py-2 font-mono text-xl font-semibold tracking-widest"
                aria-label="Código de validação"
              >
                {empresa.codigo_validacao}
              </code>
              <Button variant="outline" onClick={() => void copiar(empresa.codigo_validacao!, "Código copiado")}>
                <CopyIcon /> Copiar código
              </Button>
              {link && (
                <Button variant="ghost" onClick={() => void copiar(link, "Link de cadastro copiado")}>
                  <CopyIcon /> Copiar link
                </Button>
              )}
            </div>
            {empresa.codigo_expira_em && (
              <p className="text-sm text-muted-foreground">Válido até {dataHora(empresa.codigo_expira_em)}.</p>
            )}
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            Nenhum código ativo: ninguém consegue se cadastrar na empresa. Gere um código para convidar a equipe.
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            variant={empresa.codigo_ativo ? "outline" : "default"}
            disabled={gerar.isPending}
            onClick={() => (empresa.codigo_ativo ? setConfirmando("gerar") : executar("gerar"))}
          >
            {gerar.isPending ? <Spinner /> : <RefreshCwIcon />} {empresa.codigo_ativo ? "Gerar novo código" : "Gerar código"}
          </Button>
          {empresa.codigo_ativo && (
            <Button variant="ghost" className="text-destructive" onClick={() => setConfirmando("revogar")}>
              <ShieldOffIcon /> Revogar
            </Button>
          )}
        </div>
      </CardContent>

      <AlertDialog open={confirmando !== null} onOpenChange={(o) => !o && setConfirmando(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirmando === "gerar" ? "Gerar um novo código?" : "Revogar o código?"}</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmando === "gerar"
                ? "O código atual deixa de funcionar imediatamente. Quem ainda não se cadastrou precisará do novo."
                : "Ninguém conseguirá se cadastrar até você gerar um novo código. Contas já criadas não são afetadas."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault()
                if (confirmando) executar(confirmando)
              }}
            >
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}
