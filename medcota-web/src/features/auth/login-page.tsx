import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Link, Navigate, useLocation, useNavigate } from "react-router"
import { z } from "zod"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { mensagemDeErro } from "@/lib/api"

import { AuthShell } from "./auth-shell"
import { homeDoPerfil } from "./session"
import { useAuth } from "./use-auth"
import { SenhaInput } from "@/components/senha-input"

const schema = z.object({
  email: z.string().trim().min(1, "Informe o e-mail").email("E-mail inválido"),
  senha: z.string().min(1, "Informe a senha"),
})
type Valores = z.infer<typeof schema>

export function Component() {
  const { session, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const form = useForm<Valores>({ resolver: zodResolver(schema), defaultValues: { email: "", senha: "" } })

  if (session) return <Navigate to={homeDoPerfil(session.perfil)} replace />

  async function aoSubmeter({ email, senha }: Valores) {
    try {
      const s = await login(email, senha)
      const destino = (location.state as { from?: string } | null)?.from
      void navigate(destino ?? homeDoPerfil(s.perfil), { replace: true })
    } catch (e) {
      form.setError("root", { message: mensagemDeErro(e) })
    }
  }

  return (
    <AuthShell
      title="Entrar"
      description="Use o e-mail e a senha cadastrados."
      footer={
        <>
          <p>
            Tem um código da empresa?{" "}
            <Link to="/cadastro/funcionario" className="font-medium text-foreground underline-offset-4 hover:underline">
              Cadastre-se como funcionário
            </Link>
          </p>
          <p>
            Sua empresa ainda não usa o MedCota?{" "}
            <Link to="/cadastro/empresa" className="font-medium text-foreground underline-offset-4 hover:underline">
              Cadastrar empresa
            </Link>
          </p>
        </>
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(aoSubmeter)} className="space-y-4" noValidate>
          {form.formState.errors.root && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{form.formState.errors.root.message}</AlertDescription>
            </Alert>
          )}
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>E-mail</FormLabel>
                <FormControl>
                  <Input type="email" autoComplete="username" autoFocus {...field} />
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
                <FormLabel>Senha</FormLabel>
                <FormControl>
                  <SenhaInput autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting && <Spinner />} Entrar
          </Button>
        </form>
      </Form>
    </AuthShell>
  )
}
