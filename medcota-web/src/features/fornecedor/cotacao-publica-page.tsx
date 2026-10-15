import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery } from "@tanstack/react-query"
import { CheckCircle2Icon, LinkIcon } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useFieldArray, useForm } from "react-hook-form"
import { useParams } from "react-router"
import { toast } from "sonner"
import { z } from "zod"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { ApiError, mensagemDeErro, request } from "@/lib/api"
import { dataHora, numeroBR } from "@/lib/format"
import { PAGAMENTO } from "@/lib/labels"
import type { CotacaoPublica, RespostaIn } from "@/lib/types"

// ---- validação -------------------------------------------------------------
// Uma linha só é enviada se o preço foi preenchido; aí todos os campos passam a ser obrigatórios.
const linhaSchema = z
  .object({
    item_id: z.number(),
    preco: z.string(),
    quantidade: z.string(),
    prazo_dias: z.string(),
    pagamento: z.enum(["a_vista", "15d", "30d", "45d"]),
    lote: z.string().max(40, "Máximo de 40 caracteres"),
  })
  .superRefine((v, ctx) => {
    if (!v.preco.trim()) return
    const erro = (path: string, message: string) => ctx.addIssue({ code: z.ZodIssueCode.custom, path: [path], message })

    if (!/^\d+([.,]\d{1,4})?$/.test(v.preco.trim()) || numeroBR(v.preco) <= 0) erro("preco", "Preço inválido (até 4 casas)")
    const qtd = Number(v.quantidade)
    if (!Number.isInteger(qtd) || qtd <= 0 || qtd > 1_000_000) erro("quantidade", "Quantidade inválida")
    const prazo = Number(v.prazo_dias)
    if (!Number.isInteger(prazo) || prazo < 1 || prazo > 365) erro("prazo_dias", "Prazo de 1 a 365 dias")
  })

const schema = z.object({ itens: z.array(linhaSchema) }).refine((v) => v.itens.some((i) => i.preco.trim() !== ""), {
  message: "Informe o preço de ao menos um item.",
  path: ["itens"],
})
type Valores = z.infer<typeof schema>

function paraPayload(v: Valores): RespostaIn[] {
  return v.itens
    .filter((i) => i.preco.trim() !== "")
    .map((i) => ({
      item_id: i.item_id,
      preco: i.preco.trim().replace(",", "."),
      quantidade: Number(i.quantidade),
      prazo_dias: Number(i.prazo_dias),
      pagamento: i.pagamento,
      lote: i.lote.trim(),
    }))
}

// ---- página ----------------------------------------------------------------
function Moldura({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-svh">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-3xl items-center px-4 font-semibold tracking-tight">MedCota</div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">{children}</main>
    </div>
  )
}

export function Component() {
  const { token = "" } = useParams()
  const registrouAbertura = useRef(false)

  const { data, isPending, error, refetch } = useQuery({
    queryKey: ["cotacao-publica", token],
    queryFn: ({ signal }) => request<CotacaoPublica>(`/c/${encodeURIComponent(token)}`, { auth: false, signal }),
    retry: false,
    staleTime: Infinity,
  })

  // RF-17: conta a abertura uma única vez (o GET é somente leitura)
  useEffect(() => {
    if (data && !registrouAbertura.current) {
      registrouAbertura.current = true
      void request(`/c/${encodeURIComponent(token)}/abertura`, { method: "POST", auth: false }).catch(() => {})
    }
  }, [data, token])

  if (isPending) {
    return (
      <Moldura>
        <TableSkeleton rows={4} />
      </Moldura>
    )
  }

  if (error) {
    const link = error instanceof ApiError && (error.status === 404 || error.status === 410)
    return (
      <Moldura>
        {link ? (
          <EmptyState
            title={error.status === 410 ? "Este link expirou" : "Link inválido"}
            description={
              error.status === 410
                ? "Solicite um novo envio ao comprador."
                : "Confira se o endereço foi copiado por inteiro."
            }
          />
        ) : (
          <ErrorState error={error} onRetry={() => void refetch()} />
        )}
      </Moldura>
    )
  }

  return (
    <Moldura>
      <div className="mb-6 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Cotação — {data.fornecedor}</h1>
        <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <LinkIcon className="size-4" /> Responda até {dataHora(data.expira_em)}
          {data.rodada > 1 && <Badge variant="secondary">{data.rodada}ª rodada</Badge>}
        </p>
      </div>
      <FormularioResposta cotacao={data} token={token} />
    </Moldura>
  )
}

function FormularioResposta({ cotacao, token }: { cotacao: CotacaoPublica; token: string }) {
  const [enviado, setEnviado] = useState(false)

  const form = useForm<Valores>({
    resolver: zodResolver(schema),
    defaultValues: {
      itens: cotacao.itens.map((i) => ({
        item_id: i.item_id,
        preco: "",
        quantidade: String(i.demanda),
        prazo_dias: "",
        pagamento: "a_vista" as const,
        lote: "",
      })),
    },
  })
  const { fields } = useFieldArray({ control: form.control, name: "itens" })

  const enviar = useMutation({
    mutationFn: (payload: RespostaIn[]) =>
      request<void>(`/c/${encodeURIComponent(token)}/responder`, { method: "POST", body: payload, auth: false }),
    onSuccess: () => setEnviado(true),
    onError: (e) => toast.error(mensagemDeErro(e)),
  })

  if (enviado) {
    return (
      <Card>
        <CardHeader className="items-center text-center">
          <CheckCircle2Icon className="size-10 text-success" aria-hidden />
          <CardTitle>Resposta enviada</CardTitle>
          <CardDescription>Obrigado! O comprador já pode ver suas ofertas.</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Button variant="outline" onClick={() => setEnviado(false)}>
            Revisar ou corrigir respostas
          </Button>
        </CardContent>
      </Card>
    )
  }

  const erroGeral = form.formState.errors.itens?.root?.message ?? form.formState.errors.itens?.message

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((v) => enviar.mutate(paraPayload(v)))} className="space-y-4" noValidate>
        {fields.map((campo, i) => {
          const item = cotacao.itens[i]!
          return (
            <Card key={campo.id}>
              <CardHeader>
                <CardTitle className="text-base">{item.produto}</CardTitle>
                <CardDescription>
                  {item.ean ? `EAN ${item.ean} · ` : ""}Demanda: {item.demanda} un
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <FormField
                  control={form.control}
                  name={`itens.${i}.preco`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Preço unitário (R$)</FormLabel>
                      <FormControl>
                        <Input inputMode="decimal" placeholder="0,00" {...field} />
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
                      <FormLabel>Qtd disponível</FormLabel>
                      <FormControl>
                        <Input inputMode="numeric" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name={`itens.${i}.prazo_dias`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Prazo (dias)</FormLabel>
                      <FormControl>
                        <Input inputMode="numeric" placeholder="3" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name={`itens.${i}.pagamento`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Pagamento</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {Object.entries(PAGAMENTO).map(([valor, rotulo]) => (
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
              </CardContent>
            </Card>
          )
        })}

        {erroGeral && (
          <p role="alert" className="text-sm text-destructive">
            {erroGeral}
          </p>
        )}
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">Deixe o preço em branco nos itens que você não fornece.</p>
          <Button type="submit" disabled={enviar.isPending}>
            {enviar.isPending && <Spinner />} Enviar resposta
          </Button>
        </div>
      </form>
    </Form>
  )
}
