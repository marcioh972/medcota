import { zodResolver } from "@hookform/resolvers/zod"
import { PlusIcon, Trash2Icon } from "lucide-react"
import { useFieldArray, useForm, useWatch } from "react-hook-form"
import { Link, useNavigate } from "react-router"
import { toast } from "sonner"
import { z } from "zod"

import { PageHeader } from "@/components/page-header"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { useFornecedores } from "@/features/catalogo/api"
import { ProdutoCombobox } from "@/features/faltas/produto-combobox"
import { aplicarErroDaApi } from "@/lib/form-errors"
import { moeda, numeroBR } from "@/lib/format"
import type { PedidoManualIn, Produto } from "@/lib/types"

import { useRegistrarPedido } from "./api"

const linha = z.object({
  produto: z.custom<Produto | null>().refine((p): boolean => p !== null && p !== undefined, "Selecione o produto"),
  quantidade: z
    .string()
    .trim()
    .regex(/^\d+$/, "Use um número inteiro")
    .refine((v) => Number(v) > 0 && Number(v) <= 1_000_000, "Entre 1 e 1.000.000"),
  preco: z
    .string()
    .trim()
    .regex(/^\d+([.,]\d{1,4})?$/, "Preço inválido (até 4 casas decimais)")
    .refine((v) => numeroBR(v) > 0, "Deve ser maior que zero"),
})

const schema = z
  .object({
    fornecedor_id: z.string().min(1, "Escolha o fornecedor"),
    numero_externo: z.string().trim().max(40, "Máximo de 40 caracteres"),
    frete_previsto: z.string().trim().regex(/^\d+([.,]\d{1,2})?$/, "Valor inválido (até 2 casas decimais)"),
    observacao: z.string().max(500, "Máximo de 500 caracteres"),
    itens: z.array(linha).min(1, "Adicione ao menos um item"),
  })
  .superRefine((v, ctx) => {
    const vistos = new Set<number>()
    v.itens.forEach((it, i) => {
      const id = it.produto?.id
      if (id === undefined) return
      if (vistos.has(id)) ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["itens", i, "produto"], message: "Produto repetido: some as quantidades" })
      vistos.add(id)
    })
  })
type Valores = z.infer<typeof schema>

const CAMPOS_API = ["fornecedor_id", "itens", "frete_previsto", "numero_externo", "observacao"] as const
const LINHA_VAZIA = { produto: null as unknown as Produto, quantidade: "", preco: "" }

export function Component() {
  const navigate = useNavigate()
  const { data: fornecedores, isPending: carregandoFornecedores } = useFornecedores()
  const registrar = useRegistrarPedido()
  const form = useForm<Valores>({
    resolver: zodResolver(schema),
    defaultValues: { fornecedor_id: "", numero_externo: "", frete_previsto: "0", observacao: "", itens: [LINHA_VAZIA] },
  })
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "itens" })
  const itens = useWatch({ control: form.control, name: "itens" })
  const frete = useWatch({ control: form.control, name: "frete_previsto" })

  // Pré-visualização apenas (o servidor calcula o total oficial).
  const subtotal = (itens ?? []).reduce((acc, it) => {
    const q = Number(it?.quantidade)
    const p = numeroBR(it?.preco ?? "")
    return acc + (Number.isFinite(q) && Number.isFinite(p) ? q * p : 0)
  }, 0)
  const total = subtotal + (Number.isFinite(numeroBR(frete ?? "")) ? numeroBR(frete) : 0)

  function aoSubmeter(v: Valores) {
    const dados: PedidoManualIn = {
      fornecedor_id: Number(v.fornecedor_id),
      itens: v.itens.map((i) => ({ produto_id: i.produto!.id, quantidade: Number(i.quantidade), preco: i.preco.replace(",", ".") })),
      frete_previsto: v.frete_previsto.replace(",", "."),
      ...(v.numero_externo ? { numero_externo: v.numero_externo } : {}),
      ...(v.observacao ? { observacao: v.observacao } : {}),
    }
    registrar.mutate(dados, {
      onSuccess: (pedido) => {
        toast.success(`Pedido #${pedido.id} registrado`)
        void navigate(`/recebimento/${pedido.id}`)
      },
      onError: (e) => aplicarErroDaApi(form, e, CAMPOS_API),
    })
  }

  return (
    <>
      <PageHeader title="Registrar pedido" description="Informe o que foi pedido ao fornecedor. A nota fiscal será conferida contra estes dados." />
      <Form {...form}>
        <form onSubmit={form.handleSubmit(aoSubmeter)} className="space-y-6" noValidate>
          {form.formState.errors.root && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{form.formState.errors.root.message}</AlertDescription>
            </Alert>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Fornecedor</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="fornecedor_id"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel>Fornecedor</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={carregandoFornecedores}>
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder={carregandoFornecedores ? "Carregando…" : "Selecione"} />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {fornecedores?.map((f) => (
                          <SelectItem key={f.id} value={String(f.id)}>
                            {f.nome}
                            {f.cnpj ? ` · ${f.cnpj}` : " · sem CNPJ"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>Cadastre o CNPJ do fornecedor em Cadastros para validar o emitente da nota.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="numero_externo"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nº do pedido no fornecedor (opcional)</FormLabel>
                    <FormControl>
                      <Input autoComplete="off" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="frete_previsto"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Frete previsto (R$)</FormLabel>
                    <FormControl>
                      <Input inputMode="decimal" {...field} />
                    </FormControl>
                    <FormDescription>Fornecedores de Maceió não cobram frete: deixe 0,00.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Itens</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {fields.map((campo, i) => (
                <div key={campo.id} className="grid gap-3 rounded-md border p-3 sm:grid-cols-[1fr_7rem_9rem_auto] sm:items-start">
                  <FormField
                    control={form.control}
                    name={`itens.${i}.produto`}
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
                    name={`itens.${i}.quantidade`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Quantidade</FormLabel>
                        <FormControl>
                          <Input inputMode="numeric" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`itens.${i}.preco`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Preço unit. (R$)</FormLabel>
                        <FormControl>
                          <Input inputMode="decimal" placeholder="0,00" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="sm:mt-6"
                    aria-label={`Remover item ${i + 1}`}
                    disabled={fields.length === 1}
                    onClick={() => remove(i)}
                  >
                    <Trash2Icon />
                  </Button>
                </div>
              ))}
              {typeof form.formState.errors.itens?.message === "string" && (
                <p role="alert" className="text-sm text-destructive">
                  {form.formState.errors.itens.message}
                </p>
              )}
              <Button type="button" variant="outline" onClick={() => append(LINHA_VAZIA)}>
                <PlusIcon /> Adicionar item
              </Button>
            </CardContent>
          </Card>

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

          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              Total estimado: <strong className="tabular-nums text-foreground">{moeda(String(total))}</strong>
            </p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" asChild>
                <Link to="/recebimento">Cancelar</Link>
              </Button>
              <Button type="submit" disabled={registrar.isPending}>
                {registrar.isPending && <Spinner />} Registrar pedido
              </Button>
            </div>
          </div>
        </form>
      </Form>
    </>
  )
}
