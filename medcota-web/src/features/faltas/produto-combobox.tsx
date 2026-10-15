import { CheckIcon, ChevronsUpDownIcon } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { useDebounce } from "@/hooks/use-debounce"
import type { Produto } from "@/lib/types"

import { useBuscaProdutos } from "./api"

interface Props {
  value: Produto | null
  onChange: (produto: Produto) => void
  id?: string
  invalid?: boolean
}

/** Combobox do shadcn com busca no servidor (nome, princípio ativo ou EAN). */
export function ProdutoCombobox({ value, onChange, id, invalid }: Props) {
  const [open, setOpen] = useState(false)
  const [busca, setBusca] = useState("")
  const termo = useDebounce(busca.trim(), 250)
  const { data, isFetching, isError } = useBuscaProdutos(termo, open)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-invalid={invalid}
          className="w-full justify-between font-normal"
        >
          <span className="truncate">{value ? value.nome : "Buscar produto…"}</span>
          <ChevronsUpDownIcon className="opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Nome, princípio ativo ou EAN" value={busca} onValueChange={setBusca} />
          <CommandList>
            <CommandEmpty>
              {isError ? "Erro ao buscar produtos." : isFetching ? "Buscando…" : "Nenhum produto encontrado."}
            </CommandEmpty>
            <CommandGroup>
              {data?.map((p) => (
                <CommandItem
                  key={p.id}
                  value={String(p.id)}
                  onSelect={() => {
                    onChange(p)
                    setOpen(false)
                  }}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate">{p.nome}</p>
                    <p className="text-xs text-muted-foreground">
                      {p.ean ?? "sem EAN"} · {p.origem}
                    </p>
                  </div>
                  {value?.id === p.id && <CheckIcon className="size-4" />}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
