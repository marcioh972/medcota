import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useForm, useWatch } from "react-hook-form"
import { Link, Navigate, useNavigate, useSearchParams } from "react-router"
import { toast } from "sonner"
import { z } from "zod"

import { SenhaChecklist, SenhaInput } from "@/components/senha-input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { request } from "@/lib/api"
import { aplicarErroDaApi } from "@/lib/form-errors"
import type { CadastroFuncionarioIn, LoginOut } from "@/lib/types"

import { AuthShell } from "./auth-shell"
import { senhaSchema } from "./senha-schema"
import { homeDoPerfil } from "./session"
import { useAuth } from "./use-auth"

const schema = z
  .object({
    codigo: z
      .string()
      .trim()
      .min(1, "Informe o código da empresa")
      .refine((c) => c.replace(/[\s-]/g, "").length === 12, "O código tem 12 caracteres (ex.: ABCD-EFGH-JKLM)"),
    perfil: z.enum(["vendedor", "comprador"], { message: "Escolha o seu perfil" }),
    nome: z.string().trim().min(2, "Informe seu nome").max(150, "Máximo de 150 caracteres"),
    email: z.string().trim().min(1, "Informe o e-mail").email("E-mail inválido"),
    senha: senhaSchema,
    confirmar: z.string(),
  })
  .refine((v) => v.senha === v.confirmar, { path: ["confirmar"], message: "As senhas não conferem" })
type Valores = z.infer<typeof schema>

const CAMPOS_API = ["codigo", "perfil", "nome", "email", "senha"] as const

export function Component() {
  const { session, iniciarSessao } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const form = useForm<Valores>({
    resolver: zodResolver(schema),
    // aceita ?codigo=ABCD-EFGH-JKLM para o gestor compartilhar um link pronto
    defaultValues: { codigo: params.get("codigo") ?? "", perfil: undefined, nome: "", email: "", senha: "", confirmar: "" },
  })

  const cadastrar = useMutation({
    mutationFn: (dados: CadastroFuncionarioIn) =>
      request<LoginOut>("/cadastro/funcionario", { method: "POST", body: dados, auth: false }),
    onSuccess: (r) => {
      const s = iniciarSessao(r)
      toast.success(`Bem-vindo(a) à ${r.empresa}!`)
      void navigate(homeDoPerfil(s.perfil), { replace: true })
    },
    onError: (e) => aplicarErroDaApi(form, e, CAMPOS_API),
  })

  const senha = useWatch({ control: form.control, name: "senha" })

  // já logado (ex.: abriu a página por link) vai para a própria tela; após o cadastro, quem navega é o onSuccess
  if (session && !cadastrar.isSuccess) return <Navigate to={homeDoPerfil(session.perfil)} replace />


  return (
    <AuthShell
      wide
      title="Cadastro de funcionário"
      description="Peça ao gestor da sua empresa o código de validação e crie a sua senha."
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
            cadastrar.mutate({ ...v, codigo: v.codigo.trim().toUpperCase() }),
          )}
          className="space-y-4"
          noValidate
        >
          {form.formState.errors.root && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{form.formState.errors.root.message}</AlertDescription>
            </Alert>
          )}

          <FormField
            control={form.control}
            name="codigo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Código de validação</FormLabel>
                <FormControl>
                  <Input
                    placeholder="ABCD-EFGH-JKLM"
                    autoComplete="off"
                    autoCapitalize="characters"
                    spellCheck={false}
                    className="font-mono uppercase tracking-wider"
                    autoFocus
                    {...field}
                  />
                </FormControl>
                <FormDescription>Fornecido pelo gestor da empresa. Cada empresa tem o seu.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="perfil"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Perfil</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Selecione" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="vendedor">Vendedor</SelectItem>
                    <SelectItem value="comprador">Comprador</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="nome"
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

          <Button type="submit" className="w-full" disabled={cadastrar.isPending}>
            {cadastrar.isPending && <Spinner />} Criar conta
          </Button>
        </form>
      </Form>
    </AuthShell>
  )
}
