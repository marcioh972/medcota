import { FileUpIcon } from "lucide-react"
import { useRef, useState } from "react"
import { Link } from "react-router"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { ApiError, mensagemDeErro } from "@/lib/api"

import { useEnviarNfe } from "./api"

const LIMITE_MB = 2

export function EnviarNfeCard({ pedidoId }: { pedidoId: number }) {
  const entrada = useRef<HTMLInputElement>(null)
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [erro, setErro] = useState<ApiError | null>(null)
  const enviar = useEnviarNfe(pedidoId)

  function aoEscolher(f: File | null) {
    setErro(null)
    if (f && f.size > LIMITE_MB * 1_000_000) {
      setArquivo(null)
      setErro(new ApiError(413, "arquivo_grande", `O arquivo excede o limite de ${LIMITE_MB} MB.`))
      return
    }
    setArquivo(f)
  }

  function aoEnviar() {
    if (!arquivo) return
    setErro(null)
    enviar.mutate(arquivo, {
      onSuccess: (nfe) => {
        toast.success(
          nfe.resultado === "aprovada"
            ? "Nota enviada: nenhum erro ou alerta"
            : `Nota enviada: ${nfe.erros} erro(s) e ${nfe.alertas} alerta(s)`,
        )
        setArquivo(null)
        if (entrada.current) entrada.current.value = ""
      },
      onError: (e) => (e instanceof ApiError ? setErro(e) : toast.error(mensagemDeErro(e))),
    })
  }

  const duplicada = erro?.codigo === "nfe_duplicada"

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Enviar XML da nota fiscal</CardTitle>
        <CardDescription>
          Use o XML <strong>autorizado</strong> (com protocolo da SEFAZ) enviado pelo fornecedor. O sistema confere
          preços, quantidades, frete, impostos e totais contra este pedido.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {erro && (
          <Alert variant="destructive" role="alert">
            <AlertTitle>{duplicada ? "Nota já enviada" : "Não foi possível enviar a nota"}</AlertTitle>
            <AlertDescription>{erro.message}</AlertDescription>
          </Alert>
        )}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="grid flex-1 gap-2">
            <Label htmlFor="arquivo-nfe">Arquivo XML (até {LIMITE_MB} MB)</Label>
            <Input
              id="arquivo-nfe"
              ref={entrada}
              type="file"
              accept=".xml,text/xml,application/xml"
              onChange={(e) => aoEscolher(e.target.files?.[0] ?? null)}
            />
          </div>
          <Button onClick={aoEnviar} disabled={!arquivo || enviar.isPending}>
            {enviar.isPending ? <Spinner /> : <FileUpIcon />} Enviar e conferir
          </Button>
        </div>
        {duplicada && (
          <p className="text-sm text-muted-foreground">
            Ela já aparece abaixo, ou em <Link to="/recebimento" className="underline">Recebimento</Link>.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
