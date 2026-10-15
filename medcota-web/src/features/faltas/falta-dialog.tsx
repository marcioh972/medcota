import { zodResolver } from "@hookform/resolvers/zod"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { ApiError, mensagemDeErro } from "@/lib/api"
import { URGENCIA } from "@/lib/labels"
import type { FaltaIn, Produto } from "@/lib/types"

import { useLancarFalta } from "./api"
import { ProdutoCombobox } from "./produto-combobox"

const schema = z.object({
  produto: z.custom<Produto | null>().refine((p): boolean => p !== null && p !== undefined, "Selecione um produto"),
  cliente: z.string().trim().min(2, "Informe o cliente").max(150, "Máximo de 150 caracteres"),
  quantidade: z
    .string()
    .trim()
    .regex(/^\d+$/, "Use um número inteiro")
    .refine((v) => Number(v) > 0, "Deve ser maior que zero")
    .refine((v) => Number(v) <= 100_000, "Máximo de 100.000"),
  urgencia: z.enum(["baixa", "media", "alta"]),
  observacao: z.string().max(500, "Máximo de 500 caracteres"),
})
type Valores = z.infer<typeof schema>

const VAZIO: Valores = { produto: null, cliente: "", quantidade: "", urgencia: "media", observacao: "" }

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function FaltaDialog({ open, onOpenChange }: Props) {
  const form = useForm<Valores>({ resolver: zodResolver(schema), defaultValues: VAZIO })
  const lancar = useLancarFalta()
  const [duplicata, setDuplicata] = useState<{ mensagem: string; dados: FaltaIn } | null>(null)

  function concluir() {
    toast.success("Falta lançada")
    form.reset(VAZIO)
    setDuplicata(null)
    onOpenChange(false)
  }

  function enviar(dados: FaltaIn, somar: boolean) {
    lancar.mutate(
      { dados, somar },
      {
        onSuccess: concluir,
        onError: (erro) => {
          if (erro instanceof ApiError && erro.codigo === "duplicata") {
            setDuplicata({ mensagem: erro.message, dados }) // RF-08: pedir confirmação para somar
            return
          }
          toast.error(mensagemDeErro(erro))
        },
      },
    )
  }

  function aoSubmeter(v: Valores) {
    enviar(
      {
        produto_id: v.produto!.id,
        cliente: v.cliente.trim(),
        quantidade: Number(v.quantidade),
        urgencia: v.urgencia,
        observacao: v.observacao.trim(),
      },
      false,
    )
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Lançar falta</DialogTitle>
            <DialogDescription>Registre o item que faltou para um cliente hoje.</DialogDescription>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(aoSubmeter)} className="space-y-4" noValidate>
              <FormField
                control={form.control}
                name="produto"
                render={({ field, fieldState }) => (
                  <FormItem>
                    <FormLabel>Produto</FormLabel>
                    <FormControl>
                      <ProdutoCombobox value={field.value} onChange={field.onChange} invalid={!!fieldState.error} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="cliente"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cliente</FormLabel>
                    <FormControl>
                      <Input placeholder="Nome do cliente" autoComplete="off" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="quantidade"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Quantidade</FormLabel>
                      <FormControl>
                        <Input type="number" inputMode="numeric" min={1} placeholder="0" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="urgencia"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Urgência</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {Object.entries(URGENCIA).map(([valor, rotulo]) => (
                            <SelectItem key={valor} value={valor}>
                              {rotulo}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="observacao"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Observação (opcional)</FormLabel>
                    <FormControl>
                      <Textarea rows={2} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={lancar.isPending}>
                  {lancar.isPending && <Spinner />} Lançar
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={duplicata !== null} onOpenChange={(o) => !o && setDuplicata(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Item já lançado hoje</AlertDialogTitle>
            <AlertDialogDescription>{duplicata?.mensagem} Deseja somar esta quantidade à demanda?</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault()
                if (duplicata) enviar(duplicata.dados, true)
              }}
            >
              Somar quantidade
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
