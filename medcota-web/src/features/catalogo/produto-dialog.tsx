import { zodResolver } from "@hookform/resolvers/zod"
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
import { aplicarErroDaApi } from "@/lib/form-errors"

import { useCriarProduto } from "./api"

const schema = z.object({
  nome: z.string().trim().min(2, "Informe o nome").max(200, "Máximo de 200 caracteres"),
  principio_ativo: z.string().trim().max(200, "Máximo de 200 caracteres"),
  ean: z.string().trim().refine((v) => v === "" || /^\d{8,13}$/.test(v), "O EAN tem de 8 a 13 dígitos"),
  classe: z.enum(["Farma", "Hospitalar"]),
  origem: z.enum(["Local", "Nacional"]),
  controlado: z.boolean(),
})
type Valores = z.infer<typeof schema>

const VAZIO: Valores = { nome: "", principio_ativo: "", ean: "", classe: "Farma", origem: "Local", controlado: false }
const CAMPOS_API = ["nome", "principio_ativo", "ean", "classe", "origem", "controlado"] as const

export function ProdutoDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const form = useForm<Valores>({ resolver: zodResolver(schema), defaultValues: VAZIO })
  const criar = useCriarProduto()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Novo produto</DialogTitle>
          <DialogDescription>Fica disponível para o lançamento de faltas da sua empresa.</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((v) =>
              criar.mutate(
                { ...v, principio_ativo: v.principio_ativo || undefined, ean: v.ean || undefined },
                {
                  onSuccess: () => {
                    toast.success("Produto cadastrado")
                    form.reset(VAZIO)
                    onOpenChange(false)
                  },
                  onError: (e) => aplicarErroDaApi(form, e, CAMPOS_API),
                },
              ),
            )}
            className="space-y-4"
            noValidate
          >
            {form.formState.errors.root && (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{form.formState.errors.root.message}</AlertDescription>
              </Alert>
            )}
            <FormField control={form.control} name="nome" render={({ field }) => (
              <FormItem><FormLabel>Nome</FormLabel><FormControl><Input autoFocus placeholder="Dipirona 500mg · 20 comp" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="principio_ativo" render={({ field }) => (
              <FormItem><FormLabel>Princípio ativo (opcional)</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="ean" render={({ field }) => (
              <FormItem><FormLabel>EAN (opcional)</FormLabel><FormControl><Input inputMode="numeric" {...field} /></FormControl><FormDescription>Único dentro da sua empresa.</FormDescription><FormMessage /></FormItem>
            )} />
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField control={form.control} name="classe" render={({ field }) => (
                <FormItem><FormLabel>Classe</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl><SelectTrigger className="w-full"><SelectValue /></SelectTrigger></FormControl>
                    <SelectContent><SelectItem value="Farma">Farma</SelectItem><SelectItem value="Hospitalar">Hospitalar</SelectItem></SelectContent>
                  </Select><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="origem" render={({ field }) => (
                <FormItem><FormLabel>Origem</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl><SelectTrigger className="w-full"><SelectValue /></SelectTrigger></FormControl>
                    <SelectContent><SelectItem value="Local">Local</SelectItem><SelectItem value="Nacional">Nacional</SelectItem></SelectContent>
                  </Select><FormMessage /></FormItem>
              )} />
            </div>
            <FormField control={form.control} name="controlado" render={({ field }) => (
              <FormItem className="flex items-center justify-between rounded-md border p-3">
                <div><FormLabel>Medicamento controlado</FormLabel><FormDescription>Portaria 344/98.</FormDescription></div>
                <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
              <Button type="submit" disabled={criar.isPending}>{criar.isPending && <Spinner />} Salvar</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
