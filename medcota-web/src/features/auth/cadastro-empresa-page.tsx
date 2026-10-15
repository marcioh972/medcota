import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useForm, useWatch } from "react-hook-form"
import { Link, Navigate, useNavigate } from "react-router"
import { toast } from "sonner"
import { z } from "zod"

import { SenhaChecklist, SenhaInput } from "@/components/senha-input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { request } from "@/lib/api"
import { cnpjValido, normalizarCnpj } from "@/lib/cnpj"
import { aplicarErroDaApi } from "@/lib/form-errors"
import type { CadastroEmpresaIn, LoginOut } from "@/lib/types"

import { AuthShell } from "./auth-shell"
import { senhaSchema } from "./senha-schema"
import { homeDoPerfil } from "./session"
import { useAuth } from "./use-auth"

const schema = z
  .object({
    empresa_nome: z.string().trim().min(2, "Informe o nome da empresa").max(150, "Máximo de 150 caracteres"),
    cnpj: z.string().refine(cnpjValido, "CNPJ inválido"),
    gestor_nome: z.string().trim().min(2, "Informe seu nome").max(150, "Máximo de 150 caracteres"),
    email: z.string().trim().min(1, "Informe o e-mail").email("E-mail inválido"),
    senha: senhaSchema,
    confirmar: z.string(),
  })
  .refine((v) => v.senha === v.confirmar, { path: ["confirmar"], message: "As senhas não conferem" })
type Valores = z.infer<typeof schema>

const CAMPOS_API = ["empresa_nome", "cnpj", "gestor_nome", "email", "senha"] as const

export function Component() {
  const { session, iniciarSessao } = useAuth()
  const navigate = useNavigate()
  const form = useForm<Valores>({
    resolver: zodResolver(schema),
    defaultValues: { empresa_nome: "", cnpj: "", gestor_nome: "", email: "", senha: "", confirmar: "" },
  })

  const cadastrar = useMutation({
    mutationFn: (dados: CadastroEmpresaIn) =>
      request<LoginOut>("/cadastro/empresa", { method: "POST", body: dados, auth: false }),
    onSuccess: (r) => {
      iniciarSessao(r)
      toast.success("Empresa cadastrada! Gere o código de validação para convidar sua equipe.")
      void navigate("/equipe", { replace: true })
    },
    onError: (e) => aplicarErroDaApi(form, e, CAMPOS_API),
  })

  const senha = useWatch({ control: form.control, name: "senha" })

  // já logado (ex.: abriu a página por link) vai para a própria tela; após o cadastro, quem navega é o onSuccess
  if (session && !cadastrar.isSuccess) return <Navigate to={homeDoPerfil(session.perfil)} replace />


  return (
    <AuthShell
      wide
      title="Cadastrar empresa"
      description="Você será o gestor da empresa. Depois, gere o código para os funcionários se cadastrarem."
      footer={
        <p>
          Já tem conta?{" "}
          <Link to="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
            Entrar
          </Link>
        </p>
      }
    >
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(({ confirmar: _c, ...v }) =>
            cadastrar.mutate({ ...v, cnpj: normalizarCnpj(v.cnpj) }),
          )}
          className="space-y-4"
          noValidate
        >
          {form.formState.errors.root && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{form.formState.errors.root.message}</AlertDescription>
            </Alert>
          )}

          <fieldset className="space-y-4">
            <legend className="mb-2 text-sm font-medium">Empresa</legend>
            <FormField
              control={form.control}
              name="empresa_nome"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome da empresa</FormLabel>
                  <FormControl>
                    <Input autoComplete="organization" autoFocus {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="cnpj"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>CNPJ</FormLabel>
                  <FormControl>
                    <Input inputMode="text" placeholder="00.000.000/0000-00" autoComplete="off" {...field} />
                  </FormControl>
                  <FormDescription>Aceita o CNPJ numérico e o alfanumérico.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </fieldset>

          <fieldset className="space-y-4">
            <legend className="mb-2 text-sm font-medium">Gestor</legend>
            <FormField
              control={form.control}
              name="gestor_nome"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Seu nome</FormLabel>
                  <FormControl>
                    <Input autoComplete="name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>E-mail</FormLabel>
                  <FormControl>
                    <Input type="email" autoComplete="username" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="senha"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Crie sua senha</FormLabel>
                  <FormControl>
                    <SenhaInput autoComplete="new-password" {...field} />
                  </FormControl>
                  <SenhaChecklist senha={senha} />
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirmar"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirme a senha</FormLabel>
                  <FormControl>
                    <SenhaInput autoComplete="new-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </fieldset>

          <Button type="submit" className="w-full" disabled={cadastrar.isPending}>
            {cadastrar.isPending && <Spinner />} Cadastrar empresa
          </Button>
        </form>
      </Form>
    </AuthShell>
  )
}
