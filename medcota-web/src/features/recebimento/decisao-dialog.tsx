import { useState } from "react"
import { toast } from "sonner"

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { mensagemDeErro } from "@/lib/api"
import type { NFeResumo } from "@/lib/types"

import { useDecidirNfe } from "./api"

export type TipoDecisao = "aceita" | "recusada"

interface Props {
  nfe: NFeResumo
  tipo: TipoDecisao | null
  onClose: () => void
}

/** Aceitar ou recusar a nota. Nota com erro exige justificativa (e só o gestor pode aceitá-la). */
export function DecisaoDialog({ nfe, tipo, onClose }: Props) {
  const [justificativa, setJustificativa] = useState("")
  const decidir = useDecidirNfe()
  const aceitando = tipo === "aceita"
  const minimo = tipo === "recusada" ? 5 : nfe.resultado === "reprovada" ? 10 : 0
  const texto = justificativa.trim()
  const invalida = texto.length < minimo

  function confirmar() {
    if (!tipo || invalida) return
    decidir.mutate(
      { id: nfe.id, decisao: tipo, justificativa: texto },
      {
        onSuccess: () => {
          toast.success(aceitando ? "Nota aceita" : "Nota recusada")
          setJustificativa("")
          onClose()
        },
        onError: (e) => toast.error(mensagemDeErro(e)),
      },
    )
  }

  return (
    <AlertDialog open={tipo !== null} onOpenChange={(o) => !o && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{aceitando ? "Aceitar nota" : "Recusar nota"} {nfe.numero ? `nº ${nfe.numero}` : ""}?</AlertDialogTitle>
          <AlertDialogDescription>
            {aceitando
              ? nfe.resultado === "reprovada"
                ? "Esta nota tem erros na conferência. Ao aceitá-la você assume a divergência: explique o motivo."
                : "A mercadoria será dada como recebida para este fornecedor."
              : "A nota será marcada como recusada e o pedido volta a aguardar uma nova nota."}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {(minimo > 0 || !aceitando) && (
          <div className="space-y-2">
            <Label htmlFor="justificativa">
              {aceitando ? "Justificativa" : "Motivo"} (mínimo de {minimo} caracteres)
            </Label>
            <Textarea
              id="justificativa"
              rows={3}
              maxLength={500}
              value={justificativa}
              onChange={(e) => setJustificativa(e.target.value)}
              aria-invalid={texto.length > 0 && invalida}
            />
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <Button
            variant={aceitando ? "default" : "destructive"}
            onClick={confirmar}
            disabled={invalida || decidir.isPending}
          >
            {decidir.isPending && <Spinner />} {aceitando ? "Aceitar nota" : "Recusar nota"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
