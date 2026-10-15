import { PencilIcon, PlusIcon } from "lucide-react"
import { useState } from "react"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/data-states"
import { PageHeader } from "@/components/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatarCnpj } from "@/lib/cnpj"
import type { Fornecedor } from "@/lib/types"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { useFornecedores, useProdutos } from "./api"
import { FornecedorDialog } from "./fornecedor-dialog"
import { ProdutoDialog } from "./produto-dialog"

function Produtos() {
  const [aberto, setAberto] = useState(false)
  const { data, isPending, error, refetch } = useProdutos()
  const novo = (
    <Button onClick={() => setAberto(true)}>
      <PlusIcon /> Novo produto
    </Button>
  )
  return (
    <div className="space-y-4">
      <div className="flex justify-end">{novo}</div>
      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Nenhum produto cadastrado" description="Cadastre os produtos para os vendedores poderem lançar faltas." action={novo} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Produto</TableHead>
                <TableHead>EAN</TableHead>
                <TableHead>Classe</TableHead>
                <TableHead>Origem</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <p className="font-medium">{p.nome}</p>
                    {p.principio_ativo && <p className="text-xs text-muted-foreground">{p.principio_ativo}</p>}
                  </TableCell>
                  <TableCell className="tabular-nums">{p.ean ?? "—"}</TableCell>
                  <TableCell>{p.classe}</TableCell>
                  <TableCell><Badge variant="outline">{p.origem}</Badge></TableCell>
                  <TableCell>{p.controlado && <Badge variant="destructive">Controlado</Badge>}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <ProdutoDialog open={aberto} onOpenChange={setAberto} />
    </div>
  )
}

function Fornecedores() {
  const [aberto, setAberto] = useState(false)
  const [editando, setEditando] = useState<Fornecedor | undefined>()
  const { data, isPending, error, refetch } = useFornecedores()
  const abrirNovo = () => {
    setEditando(undefined)
    setAberto(true)
  }
  const novo = (
    <Button onClick={abrirNovo}>
      <PlusIcon /> Novo fornecedor
    </Button>
  )
  return (
    <div className="space-y-4">
      <div className="flex justify-end">{novo}</div>
      {isPending ? (
        <TableSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState title="Nenhum fornecedor cadastrado" description="Sem fornecedores não é possível gerar cotações." action={novo} />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fornecedor</TableHead>
                <TableHead>CNPJ</TableHead>
                <TableHead>Escopo</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((f) => (
                <TableRow key={f.id}>
                  <TableCell className="font-medium">
                    {f.nome}
                    {f.credenciado_72101 && <Badge variant="secondary" className="ml-2">Credenciado 72.101</Badge>}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {f.cnpj ? formatarCnpj(f.cnpj) : <span className="text-amber-600 dark:text-amber-400">não informado</span>}
                  </TableCell>
                  <TableCell><Badge variant="outline">{f.escopo}</Badge></TableCell>
                  <TableCell className="text-muted-foreground">{f.email || "—"}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Editar ${f.nome}`}
                      onClick={() => {
                        setEditando(f)
                        setAberto(true)
                      }}
                    >
                      <PencilIcon />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <FornecedorDialog open={aberto} onOpenChange={setAberto} fornecedor={editando} />
    </div>
  )
}

export function Component() {
  return (
    <>
      <PageHeader title="Cadastros" description="Produtos e fornecedores da sua empresa." />
      <Tabs defaultValue="produtos">
        <TabsList>
          <TabsTrigger value="produtos">Produtos</TabsTrigger>
          <TabsTrigger value="fornecedores">Fornecedores</TabsTrigger>
        </TabsList>
        <TabsContent value="produtos" className="pt-4"><Produtos /></TabsContent>
        <TabsContent value="fornecedores" className="pt-4"><Fornecedores /></TabsContent>
      </Tabs>
    </>
  )
}
