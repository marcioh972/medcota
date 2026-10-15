import { zodResolver } from "@hookform/resolvers/zod"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { cnpjValido, formatarCnpj, normalizarCnpj } from "@/lib/cnpj"
import { aplicarErroDaApi } from "@/lib/form-errors"
import type { Fornecedor } from "@/lib/types"

import { useAtualizarFornecedor, useCriarFornecedor } from "./api"

const schema = z.object({
  nome: z.string().trim().min(2, "Informe o nome").max(150, "Máximo de 150 caracteres"),
  escopo: z.enum(["Local", "Nacional"]),
  email: z.string().trim().refine((v) => v === "" || z.string().email().safeParse(v).success, "E-mail inválido"),
  cnpj: z.string().trim().refine((v) => v === "" || cnpjValido(v), "CNPJ inválido"),
  credenciado_72101: z.boolean(),
})
type Valores = z.infer<typeof schema>

const VAZIO: Valores = { nome: "", escopo: "Nacional", email: "", cnpj: "", credenciado_72101: false }
const CAMPOS_API = ["nome", "escopo", "email", "cnpj", "credenciado_72101"] as const

interface Props {
  open: boolean
  onOpenChange: (o: boolean) => void
  /** Quando informado, o diálogo edita CNPJ, e-mail e credenciamento deste fornecedor. */
  fornecedor?: Fornecedor
}

export function FornecedorDialog({ open, onOpenChange, fornecedor }: Props) {
  const editando = fornecedor !== undefined
  const form = useForm<Valores>({ resolver: zodResolver(schema), defaultValues: VAZIO })
  const criar = useCriarFornecedor()
  const atualizar = useAtualizarFornecedor()
  const pendente = criar.isPending || atualizar.isPending

  useEffect(() => {
    if (open) {
      form.reset(
        fornecedor
          ? {
              nome: fornecedor.nome,
              escopo: fornecedor.escopo,
              email: fornecedor.email,
              cnpj: fornecedor.cnpj ? formatarCnpj(fornecedor.cnpj) : "",
              credenciado_72101: fornecedor.credenciado_72101,
            }
          : VAZIO,
      )
    }
  }, [open, fornecedor, form])

  function concluir(mensagem: string) {
    toast.success(mensagem)
    onOpenChange(false)
  }

  function aoSubmeter(v: Valores) {
    const cnpj = v.cnpj ? normalizarCnpj(v.cnpj) : undefined
    if (fornecedor) {
      atualizar.mutate(
        { id: fornecedor.id, cnpj: cnpj ?? null, email: v.email || null, credenciado_72101: v.credenciado_72101 },
        { onSuccess: () => concluir("Fornecedor atualizado"), onError: (e) => aplicarErroDaApi(form, e, CAMPOS_API) },
      )
      return
    }
    criar.mutate(
      { nome: v.nome, escopo: v.escopo, email: v.email || undefined, cnpj, credenciado_72101: v.credenciado_72101 },
      { onSuccess: () => concluir("Fornecedor cadastrado"), onError: (e) => aplicarErroDaApi(form, e, CAMPOS_API) },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{editando ? `Editar ${fornecedor.nome}` : "Novo fornecedor"}</DialogTitle>
          <DialogDescription>
            {editando
              ? "O CNPJ permite conferir o emitente das notas fiscais deste fornecedor."
              : "Recebe a lista de cotação dos produtos do mesmo escopo (Local ou Nacional)."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(aoSubmeter)} className="space-y-4" noValidate>
            {form.formState.errors.root && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{form.formState.errors.root.message}</AlertDescription>
              </Alert>
            )}
            {!editando && (
              <>
                <FormField control={form.control} name="nome" render={({ field }) => (
                  <FormItem><FormLabel>Nome</FormLabel><FormControl><Input autoFocus {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="escopo" render={({ field }) => (
                  <FormItem><FormLabel>Escopo</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl><SelectTrigger className="w-full"><SelectValue /></SelectTrigger></FormControl>
                      <SelectContent><SelectItem value="Local">Local</SelectItem><SelectItem value="Nacional">Nacional</SelectItem></SelectContent>
                    </Select>
                    <FormDescription>Fornecedor Local cota produtos de origem Local; Nacional, os de origem Nacional.</FormDescription>
                    <FormMessage /></FormItem>
                )} />
              </>
            )}
            <FormField control={form.control} name="cnpj" render={({ field }) => (
              <FormItem><FormLabel>CNPJ (opcional)</FormLabel><FormControl><Input placeholder="00.000.000/0000-00" autoComplete="off" {...field} /></FormControl>
                <FormDescription>Aceita CNPJ numérico e alfanumérico. Único por empresa.</FormDescription><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="email" render={({ field }) => (
              <FormItem><FormLabel>E-mail (opcional)</FormLabel><FormControl><Input type="email" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="credenciado_72101" render={({ field }) => (
              <FormItem className="flex items-center justify-between gap-4 rounded-md border p-3">
                <div>
                  <FormLabel>Atacadista credenciado (Decreto AL 72.101/2020)</FormLabel>
                  <FormDescription>Informe só se o credenciamento foi confirmado na SEFAZ-AL.</FormDescription>
                </div>
                <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
              <Button type="submit" disabled={pendente}>{pendente && <Spinner />} Salvar</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
