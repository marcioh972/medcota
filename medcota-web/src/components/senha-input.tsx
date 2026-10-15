import { CheckIcon, EyeIcon, EyeOffIcon, XIcon } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { requisitosDaSenha } from "@/lib/password"
import { cn } from "@/lib/utils"

/** Campo de senha com botão de mostrar/ocultar. Repassa todas as props ao <Input> (compatível com FormControl). */
export function SenhaInput({ className, ...props }: React.ComponentProps<"input">) {
  const [visivel, setVisivel] = useState(false)
  return (
    <div className="relative">
      <Input {...props} type={visivel ? "text" : "password"} className={cn("pr-10", className)} />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute right-0 top-0 size-9 text-muted-foreground"
        aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
        aria-pressed={visivel}
        onClick={() => setVisivel((v) => !v)}
      >
        {visivel ? <EyeOffIcon /> : <EyeIcon />}
      </Button>
    </div>
  )
}

/** Checklist ao vivo da política de senha (8+ caracteres, maiúscula, minúscula e número). */
export function SenhaChecklist({ senha }: { senha: string }) {
  return (
    <ul aria-label="Requisitos da senha" className="grid gap-1 text-xs sm:grid-cols-2">
      {requisitosDaSenha(senha).map((r) => (
        <li key={r.id} className={cn("flex items-center gap-1.5", r.ok ? "text-success" : "text-muted-foreground")}>
          {r.ok ? <CheckIcon className="size-3.5" aria-hidden /> : <XIcon className="size-3.5" aria-hidden />}
          <span>{r.texto}</span>
          <span className="sr-only">{r.ok ? "atendido" : "pendente"}</span>
        </li>
      ))}
    </ul>
  )
}
