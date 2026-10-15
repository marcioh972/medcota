import { Badge } from "@/components/ui/badge"
import { DECISAO_NFE, RESULTADO_NFE, STATUS_FALTA, STATUS_PEDIDO, STATUS_RECEBIMENTO, URGENCIA } from "@/lib/labels"
import type { DecisaoNFe, ResultadoNFe, StatusFalta, StatusPedido, StatusRecebimento, Urgencia } from "@/lib/types"

const SUCESSO = "border-transparent bg-success text-success-foreground"

export function FaltaStatusBadge({ status }: { status: StatusFalta }) {
  const label = STATUS_FALTA[status]
  if (status === "comprado") return <Badge className={SUCESSO}>{label}</Badge>
  if (status === "sem_oferta") return <Badge variant="destructive">{label}</Badge>
  if (status === "cotado") return <Badge variant="secondary">{label}</Badge>
  return <Badge variant="outline">{label}</Badge>
}

export function PedidoStatusBadge({ status }: { status: StatusPedido }) {
  const label = STATUS_PEDIDO[status]
  if (status === "aprovado") return <Badge className={SUCESSO}>{label}</Badge>
  if (status === "reprovado") return <Badge variant="destructive">{label}</Badge>
  return <Badge variant="secondary">{label}</Badge>
}

export function UrgenciaBadge({ urgencia }: { urgencia: Urgencia }) {
  const label = URGENCIA[urgencia]
  if (urgencia === "alta") return <Badge variant="destructive">{label}</Badge>
  if (urgencia === "media") return <Badge variant="secondary">{label}</Badge>
  return <Badge variant="outline">{label}</Badge>
}

export function RecebimentoBadge({ status }: { status: StatusRecebimento }) {
  const label = STATUS_RECEBIMENTO[status]
  if (status === "recebido") return <Badge className={SUCESSO}>{label}</Badge>
  if (status === "em_conferencia") return <Badge variant="secondary">{label}</Badge>
  return <Badge variant="outline">{label}</Badge>
}

export function ResultadoNFeBadge({ resultado }: { resultado: ResultadoNFe }) {
  const label = RESULTADO_NFE[resultado]
  if (resultado === "reprovada") return <Badge variant="destructive">{label}</Badge>
  if (resultado === "com_alertas") return <Badge variant="secondary">{label}</Badge>
  return <Badge className={SUCESSO}>{label}</Badge>
}

export function DecisaoBadge({ decisao }: { decisao: DecisaoNFe }) {
  const label = DECISAO_NFE[decisao]
  if (decisao === "aceita") return <Badge className={SUCESSO}>{label}</Badge>
  if (decisao === "recusada") return <Badge variant="destructive">{label}</Badge>
  return <Badge variant="outline">{label}</Badge>
}
