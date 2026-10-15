# MedCota Web

Frontend do MedCota (SaaS multiempresa): **React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui**, com
TanStack Query, React Router, React Hook Form + Zod e Sonner. Consome a API em `../medcota` (FastAPI).

## Rodando

```powershell
npm install
copy .env.example .env     # ajuste VITE_API_URL se a API não estiver em http://localhost:8000
npm run dev                # http://localhost:5173
```

A API precisa estar no ar (`uvicorn app.main:app --reload`) e permitir a origem do front em
`CORS_ORIGENS` (o padrão já inclui `http://localhost:5173`). O `python -m app.seed` do backend cria uma
empresa de demonstração e mostra a senha e o código de validação.

## Scripts

| Comando | O que faz |
|---|---|
| `npm run dev` | servidor de desenvolvimento |
| `npm run build` | typecheck (`tsc -b`) + build de produção em `dist/` |
| `npm test` | testes (Vitest + Testing Library) — 84 testes |
| `npm run lint` | oxlint |

## Cadastro, empresas e equipe (SaaS)

Cada empresa usa o sistema de forma isolada. O fluxo, do ponto de vista do usuário:

1. **Cadastrar empresa** — `/cadastro/empresa`
   O gestor informa empresa, CNPJ, seu nome, e-mail e **cria a própria senha**. Ao concluir, já entra no
   sistema e é levado à tela **Equipe**.
2. **Gerar o código de validação** — `/equipe` (só gestor)
   Uma empresa nova não tem código; o gestor clica em *Gerar código*. A tela mostra o código
   (`ABCD-EFGH-JKLM`), a validade, e botões para **copiar o código**, **copiar um link de cadastro**,
   **gerar um novo** (o anterior deixa de valer, com confirmação) e **revogar**.
3. **Cadastrar-se como funcionário** — `/cadastro/funcionario`
   O funcionário informa o código da empresa, escolhe **Vendedor** ou **Comprador**, preenche nome e
   e-mail e **cria a própria senha**. O código define em qual empresa a conta nasce. O link copiado pelo
   gestor (`/cadastro/funcionario?codigo=...`) já abre com o código preenchido.
4. **Gerenciar a equipe** — `/equipe`
   O gestor ativa/desativa contas e define quem pode ver preços e custos. O gestor não pode desativar a
   própria conta.
5. **Cadastrar produtos e fornecedores** — `/cadastros` (comprador e gestor)
   Cada empresa tem o seu catálogo. Sem produtos os vendedores não conseguem lançar faltas e, sem
   fornecedores, não há como gerar cotações.

A tela de login tem atalhos para os dois cadastros, e o cabeçalho mostra o nome da empresa.

### Regra de senha

Mínimo de **8 caracteres**, com **letra maiúscula, letra minúscula e número** (máximo de 72 bytes). Os
formulários mostram um **checklist ao vivo** dos requisitos, botão de mostrar/ocultar senha e campo de
confirmação. A mesma regra é validada no backend; o front só antecipa o feedback.

### CNPJ

Aceita com ou sem máscara e também o **CNPJ alfanumérico**. A validação dos dígitos verificadores roda
no navegador (`src/lib/cnpj.ts`) e de novo no servidor; o valor é enviado normalizado (sem pontuação).

## Recebimento e conferência de NF-e

Disponível para **comprador e gestor** (o vendedor não tem o item no menu e é redirecionado se abrir a rota).

1. **Registrar o pedido** — `/recebimento/novo`
   Fornecedor, itens (produto com busca, quantidade, preço unitário), frete previsto, nº do pedido no fornecedor e
   observação. Mostra o total estimado (o servidor calcula o oficial). Acima da alçada, o pedido do comprador aguarda a
   aprovação do gestor; enquanto isso não é possível enviar a nota.
2. **Acompanhar** — `/recebimento`
   Lista com abas (*todos, aguardando nota, em conferência, recebidos*), situação do pedido e resultado da última nota.
3. **Enviar o XML e conferir** — `/recebimento/:pedidoId`
   Envie o XML **autorizado** (até 2 MB). O sistema mostra, por nota, o resultado (*sem apontamentos, com alertas, com
   erros*) e cada apontamento com mensagem, item, **esperado × encontrado** e base normativa. Erros e alertas ficam
   abertos; as informações (limites da conferência) ficam recolhidas.
4. **Decidir**
   *Aceitar* ou *Recusar* a nota. Nota com erro só pode ser aceita pelo **gestor**, com justificativa (mín. 10
   caracteres); o botão fica desabilitado para o comprador, que pode recusar (motivo mín. 5). Também há *Reanalisar*
   (depois de corrigir CNPJ do fornecedor ou parâmetros) e *Baixar XML* (download autenticado).
5. **Parâmetros fiscais** — `/recebimento/parametros`
   Alíquota interna de ICMS, tolerância de preço, municípios cujos fornecedores não cobram frete (padrão Maceió/AL) e
   exigência de protocolo. Só o gestor altera. A tela explica o alcance do **Decreto AL nº 72.101/2020**: o ICMS que o
   atacadista recolhe nesse regime é mensal e não aparece na nota, então o sistema confere o que está destacado nela.
6. **Fornecedores com CNPJ** — `/cadastros` → Fornecedores
   O CNPJ do fornecedor (numérico ou alfanumérico) permite validar o emitente da nota; há também a marcação
   *Atacadista credenciado (Decreto AL 72.101/2020)*, que deve ser confirmada na SEFAZ-AL. Fornecedores sem CNPJ são
   destacados, e é possível editá-los.

A conferência é um **apoio**: não consulta a SEFAZ e não substitui a análise do contador. As regras vivem no backend;
o front apenas apresenta os apontamentos.

## Telas por perfil

| Perfil | Telas |
|---|---|
| **Vendedor** | `/faltas` — lista do dia, lançar falta (busca de produto, confirmação ao somar duplicata). |
| **Comprador** | `/dashboard`, `/consolidacao`, `/cotacoes`, `/comparativo`, `/pedidos`, `/recebimento`, `/cadastros`. Gera cotações, abre 2ª rodada, fecha a compra e confere as notas fiscais. |
| **Gestor** | Tudo do comprador, **mais** `/equipe`. Aprova ou reprova pedidos acima da alçada, **aceita notas com erro** (com justificativa) e altera os parâmetros fiscais. |
| **Fornecedor** (público) | `/c/:token` — responde a cotação pelo link, sem login. |
| **Público** | `/login`, `/cadastro/empresa`, `/cadastro/funcionario`. |

O **vendedor não vê nem acessa** o módulo de recebimento (o backend também o bloqueia). O menu e as rotas respeitam o perfil: acessar uma tela sem permissão redireciona para a tela inicial do
próprio perfil.

## Estrutura

```
src/
  app/            providers, rotas (lazy), QueryClient
  components/
    ui/           componentes shadcn/ui (código do projeto, edite à vontade)
    layout/       shell, navegação por perfil, menu do usuário
    senha-input   campo de senha (mostrar/ocultar) + checklist de requisitos
  features/       auth (login, cadastros) · equipe · catalogo · faltas · compras · recebimento · dashboard · fornecedor
  lib/            api (cliente HTTP), types, format, labels, password, cnpj, form-errors, utils
  hooks/  test/
```

## Decisões

- **Sessão:** token e nome da empresa em `sessionStorage` (some ao fechar a aba). Um 401 em rota
  autenticada encerra a sessão e limpa o cache. Para segurança máxima em produção, o ideal é cookie
  `HttpOnly` emitido pela API.
- **Isolamento entre empresas:** quem garante é o backend (a empresa vem do token, nunca de um campo do
  formulário). Ao sair, o cache do TanStack Query é limpo para nada vazar entre contas.
- **Erros da API → formulário:** `aplicarErroDaApi` leva erros de validação (`campos`) e erros de negócio
  com `campo` (ex.: CNPJ já cadastrado, código inválido) para o campo certo; o resto vira alerta geral.
- **Redirecionamento pós-cadastro:** a guarda "já logado" é ignorada logo após o cadastro, para a
  navegação intencional (gestor → Equipe) não ser sobrescrita.
- **Upload e download autenticados:** o XML vai como `multipart/form-data` (sem definir `Content-Type`, para o
  navegador incluir o *boundary*) e o download usa `fetch` com o token, pois um `<a href>` não enviaria o `Authorization`.
- **Dinheiro:** a API envia `Decimal` como string; o front só **formata**. Sem a permissão
  `ver_preco_custo` os valores chegam `null` e a UI mostra "—".
- **Datas:** a API devolve UTC sem fuso; `parseUtc` evita ler como horário local.
- **Code splitting:** cada página é carregada sob demanda pelo roteador.
- **Acessibilidade:** link "pular para o conteúdo", labels em todos os campos, `role="alert"` em erros,
  checklist de senha com texto para leitores de tela.

## shadcn/ui

Os componentes em `src/components/ui` seguem o estilo **new-york** (Radix) do repositório oficial
`shadcn-ui/ui` (incluindo `switch` e `tabs`, usados em Equipe e Cadastros). Para adicionar mais:
`npx shadcn@latest add <componente>` (o `components.json` já está configurado). O tema (neutral,
claro/escuro) fica em `src/index.css`.
