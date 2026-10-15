"""Enumerações do domínio. Os valores (não os nomes) são o que vai para o banco e para a API."""

import enum


class Perfil(enum.StrEnum):
    vendedor = "vendedor"
    comprador = "comprador"
    gestor = "gestor"


class StatusFalta(enum.StrEnum):
    pendente = "pendente"
    cotado = "cotado"
    comprado = "comprado"
    sem_oferta = "sem_oferta"


class Urgencia(enum.StrEnum):
    baixa = "baixa"
    media = "media"
    alta = "alta"


class Escopo(enum.StrEnum):
    """RN-02: usado em Fornecedor.escopo e Produto.origem."""

    local = "Local"
    nacional = "Nacional"


class ClasseProduto(enum.StrEnum):
    farma = "Farma"
    hospitalar = "Hospitalar"


class Pagamento(enum.StrEnum):
    a_vista = "a_vista"
    d15 = "15d"
    d30 = "30d"
    d45 = "45d"


class StatusPedido(enum.StrEnum):
    aguardando_aprovacao = "aguardando_aprovacao"
    aprovado = "aprovado"
    reprovado = "reprovado"


class OrigemPedido(enum.StrEnum):
    cotacao = "cotacao"  # gerado pelo fechamento da compra (comparativo de cotações)
    manual = "manual"  # registrado na tela pelo comprador/gestor


class StatusRecebimento(enum.StrEnum):
    aguardando_nfe = "aguardando_nfe"
    em_conferencia = "em_conferencia"  # XML enviado, aguardando decisão do comprador
    recebido = "recebido"  # nota aceita


class Severidade(enum.StrEnum):
    erro = "erro"
    alerta = "alerta"
    info = "info"


class ResultadoNFe(enum.StrEnum):
    aprovada = "aprovada"  # nenhum apontamento de erro ou alerta
    com_alertas = "com_alertas"
    reprovada = "reprovada"  # há ao menos um erro


class DecisaoNFe(enum.StrEnum):
    pendente = "pendente"
    aceita = "aceita"
    recusada = "recusada"
