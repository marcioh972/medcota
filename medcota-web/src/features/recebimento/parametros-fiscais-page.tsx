import { zodResolver } from "@hookform/resolvers/zod"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { Link } from "react-router"
import { toast } from "sonner"
import { z } from "zod"

import { ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { useAuth } from "@/features/auth/use-auth"
import { aplicarErroDaApi } from "@/lib/form-errors"
import { dataHora, numeroBR } from "@/lib/format"
import type { ConfiguracaoFiscal } from "@/lib/types"

import { useConfiguracaoFiscal, useSalvarConfiguracaoFiscal } from "./api"

const percentual = (vazioPermitido: boolean) =>
  z
    .string()
    .trim()
    .refine((v) => (vazioPermitido && v === "") || /^\d+([.,]\d{1,2})?$/.test(v), "Use um número com até 2 casas")
    .refine((v) => v === "" || (numeroBR(v) >= 0 && numeroBR(v) <= 100), "Entre 0 e 100")

const separar = (texto: string) => texto.split(/[\s,;]+/).filter(Boolean)

const schema = z.object({
  aliquota_interna_icms: percentual(true),
  tolerancia_preco_pct: percentual(false),
  municipios: z.string().refine((t) => separar(t).every((m) => /^\d{7}$/.test(m)), "Cada código IBGE tem 7 dígitos"),
  exigir_protocolo: z.boolean(),
})
type Valores = z.infer<typeof schema>

const paraFormulario = (c: ConfiguracaoFiscal): Valores => ({
  aliquota_interna_icms: c.aliquota_interna_icms ?? "",
  tolerancia_preco_pct: c.tolerancia_preco_pct,
  municipios: c.frete_zero_municipios.join(", "),
  exigir_protocolo: c.exigir_protocolo,
})

export function Component() {
  const { session } = useAuth()
  const ehGestor = session?.perfil === "gestor"
  const { data, isPending, error, refetch } = useConfiguracaoFiscal()
  const salvar = useSalvarConfiguracaoFiscal()
  const form = useForm<Valores>({
    resolver: zodResolver(schema),
    defaultValues: { aliquota_interna_icms: "", tolerancia_preco_pct: "0", municipios: "", exigir_protocolo: true },
  })

  useEffect(() => {
    if (data) form.reset(paraFormulario(data))
  }, [data, form])

  if (isPending) return <TableSkeleton rows={3} />
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />

  function aoSubmeter(v: Valores) {
    salvar.mutate(
      {
        aliquota_interna_icms: v.aliquota_interna_icms === "" ? null : v.aliquota_interna_icms.replace(",", "."),
        tolerancia_preco_pct: v.tolerancia_preco_pct.replace(",", "."),
        frete_zero_municipios: separar(v.municipios),
        exigir_protocolo: v.exigir_protocolo,
      },
      {
        onSuccess: () => toast.success("Parâmetros fiscais salvos. Reanalise as notas pendentes para aplicá-los."),
        onError: (e) => aplicarErroDaApi(form, e, ["aliquota_interna_icms", "tolerancia_preco_pct", "frete_zero_municipios", "exigir_protocolo"]),
      },
    )
  }

  return (
    <>
      <PageHeader
        title="Parâmetros fiscais"
        description="Valores usados na conferência das notas fiscais da sua empresa."
        actions={
          <Button variant="outline" asChild>
            <Link to="/recebimento">Voltar</Link>
          </Button>
        }
      />

      <Alert className="mb-6">
        <AlertTitle>Sobre o Decreto nº 72.101/2020 (Alagoas)</AlertTitle>
        <AlertDescription>
          O decreto concede tratamento tributário diferenciado de ICMS a atacadistas credenciados de medicamentos. O ICMS
          recolhido nesse regime é apurado mensalmente pelo fornecedor e não aparece na nota, então o sistema confere o que
          está destacado nela (ICMS, ICMS-ST, FCP, PIS/COFINS, totais). As alíquotas dependem da legislação vigente: informe-as
          com seu contador. A conferência é um apoio e não substitui a análise contábil.
        </AlertDescription>
      </Alert>

      {!ehGestor && (
        <Alert className="mb-6">
          <AlertDescription>Somente o gestor pode alterar os parâmetros. Você está vendo os valores atuais.</AlertDescription>
        </Alert>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(aoSubmeter)} className="space-y-6" noValidate>
          {form.formState.errors.root && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{form.formState.errors.root.message}</AlertDescription>
            </Alert>
          )}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">ICMS e preços</CardTitle>
              <CardDescription>Sem alíquota interna configurada, as operações dentro do estado não têm a alíquota validada.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="aliquota_interna_icms"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Alíquota interna de ICMS (%)</FormLabel>
                    <FormControl>
                      <Input inputMode="decimal" placeholder="não validar" disabled={!ehGestor} {...field} />
                    </FormControl>
                    <FormDescription>Deixe em branco para não validar.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="tolerancia_preco_pct"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tolerância de preço (%)</FormLabel>
                    <FormControl>
                      <Input inputMode="decimal" disabled={!ehGestor} {...field} />
                    </FormControl>
                    <FormDescription>Diferença aceita entre o preço do pedido e o da nota.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Frete</CardTitle>
              <CardDescription>Fornecedores destes municípios não cobram frete na nota; frete cobrado vira erro.</CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="municipios"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Códigos IBGE dos municípios sem frete</FormLabel>
                    <FormControl>
                      <Textarea rows={2} disabled={!ehGestor} {...field} />
                    </FormControl>
                    <FormDescription>Separe por vírgula. Padrão: 2704302 (Maceió/AL). Vazio desliga a regra.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <FormField
                control={form.control}
                name="exigir_protocolo"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between gap-4">
                    <div>
                      <FormLabel>Exigir protocolo de autorização</FormLabel>
                      <FormDescription>XML sem o protocolo da SEFAZ vira erro (em vez de alerta).</FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} disabled={!ehGestor} />
                    </FormControl>
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground">
              {data.atualizada_em ? `Atualizado em ${dataHora(data.atualizada_em)}` : "Usando os valores padrão."}
            </p>
            {ehGestor && (
              <Button type="submit" disabled={salvar.isPending}>
                {salvar.isPending && <Spinner />} Salvar parâmetros
              </Button>
            )}
          </div>
        </form>
      </Form>
    </>
  )
}
