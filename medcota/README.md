# MedCota — API de compras e cotações (SaaS multiempresa)

FastAPI + SQLAlchemy 2 + Alembic. Python 3.11+ (testado no 3.12).
O sistema funciona como **SaaS**: várias empresas usam a mesma instalação, cada uma com seus dados totalmente separados.

> O frontend está no projeto irmão `medcota-web` (React + shadcn/ui).

## Sumário

1. [Instalação e execução](#instalação-e-execução-windows--powershell)
2. [Como funciona o SaaS (multiempresa)](#como-funciona-o-saas-multiempresa)
3. [Fluxo de cadastro (passo a passo)](#fluxo-de-cadastro-passo-a-passo)
4. [Regras de cadastro](#regras-de-cadastro)
5. [Endpoints do onboarding](#endpoints-do-onboarding)
6. [Recebimento e conferência de NF-e](#recebimento-e-conferência-de-nf-e)
7. [Segurança](#segurança)
8. [Banco de dados e migrações](#banco-de-dados-e-migrações)
9. [Configuração](#configuração-variáveis-de-ambiente)
10. [Testes](#testes-e-qualidade)
11. [Estrutura do projeto](#estrutura-do-projeto)
12. [Produção e próximos passos](#produção-e-próximos-passos)
13. [Mudanças de contrato](#mudanças-de-contrato)

---

## Instalação e execução (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

copy .env.example .env
# edite o .env e defina JWT_SECRET (>= 32 caracteres):
python -c "import secrets; print(secrets.token_urlsafe(48))"

alembic upgrade head          # cria/atualiza as tabelas
python -m app.seed            # (só dev) empresa de demonstração; mostra a senha e o código gerados
uvicorn app.main:app --reload
```

Docs interativas: http://localhost:8000/docs · Healthcheck: `GET /saude`

O `seed` cria a empresa **Distribuidora Demo** com um gestor, um comprador e um vendedor
(`carla@`, `bruno@`, `ana@` + `medcota.com.br`), produtos, fornecedores e um código de validação
ativo. A senha dos três é gerada e exibida uma única vez (ou defina `SEED_SENHA`, que precisa cumprir a
política de senha). O seed recusa rodar com `AMBIENTE=producao`.

---

## Como funciona o SaaS (multiempresa)

### Conceitos

| Conceito | O que é |
|---|---|
| **Empresa** (tenant) | Cliente do SaaS. Tem nome, CNPJ único e um código de validação. |
| **Gestor** | Quem cadastra a empresa. Administra a equipe, gera o código e aprova pedidos acima da alçada. |
| **Comprador / Vendedor** | Funcionários que criam a própria conta usando o código de validação da empresa. |
| **Código de validação** | Código único por empresa, gerado pelo gestor, que autoriza o cadastro de funcionários. |

### Isolamento de dados

Todas as tabelas de negócio (`usuarios`, `produtos`, `fornecedores`, `faltas`, `cotacoes`, `pedidos`,
`preco_historico`, `avaliacoes_fornecedor`, `nfe_entradas`, `auditoria`) têm a coluna `empresa_id`
(`NOT NULL`, com chave estrangeira e índice). As tabelas-filhas (`cotacao_itens`, `respostas`,
`pedido_itens`) herdam a empresa do registro pai e só são acessadas através dele.

- A empresa **sempre vem do usuário autenticado**, nunca de um campo enviado pelo cliente. Não existe
  parâmetro "empresa" em nenhum endpoint.
- Todo service filtra por `empresa_id` (consultas, agregações, médias históricas, painel, comparativo).
- Pedir um recurso de outra empresa (por ID) responde **404**, igual a um recurso inexistente: não revela
  que o ID existe.
- O **link público do fornecedor** (`/c/{token}`) identifica a cotação — e, por ela, a empresa — pelo
  token de 192 bits; as respostas e o histórico de preços são gravados na empresa dona da cotação.
- Os dados de uma empresa nunca influenciam os de outra (ex.: a média histórica de preços do alerta
  "acima da média" é calculada só com os preços da própria empresa).

A suíte `tests/test_isolamento.py` cobre esses cenários com duas empresas operando em paralelo
(catálogo, faltas, consolidação, cotações, comparativo, pedidos, painel, equipe, auditoria, tentativas
de acessar/alterar por ID e link público).

### Limitações atuais (decisões conscientes)

- **E-mail único no sistema inteiro:** uma conta pertence a uma única empresa.
- **Um gestor por empresa:** o gestor nasce no cadastro da empresa; o código só permite os perfis
  vendedor e comprador.
- **Parâmetros globais:** alçada de aprovação, frete padrão, validade da cotação e horário de corte
  ainda são configurações da instalação (`.env`), não por empresa.

---

## Fluxo de cadastro (passo a passo)

```
 Gestor                                   Funcionário (vendedor/comprador)
   │                                                │
   │ 1. POST /cadastro/empresa                      │
   │    (empresa + CNPJ + gestor + senha)           │
   │    └─► cria a empresa e o gestor, já logado    │
   │                                                │
   │ 2. POST /empresa/codigo                        │
   │    └─► código único: ABCD-EFGH-JKLM            │
   │                                                │
   │ 3. compartilha o código ───────────────────────►
   │                                                │ 4. POST /cadastro/funcionario
   │                                                │    (código + nome + e-mail + perfil
   │                                                │     + a PRÓPRIA senha)
   │                                                │    └─► conta criada na empresa do código,
   │                                                │        já logado
   │ 5. GET/PATCH /empresa/equipe                   │
   │    └─► desativa contas, define quem vê preços  │
   │ 6. POST (gerar novo) ou DELETE /empresa/codigo │
   │    └─► troca ou revoga o código                │
```

1. **O gestor cadastra a empresa** informando nome da empresa, CNPJ, seu nome, e-mail e senha. A
   resposta já traz o token de acesso (login automático).
2. **O gestor gera o código de validação** (tela *Equipe*). Uma empresa nova **não tem código**:
   enquanto ninguém gerar um, ninguém consegue se cadastrar nela.
3. **O gestor compartilha o código** com a equipe (a tela também gera um link pronto,
   `/cadastro/funcionario?codigo=ABCD-EFGH-JKLM`).
4. **Cada funcionário se cadastra sozinho**, escolhendo o perfil (vendedor ou comprador) e criando a
   própria senha. O código define em qual empresa a conta é criada.
5. **O gestor administra a equipe:** desativa/reativa contas e controla quem pode ver preços e custos.
6. **O gestor pode gerar um novo código** (o anterior deixa de valer na hora) ou **revogá-lo**
   (ninguém mais se cadastra até gerar outro). Contas já criadas não são afetadas.

---

## Regras de cadastro

### Senha

Definida pelo próprio usuário (gestor e funcionários), com esta política:

- **no mínimo 8 caracteres** (não é exatamente 8: senhas maiores são bem-vindas);
- pelo menos **uma letra maiúscula**, **uma minúscula** e **um número**;
- no máximo **72 bytes** (limite do bcrypt);
- a senha **não é alterada** (nada de `trim`), é guardada só como hash bcrypt e **nunca** volta nas
  respostas nem nas mensagens de erro de validação.

Quando a senha é recusada, a API informa o que falta:
`"A senha precisa ter pelo menos 8 caracteres, uma letra maiúscula, um número"`.

### CNPJ

- Aceita com ou sem máscara e em minúsculas; é gravado **normalizado** (14 caracteres, sem pontuação).
- Valida os **dígitos verificadores**, incluindo o **CNPJ alfanumérico** (formato vigente a partir de
  julho/2026, ex.: `12.ABC.345/01DE-35`).
- Rejeita sequências repetidas (`00000000000000`) e é **único**: uma empresa por CNPJ.

### Código de validação

- Formato `ABCD-EFGH-JKLM`: 12 caracteres de um alfabeto de 32 símbolos **sem 0, O, 1 e I**
  (evita erro ao digitar) — 60 bits de entropia, gerado com `secrets` (criptograficamente seguro).
- **Único por empresa:** há uma restrição `UNIQUE` no banco e, na geração, o sistema confere colisão.
- **Validade** de `CODIGO_VALIDADE_DIAS` dias (padrão 7). Pode ser reutilizado por vários funcionários
  enquanto estiver válido.
- **Gerar um novo código invalida o anterior** imediatamente; **revogar** deixa a empresa sem código.
- Ao digitar, aceita minúsculas, espaços e com/sem hífen (`abcd efgh jklm`).
- Código inexistente, expirado ou revogado devolvem **a mesma mensagem** (`codigo_invalido`), para não
  dar pistas a quem tenta adivinhar.
- Fica visível **somente para o gestor** da empresa (`GET /empresa`).

> **Decisão registrada:** o código é guardado em texto (não em hash) para o gestor poder consultá-lo de
> novo na tela. Ele é um código de convite (curto, com validade e revogável), não uma senha de acesso.
> Se preferir "exibir uma única vez", dá para trocar por hash sem mudar a API pública.

### Demais regras

- **E-mail:** normalizado para minúsculas e único no sistema.
- **Perfil no cadastro de funcionário:** apenas `vendedor` ou `comprador`. Tentar `gestor` é recusado.
- **Permissão de ver preços (`ver_preco_custo`):** o comprador nasce com `true` e o vendedor com `false`;
  o gestor pode alterar por usuário.
- **Catálogo próprio:** cada empresa cadastra seus produtos e fornecedores (`POST /produtos`,
  `POST /fornecedores`). O EAN é único **dentro da empresa** (duas empresas podem ter o mesmo EAN).

---

## Endpoints do onboarding

| Método e rota | Quem | O que faz |
|---|---|---|
| `POST /cadastro/empresa` | público | Cria a empresa e o gestor; devolve a sessão (login automático). |
| `POST /cadastro/funcionario` | público (com código) | Cria vendedor/comprador na empresa dona do código; devolve a sessão. |
| `POST /auth/login` | público | Login. A resposta inclui o nome da `empresa`. |
| `GET /empresa` | gestor | Dados da empresa e do código (`codigo_validacao`, `codigo_expira_em`, `codigo_ativo`). |
| `POST /empresa/codigo` | gestor | Gera (ou renova) o código de validação. |
| `DELETE /empresa/codigo` | gestor | Revoga o código atual. |
| `GET /empresa/equipe` | gestor | Lista os membros da empresa. |
| `PATCH /empresa/equipe/{id}` | gestor | Altera `ativo` e/ou `ver_preco_custo` de um membro. |
| `GET /produtos` · `POST /produtos` | logado · comprador/gestor | Busca e cadastro de produtos da empresa. |
| `GET /fornecedores` · `POST /fornecedores` | comprador/gestor | Lista e cadastro de fornecedores da empresa. |

Exemplos:

```bash
# 1. Gestor cadastra a empresa
curl -X POST localhost:8000/cadastro/empresa -H "Content-Type: application/json" -d '{
  "empresa_nome": "Distribuidora Alfa", "cnpj": "11.222.333/0001-81",
  "gestor_nome": "Gina Alfa", "email": "gina@alfa.com", "senha": "Senha-forte-1"}'

# 2. Gestor gera o código (use o access_token da resposta anterior)
curl -X POST localhost:8000/empresa/codigo -H "Authorization: Bearer $TOKEN"

# 3. Funcionário se cadastra com o código
curl -X POST localhost:8000/cadastro/funcionario -H "Content-Type: application/json" -d '{
  "codigo": "ABCD-EFGH-JKLM", "nome": "Ana Alfa", "email": "ana@alfa.com",
  "senha": "Senha-forte-1", "perfil": "vendedor"}'

# 4. Gestor desativa uma conta
curl -X PATCH localhost:8000/empresa/equipe/2 -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"ativo": false}'
```

### Formato de erro

Todos os erros seguem `{"detail": {"codigo": "...", "mensagem": "...", ...}}`:

| Código | HTTP | Quando |
|---|---|---|
| `validacao` | 422 | Dados inválidos. Traz `campos: {campo: mensagem}` (sem repetir o valor enviado). |
| `cnpj_em_uso` | 409 | Já existe empresa com esse CNPJ (`campo: "cnpj"`). |
| `email_em_uso` | 409 | E-mail já cadastrado (`campo: "email"`). |
| `codigo_invalido` | 422 | Código inexistente, expirado ou revogado (`campo: "codigo"`). |
| `ean_em_uso` | 409 | Já existe produto com esse EAN **na mesma empresa** (`campo: "ean"`). |
| `cadastro_duplicado` | 409 | Dois cadastros simultâneos colidiram (CNPJ ou e-mail). |
| `nao_pode_desativar_a_si_mesmo` | 409 | O gestor tentou desativar a própria conta. |
| `usuario_nao_encontrado` | 404 | Usuário inexistente **ou de outra empresa**. |
| `limite_requisicoes` | 429 | Rate limit excedido. |

---

## Recebimento e conferência de NF-e

Módulo para **comprador e gestor** (o vendedor não tem acesso a nenhuma rota dele). O comprador registra o pedido na
tela e, quando a mercadoria chega, envia o **XML da nota fiscal**; o sistema confere preços, frete, impostos, totais e
autenticidade e lista cada divergência. Só então a nota é aceita ou recusada.

> **Limite importante:** é uma conferência automática de apoio. Ela **não consulta a SEFAZ** (a situação atual da nota
> — cancelamento, denegação — precisa ser conferida no portal) e **não substitui a análise do contador**.

### Quem acessa

| Perfil | Acesso |
|---|---|
| Vendedor | **Nenhum** (`403 perfil_sem_permissao` em todas as rotas `/recebimento/*` e `/fiscal/*`). |
| Comprador | Registra pedidos, envia XML, reanalisa, aceita notas **sem erro**, recusa notas. Lê os parâmetros fiscais. |
| Gestor | Tudo do comprador, **aceita notas com erro** (com justificativa) e altera os parâmetros fiscais. |

O módulo também exige a permissão `ver_preco_custo` (RN-04), porque a conferência exibe preços, custos e impostos
(`403 sem_permissao_precos` sem ela). Tudo é isolado por empresa: pedido ou nota de outra empresa responde 404.

### Fluxo

```
 1. Registrar o pedido (tela)            POST /recebimento/pedidos
    └─ fornecedor + itens (produto, qtd, preço) + frete previsto
       (acima da alçada o comprador precisa da aprovação do gestor; o gestor aprova os próprios)
 2. Mercadoria chega → enviar o XML      POST /recebimento/pedidos/{id}/nfe   (multipart, campo "arquivo")
    └─ o sistema lê o XML, confere e grava a nota com os apontamentos
 3. Ver o resultado                      GET  /recebimento/nfes/{id}
    └─ aprovada | com_alertas | reprovada  (+ lista de apontamentos)
 4. (opcional) corrigir cadastro e       POST /recebimento/nfes/{id}/reanalisar
    reanalisar (CNPJ do fornecedor, parâmetros fiscais)
 5. Decidir                              POST /recebimento/nfes/{id}/decisao
    ├─ aceitar → o pedido vira "recebido" (quando todos os fornecedores do pedido tiverem nota aceita)
    └─ recusar → o pedido volta a "aguardando nota" e uma nova nota pode ser enviada
```

Situação do pedido (`recebimento`): `aguardando_nfe` → `em_conferencia` (nota enviada, sem decisão) → `recebido`.
Um pedido pode ser **manual** (registrado na tela) ou vir das **cotações**; os dois passam pela mesma conferência.
Em pedido com vários fornecedores, cada nota é conferida só contra os itens do seu emitente.

### Regras de decisão

- **Nota sem erro** (aprovada ou só com alertas): o comprador ou o gestor aceita.
- **Nota com erro**: só o **gestor** aceita, e **com justificativa** (mínimo de 10 caracteres). O comprador pode recusá-la.
- **Recusar** exige um motivo (mínimo de 5 caracteres).
- Decisão tomada é definitiva: a nota não pode mais ser reanalisada nem decidida de novo.
- A mesma nota (**chave de acesso**) não pode ser enviada duas vezes na empresa (`409 nfe_duplicada`).

### O que a conferência verifica

Cada constatação é um **apontamento** com severidade, mensagem, item da nota, campo, valor esperado × encontrado e a
base normativa quando houver. Severidades: **erro** (inconsistência objetiva → nota "reprovada"), **alerta** (suspeita
que exige olhar humano) e **info** (esclarecimento ou limite da conferência).

**Autenticidade e identificação**

| Código | Sev. | O que verifica |
|---|---|---|
| `CHAVE_FORMATO`, `CHAVE_DV` | erro | Formato da chave (44 posições; CNPJ numérico ou alfanumérico) e dígito verificador (módulo 11). |
| `CHAVE_INCONSISTENTE` | erro | A chave bate com UF, CNPJ do emitente, modelo, série, número e mês/ano da nota. |
| `PROTOCOLO_AUSENTE` | erro* | XML sem protocolo de autorização (*alerta se a empresa desligar a exigência). |
| `NFE_NAO_AUTORIZADA`, `PROTOCOLO_CHAVE_DIVERGENTE` | erro | `cStat` diferente de 100/150 (denegada, rejeitada...) ou protocolo de outra chave. |
| `AMBIENTE_HOMOLOGACAO`, `MODELO_INVALIDO`, `NFE_DE_ENTRADA` | erro | Nota de homologação, modelo diferente de 55, ou marcada como entrada. |
| `FINALIDADE_NAO_NORMAL` | alerta | Nota complementar, de ajuste ou de devolução. |
| `DESTINATARIO_DIVERGENTE` | erro | O destinatário não é o CNPJ da sua empresa. |
| `DESTINATARIO_NAO_VALIDADO` | info | A empresa não tem CNPJ cadastrado. |
| `EMISSAO_FUTURA`, `EMISSAO_ANTERIOR_AO_PEDIDO` | alerta | Datas suspeitas. |
| `SEFAZ_NAO_CONSULTADA` | info | Lembra que a situação na SEFAZ não foi consultada. |

**Fornecedor e pedido × nota**

| Código | Sev. | O que verifica |
|---|---|---|
| `EMITENTE_DIVERGENTE`, `EMITENTE_NAO_ENCONTRADO` | erro | O emitente não é o fornecedor do pedido (pelo CNPJ cadastrado). |
| `FORNECEDOR_SEM_CNPJ` | alerta | O fornecedor não tem CNPJ cadastrado: o emitente não pôde ser validado. |
| `ITEM_FORA_DO_PEDIDO` | erro | Item da nota que não está no pedido (casa por EAN; sem EAN, pela descrição). |
| `ITEM_NAO_FATURADO` | alerta | Item do pedido que não veio na nota. |
| `PRECO_ACIMA_DO_PEDIDO` | erro | Preço líquido (vProd − desconto) acima do pedido, além da tolerância configurada. |
| `PRECO_ABAIXO_DO_PEDIDO` | alerta | Preço abaixo do pedido (confirme se houve desconto combinado). |
| `QUANTIDADE_ACIMA_DO_PEDIDO` | erro | Quantidade faturada maior que a pedida (somando as linhas do mesmo produto). |
| `ENTREGA_PARCIAL` | alerta | Quantidade menor que a pedida. |
| `NCM_DIVERGENTE_CADASTRO`, `NCM_INVALIDO` | alerta / erro | NCM diferente do cadastro do produto; NCM fora do formato de 8 dígitos. |

**Totais**

| Código | Sev. | O que verifica |
|---|---|---|
| `ITEM_TOTAL_INCONSISTENTE` | erro | quantidade × valor unitário ≠ valor do produto. |
| `TOTAL_PRODUTOS_DIVERGENTE` | erro | Total dos produtos (e frete/seguro/desconto/outros por item) ≠ soma dos itens. |
| `TOTAL_IMPOSTO_DIVERGENTE` | erro | Totais de ICMS, ST, FCP, IPI, PIS e COFINS ≠ soma dos itens. |
| `TOTAL_NF_DIVERGENTE` | erro | `vNF` ≠ produtos − descontos + ST + FCP-ST + frete + seguro + outras despesas + II + IPI. |
| `TOTAIS_AUSENTES` | erro | Nota sem o grupo de totais. |

**Frete** (regra da sua operação)

| Código | Sev. | O que verifica |
|---|---|---|
| `FRETE_INDEVIDO` | erro | **Fornecedor de Maceió/AL não cobra frete na nota**, mas a nota traz frete (no total ou nos itens). |
| `FRETE_ACIMA_DO_PEDIDO` | erro | Frete maior que o previsto no pedido (fornecedores de outros municípios). |
| `DESPESA_ACESSORIA_EM_FORNECEDOR_SEM_FRETE` | alerta | Seguro/outras despesas em fornecedor que não cobra frete (possível frete disfarçado). |
| `FRETE_MODALIDADE_INCOERENTE` | alerta | Modalidade FOB (frete por conta do destinatário) com frete cobrado. |

A regra de Maceió usa o **código IBGE do município do emitente** na nota (`2704302`), e os municípios sem frete são
configuráveis em **Parâmetros fiscais** (lista vazia desliga a regra). É uma regra da operação da empresa, não uma norma.

**Impostos por item**

| Código | Sev. | O que verifica |
|---|---|---|
| `ICMS_CALCULO_INCORRETO` | erro | `vICMS` ≠ base × alíquota (CST 00, 10, 20, 70, 90). |
| `ICMS_ST_CALCULO_INCORRETO` | erro | `vICMSST` ≠ base ST × alíquota ST − ICMS próprio (CST 10, 30, 70, 90). Base: Convênio ICMS 142/2018. |
| `FCP_CALCULO_INCORRETO`, `FCP_ST_CALCULO_INCORRETO` | erro | Fundo de combate à pobreza ≠ base × alíquota. |
| `ICMS_BASE_DIVERGENTE`, `ICMS_BASE_REDUZIDA_DIVERGENTE` | alerta | Base diferente do valor do item com frete/seguro/despesas − desconto (ou da redução informada no CST 20). |
| `ALIQUOTA_INTERESTADUAL_DIVERGENTE` | alerta | Operação entre estados fora de 4% (importados), 7% (S/SE → N/NE/CO/ES) ou 12%. Base: Resoluções do Senado 22/1989 e 13/2012. |
| `ALIQUOTA_INTERNA_DIVERGENTE` | erro | Operação dentro do estado com alíquota diferente da **configurada pela empresa**. |
| `ALIQUOTA_INTERNA_NAO_CONFIGURADA` | info | Sem alíquota interna configurada, ela **não é validada** (ver abaixo). |
| `ICMS_DESTACADO_EM_CST_ISENTO`, `ICMS_AUSENTE` | alerta | ICMS destacado em CST 40/41/50; item sem grupo de ICMS. |
| `ICMS_SIMPLES_NACIONAL` | info | Emitente do Simples (CSOSN): o ICMS dos itens não é recalculado. |
| `CFOP_UF_INCOERENTE`, `CFOP_DE_ENTRADA`, `CFOP_INVALIDO` | erro | CFOP 5xxx/6xxx incompatível com a operação (dentro/fora do estado); CFOP de entrada em nota de venda. |
| `CFOP_CST_INCOERENTE` | alerta | CFOP de ST (…405, …401, …403) ou de venda sem ST (…101, …102) com CST incompatível. |
| `PIS_CALCULO_INCORRETO`, `COFINS_CALCULO_INCORRETO` | erro | Valor ≠ base × alíquota (CST 01/02). |
| `PIS_VALOR_EM_CST_SEM_TRIBUTO`, `COFINS_VALOR_EM_CST_SEM_TRIBUTO` | erro | Valor destacado em CST sem tributo. |
| `PIS_AUSENTE`, `COFINS_AUSENTE` | alerta | Item sem o grupo. |
| `PIS_COFINS_MONOFASICO_REVISAR` | alerta | Medicamento (NCM 3003/3004) com PIS/COFINS tributado: na revenda costuma ser monofásico (Lei 10.147/2000). |
| `IPI_CALCULO_INCORRETO` | erro | IPI ≠ base × alíquota (CST 50). |

### Decreto nº 72.101/2020 (Alagoas) — o que o sistema faz e o que não faz

O Decreto AL nº 72.101/2020 concede **tratamento tributário diferenciado de ICMS a atacadistas credenciados de
medicamentos, drogas e produtos correlatos**, e foi alterado várias vezes (2023, 2025 e 2026). O ponto central dele é o
**recolhimento mensal do ICMS pelo atacadista credenciado**, apurado pelo próprio emitente: esse valor **não aparece
destacado na nota fiscal** que o comprador recebe. Por isso:

- O sistema **confere o que está na nota**: ICMS próprio, ICMS-ST, FCP, PIS/COFINS, CFOP/CST, totais, frete e preços.
  Quando o fornecedor é marcado como credenciado, o cálculo da ST é conferido e a nota traz um aviso (`DEC72101_ESCOPO`)
  explicando esse alcance.
- O sistema **não valida o recolhimento mensal** do atacadista nem consulta o credenciamento: o campo "credenciado"
  no cadastro do fornecedor é **informado pela empresa**, que deve confirmá-lo na SEFAZ-AL.
- Notas de fornecedores de Alagoas com medicamentos que não estejam marcados como credenciados recebem uma
  informação (`DEC72101_CREDENCIAMENTO_NAO_INFORMADO`); fornecedor marcado como credenciado mas emitindo de outro estado
  gera um alerta (`DEC72101_EMITENTE_FORA_DE_AL`).
- **Nenhuma alíquota do decreto está gravada no código.** Alíquotas e percentuais dependem da redação vigente do
  decreto e da lei estadual, que mudaram recentemente. Elas ficam em **Parâmetros fiscais** (campo
  *alíquota interna de ICMS*), mantidos pelo gestor/contador.
- O texto consolidado e atualizado do decreto não pôde ser lido integralmente durante o desenvolvimento (fonte paga).
  **Valide as regras com o contador da empresa** antes de usá-las como base fiscal.

### Parâmetros fiscais (por empresa)

`GET /fiscal/configuracao` (comprador/gestor) e `PUT /fiscal/configuracao` (só gestor):

| Campo | Padrão | Efeito |
|---|---|---|
| `aliquota_interna_icms` | vazio | Alíquota (%) das operações dentro do estado. Vazio = não valida. Diferença vira **erro**. |
| `tolerancia_preco_pct` | `0` | Diferença percentual aceita entre o preço do pedido e o da nota. |
| `frete_zero_municipios` | `["2704302"]` | Códigos IBGE (7 dígitos) cujos fornecedores não cobram frete. Vazio desliga a regra. |
| `exigir_protocolo` | `true` | XML sem protocolo vira erro (em vez de alerta). |

Depois de alterar um parâmetro, use **reanalisar** nas notas pendentes para aplicá-lo (a nota guarda o XML original).

### Endpoints do módulo

| Método e rota | Quem | O que faz |
|---|---|---|
| `POST /recebimento/pedidos` | comprador/gestor | Registra o pedido (fornecedor, itens, frete previsto, nº externo, observação). |
| `GET /recebimento/pedidos` | comprador/gestor | Lista pedidos (`?situacao=aguardando_nfe\|em_conferencia\|recebido`, `limit`, `offset`). |
| `GET /recebimento/pedidos/{id}` | comprador/gestor | Pedido com itens, fornecedores e notas. |
| `POST /recebimento/pedidos/{id}/nfe` | comprador/gestor | Envia o XML (multipart `arquivo`) e devolve a conferência. |
| `GET /recebimento/nfes` · `GET /recebimento/nfes/{id}` | comprador/gestor | Notas e apontamentos. |
| `GET /recebimento/nfes/{id}/xml` | comprador/gestor | Baixa o XML original. |
| `POST /recebimento/nfes/{id}/reanalisar` | comprador/gestor | Refaz a conferência (nota ainda sem decisão). |
| `POST /recebimento/nfes/{id}/decisao` | comprador/gestor | `{"decisao": "aceita"\|"recusada", "justificativa": "..."}`. |
| `PATCH /fornecedores/{id}` | comprador/gestor | Ajusta `cnpj`, `email` e `credenciado_72101` do fornecedor. |
| `GET /fiscal/configuracao` · `PUT /fiscal/configuracao` | comprador/gestor · gestor | Parâmetros fiscais. |

Erros específicos: `xml_invalido` (422), `arquivo_vazio` (422), `arquivo_grande` (413), `nfe_duplicada` (409, com
`nfe_id`), `pedido_nao_aprovado` (409), `nfe_ja_decidida` (409), `aceite_exige_gestor` (403),
`justificativa_obrigatoria` (422), `sem_permissao_precos` (403), `nfe_nao_encontrada` e `pedido_nao_encontrado` (404).

Exemplo:

```bash
# registra o pedido
curl -X POST localhost:8000/recebimento/pedidos -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "fornecedor_id": 1, "numero_externo": "PC-1", "frete_previsto": "0",
  "itens": [{"produto_id": 1, "quantidade": 10, "preco": "10.00"}]}'

# envia o XML da nota
curl -X POST localhost:8000/recebimento/pedidos/1/nfe -H "Authorization: Bearer $TOKEN" -F "arquivo=@nfe.xml"
```

### Segurança do upload

- O XML é lido com **`defusedxml`** (DTD, entidades e recursos externos proibidos): bloqueia XXE e "billion laughs".
  Um XML com `DOCTYPE` é recusado (`422`) e nunca expande entidades.
- Limite de tamanho (`NFE_MAX_BYTES`, padrão 2 MB): o servidor lê no máximo o limite + 1 byte, sem carregar arquivos enormes.
- Só é gravada nota com `infNFe` e chave de 44 caracteres; arquivos que não são NF-e não geram registro.
- O XML original é guardado e baixado sem alteração (`X-Content-Type-Options: nosniff`).
- Toda ação é auditada: `registrou_pedido_manual`, `importou_nfe`, `reanalisou_nfe`, `aceitou_nfe`, `recusou_nfe`,
  `atualizou_config_fiscal`, `atualizou_fornecedor`.

## Segurança

- **Rate limit por IP** nos cadastros (`RATE_LIMIT_CADASTRO`, padrão 5/min), no login e nos links
  públicos. Com 60 bits de entropia, adivinhar um código é inviável nessa taxa.
- **Bloqueio de conta** após 5 senhas erradas (30 min) e tempo de resposta equalizado para e-mails
  inexistentes.
- **Contas desativadas** perdem o acesso na hora (o token é validado contra o banco a cada requisição).
- **Validação sem eco:** erros de validação nunca devolvem o valor enviado (evita vazar senha em
  respostas e logs).
- **Auditoria** (`auditoria`, por empresa): `cadastrou_empresa`, `cadastrou_funcionario`,
  `gerou_codigo_validacao`, `revogou_codigo_validacao`, `alterou_usuario`, `criou_produto`,
  `criou_fornecedor`, além das ações de compra.
- **CORS** restrito às origens de `CORS_ORIGENS` (métodos GET, POST, PATCH e DELETE).
- **Enumeração de e-mail/CNPJ:** os cadastros informam "já cadastrado" (necessário para a usabilidade).
  É mitigado pelo rate limit; sem verificação de e-mail, essa é a troca aceita.

---

## Banco de dados e migrações

```powershell
alembic upgrade head      # aplica tudo
alembic downgrade -1      # desfaz a última
alembic check             # confere se os models e as migrações estão em sincronia
```

A migração **`0002_multiempresa`**:

- cria a tabela `empresas` (nome, CNPJ único, código de validação único e validade);
- adiciona `empresa_id` (`NOT NULL`, FK nomeada e índice) em todas as tabelas de negócio;
- **preserva dados existentes:** se o banco já tinha dados (instalação de empresa única), tudo vai para
  uma empresa **"Empresa padrão"** (sem CNPJ), e o gestor antigo continua acessando normalmente. Em
  banco vazio, nenhuma empresa é criada;
- troca as unicidades globais por unicidades **por empresa**: EAN do produto e chave de acesso da NF-e;
- funciona em SQLite (modo *batch*) e em PostgreSQL.

A migração **`0003_recebimento_nfe`** acrescenta: `cnpj` e `credenciado_72101` em `fornecedores` (CNPJ único por
empresa); `origem`, `recebimento`, `frete_previsto`, `numero_externo` e `observacao` em `pedidos`; os dados extraídos do
XML, o resultado e a decisão em `nfe_entradas`; e as tabelas `nfe_apontamentos` e `configuracoes_fiscais`. Pedidos e
notas existentes continuam válidos (as colunas novas têm valor padrão).

> Ao desfazer a 0002 com **duas ou mais empresas**, voltar a EAN/chave únicos globais pode falhar por
> duplicidade — é o comportamento esperado de um downgrade que apaga o isolamento.

---

## Configuração (variáveis de ambiente)

Veja `.env.example`. As principais:

| Variável | Padrão | Descrição |
|---|---|---|
| `AMBIENTE` | `desenvolvimento` | `desenvolvimento`, `teste` ou `producao` (em produção o CORS não aceita `*`). |
| `DATABASE_URL` | `sqlite:///./medcota.db` | Em produção, use PostgreSQL. |
| `JWT_SECRET` | — (obrigatório) | Mínimo de 32 caracteres. |
| `CORS_ORIGENS` | `localhost:5173` e `:3000` | Lista JSON de origens do frontend. |
| `CODIGO_VALIDADE_DIAS` | `7` | Validade do código de validação de funcionários. |
| `RATE_LIMIT_CADASTRO` | `5/minute` | Limite por IP nos cadastros de empresa e de funcionário. |
| `RATE_LIMIT_LOGIN` | `10/minute` | Limite por IP no login. |
| `NFE_MAX_BYTES` | `2000000` | Tamanho máximo do XML da NF-e enviado. |
| `LOGIN_MAX_FALHAS` · `LOGIN_BLOQUEIO_MIN` | `5` · `30` | Bloqueio de conta por tentativas. |
| `ALCADA_APROVACAO` · `FRETE_PADRAO` · `VALIDADE_COTACAO_H` · `HORARIO_CORTE` · `FUSO_HORARIO` | — | Regras de negócio (globais). |

---

## Testes e qualidade

```powershell
pytest          # 230 testes
ruff check .
```

| Arquivo | Cobre |
|---|---|
| `test_cadastro_empresa.py` | Cadastro da empresa e do gestor, CNPJ (inclusive alfanumérico), senha fraca, duplicidades. |
| `test_codigo_funcionarios.py` | Geração, unicidade, renovação, revogação e expiração do código; cadastro de funcionário. |
| `test_equipe.py` | Gestão da equipe: desativar, permissões de preço, proteção do gestor. |
| `test_isolamento.py` | **Isolamento entre empresas** em todos os módulos e por tentativa de acesso por ID. |
| `test_validadores.py` | Política de senha, CNPJ, formato do código e CORS (preflight de PATCH/DELETE). |
| `test_migracoes.py` | `upgrade head` sem divergência, dados legados migrados, downgrade completo. |
| `test_fiscal_regras.py` | **Motor de conferência**: parser seguro (XXE/DTD), chave de acesso e cada regra de preço, frete, totais, ICMS/ST/FCP, CFOP, PIS/COFINS e Decreto 72.101, partindo de uma nota correta e injetando um defeito por vez. |
| `test_recebimento.py` | Módulo por API: vendedor barrado em todas as rotas, pedido manual, fluxo de aceite/recusa, aceite com erro só pelo gestor, upload inválido/malicioso/duplicado, reanálise, parâmetros fiscais e isolamento entre empresas. |
| `test_auth.py`, `test_faltas.py`, `test_custo.py`, `test_fluxo_compra.py` | Login, faltas, custo final e o fluxo de compra completo. |

---

## Estrutura do projeto

```
app/
  main.py            monta o app (CORS, rate limit, request-id, erros, routers)
  enums.py           Perfil, StatusFalta, Pagamento, Escopo, StatusPedido...
  models.py          tabelas (SQLAlchemy 2 tipado; Empresa + TenantMixin; dinheiro em Decimal)
  seed.py            empresa de demonstração (recusa rodar em produção)
  core/              config, database, security (bcrypt + JWT), password, cnpj, deps, erros, logging, fuso
  schemas/           contratos de entrada/saída (Pydantic) e tipos validados (CNPJ, senha, e-mail)
  services/          regras de negócio: empresas (onboarding/código), equipe, catálogo, faltas,
                     cotações, comparativo, compras, dashboard, auth, auditoria
  services/fiscal/   motor de conferência (puro, sem banco): parser seguro do XML, chave, tabelas e regras
  routers/           endpoints HTTP finos: cadastro, empresa, produtos, fornecedores, faltas, cotações, recebimento...
alembic/versions/    0001 esquema inicial · 0002 multiempresa · 0003 recebimento de NF-e
tests/               pytest
```

---

## Produção e próximos passos

Checklist:

- `AMBIENTE=producao`, `JWT_SECRET` forte e `CORS_ORIGENS` com o domínio real (sem `*`).
- PostgreSQL: `pip install -e ".[postgres]"` e `DATABASE_URL=postgresql+psycopg://user:senha@host/medcota`.
  O lock contra compra duplicada (`SELECT ... FOR UPDATE`) só tem efeito no PostgreSQL.
- Atrás de proxy/Nginx, rode o uvicorn com `--proxy-headers` para o rate limit enxergar o IP real.
- Não rode o `seed` em produção (ele recusa).

Evoluções sugeridas para o SaaS:

- **Defesa em profundidade no PostgreSQL:** *Row-Level Security* por `empresa_id`, além dos filtros da
  aplicação.
- **Verificação de e-mail** e "esqueci minha senha".
- **Mais de um gestor** por empresa e convite por e-mail (código de uso único).
- **Parâmetros por empresa** (alçada, frete, horário de corte) e plano/assinatura.
- Guardar o código de validação como hash (exibido uma única vez).

---

## Mudanças de contrato

Em relação à versão de empresa única:

- `LoginOut` ganhou `empresa` (nome da empresa).
- Todos os endpoints passam a operar **somente** sobre a empresa do usuário autenticado.
- EAN do produto e chave da NF-e são únicos **por empresa**.
- Novos endpoints: `/cadastro/*`, `/empresa/*`, `POST /produtos`, `/fornecedores`.
- CORS agora libera `PATCH` e `DELETE`.
- Novos: módulo `/recebimento/*` e `/fiscal/*` (comprador/gestor), `PATCH /fornecedores/{id}`; fornecedores ganham `cnpj` e
  `credenciado_72101`; pedidos ganham `origem`, `recebimento`, `frete_previsto`, `numero_externo` e `observacao`.
- CORS agora também libera `PUT`.
- Mantidas as mudanças anteriores: valores monetários como `Decimal` (string no JSON), erros em
  `{"detail": {"codigo", "mensagem"}}`, `GET /c/{token}` somente leitura (a abertura é contada em
  `POST /c/{token}/abertura`), valores de preço `null` sem a permissão `ver_preco_custo` (RN-04).
