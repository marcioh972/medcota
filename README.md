<div align="center">

<img src="./assets/img/medcota-logo.png" alt="Logo do MedCota" width="200"> 

<br>

Plataforma de **compras, cotações e conferência de notas fiscais** para empresas que compram medicamentos e produtos hospitalares.

<!-- Badges -->
<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/testes%20backend-230%20passando-success?style=flat-square" alt="230 testes no backend">
  <img src="https://img.shields.io/badge/testes%20frontend-84%20passando-success?style=flat-square" alt="84 testes no frontend">
</p>

<!--
  Badges que dependem do repositório (descomente e troque seu-usuario/seu-repo depois de publicar no GitHub):
  <img src="https://img.shields.io/github/license/seu-usuario/seu-repo?style=flat-square" alt="Licença">
  <img src="https://img.shields.io/github/last-commit/seu-usuario/seu-repo?style=flat-square" alt="Último commit">
  <img src="https://img.shields.io/github/issues/seu-usuario/seu-repo?style=flat-square" alt="Issues abertas">
-->

[API (Swagger)](http://localhost:8000/docs) · [Documentação do backend](./medcota/README.md) · [Documentação do frontend](./medcota-web/README.md) · [Reportar Bug](https://github.com/seu-usuario/seu-repo/issues) · [Solicitar Feature](https://github.com/seu-usuario/seu-repo/issues)

</div>

<br>

## 📑 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Demonstração](#-demonstração)
- [Tecnologias](#️-tecnologias)
- [Funcionalidades](#-funcionalidades)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração (Variáveis de Ambiente)](#-configuração)
- [Como Usar](#️-como-usar)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Testes](#-testes)
- [Deploy](#-deploy)
- [Roadmap](#️-roadmap)
- [Como Contribuir](#-como-contribuir)
- [FAQ](#-faq)
- [Licença](#-licença)
- [Contato](#-contato)
- [Agradecimentos](#-agradecimentos)

<br>

## 📖 Sobre o Projeto

Quem compra medicamentos para revender vive um ciclo trabalhoso: o vendedor descobre que um item faltou, o comprador junta as faltas do dia, pede preço a vários fornecedores, compara o **custo final** (preço, desconto financeiro e frete) e fecha o pedido. Quando a mercadoria chega, ainda é preciso conferir se a nota fiscal bate com o que foi pedido: preços, quantidades, frete e impostos.

O **MedCota** cobre esse ciclo inteiro em um único sistema:

1. **Vendedores** lançam as faltas do dia (o sistema soma as demandas duplicadas).
2. **Compradores** consolidam a demanda, geram uma cotação por fornecedor (cada fornecedor responde por um **link único, sem precisar de login**), comparam as ofertas e fecham a compra.
3. **Gestores** aprovam pedidos acima da alçada e administram a equipe.
4. Na chegada da mercadoria, o comprador **sobe o XML da NF-e** e o sistema aponta, item a item, o que está diferente do pedido ou errado na nota.

É um **Sistema multiempresa**: várias empresas usam a mesma instalação, cada uma com seus dados totalmente isolados. O gestor cadastra a empresa e gera um **código de validação**; os funcionários se cadastram sozinhos com esse código e criam a própria senha.

**O que o diferencia:** a conferência de notas considera a realidade fiscal de Alagoas. Por exemplo, avisa quando um fornecedor de **Maceió cobra frete na nota** (regra da operação, configurável) e leva em conta o **Decreto AL nº 72.101/2020**, que trata dos atacadistas credenciados de medicamentos. A conferência é um **apoio** e não substitui a análise do contador (veja o [FAQ](#-faq)).

> 💡 O projeto é dividido em dois: o backend (`medcota/`) e o frontend (`medcota-web/`). Cada um tem um README detalhado.

<br>

## 🎬 Demonstração


  
  <div align="center">
    <img src="assets/img/tela-medcota.png" alt="Painel do comprador" width="100%">
  </div>




| Perfil | Telas |
|---|---|
| **Vendedor** | Minhas faltas (`/faltas`): lista do dia e lançamento de falta com busca de produto. |
| **Comprador** | Painel, Consolidação, Cotações, Comparativo, Pedidos, **Recebimento** (conferência de NF-e) e Cadastros (produtos e fornecedores). |
| **Gestor** | Tudo do comprador, mais **Equipe** (código de validação, membros e permissões) e aprovação de pedidos. |
| **Fornecedor** | Página pública da cotação (`/c/:token`), sem login. |

<br>

## 🛠️ Tecnologias

**Back-end** (`medcota/`)
- [Python 3.11+](https://www.python.org/) e [FastAPI](https://fastapi.tiangolo.com/) — API tipada, com documentação automática (Swagger)
- [SQLAlchemy 2](https://www.sqlalchemy.org/) — ORM com modelos tipados
- [Pydantic](https://docs.pydantic.dev/) e [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — validação e configuração por variáveis de ambiente
- [PyJWT](https://pyjwt.readthedocs.io/) e [bcrypt](https://pypi.org/project/bcrypt/) — autenticação e hash de senhas
- [defusedxml](https://pypi.org/project/defusedxml/) — leitura segura do XML da NF-e (bloqueia XXE)
- [SlowAPI](https://github.com/laurentS/slowapi) — limite de requisições por IP

**Front-end** (`medcota-web/`)
- [React 19](https://react.dev/) e [TypeScript](https://www.typescriptlang.org/) com [Vite](https://vite.dev/)
- [Tailwind CSS v4](https://tailwindcss.com/) e [shadcn/ui](https://ui.shadcn.com/) — interface minimalista e acessível
- [TanStack Query](https://tanstack.com/query) — dados do servidor; [React Router](https://reactrouter.com/) — rotas com carregamento sob demanda
- [React Hook Form](https://react-hook-form.com/) e [Zod](https://zod.dev/) — formulários e validação

**Banco de Dados**
- [SQLite](https://www.sqlite.org/) no desenvolvimento e [PostgreSQL](https://www.postgresql.org/) recomendado em produção
- [Alembic](https://alembic.sqlalchemy.org/) — migrações

**Qualidade**
- [pytest](https://pytest.org/) e [Ruff](https://docs.astral.sh/ruff/) (back-end) · [Vitest](https://vitest.dev/), [Testing Library](https://testing-library.com/) e [oxlint](https://oxc.rs/docs/guide/usage/linter) (front-end)

<br>

## ✨ Funcionalidades

**Multiempresa e acesso**
- [x] Cadastro de empresa pelo gestor (com CNPJ numérico ou alfanumérico)
- [x] Código de validação único por empresa (gerar, renovar, revogar; com validade)
- [x] Cadastro de funcionários com senha própria (8+ caracteres, maiúscula, minúscula e número)
- [x] Perfis vendedor, comprador e gestor; gestão da equipe e permissão de ver preços
- [x] Isolamento total dos dados entre empresas

**Compras**
- [x] Lançamento de faltas pelo vendedor, com horário de corte e soma de duplicatas
- [x] Consolidação da demanda e cotação por fornecedor via link único
- [x] Comparativo pelo menor **custo final** (preço, desconto financeiro e frete rateado)
- [x] Fechamento da compra e aprovação do gestor acima da alçada
- [x] Cadastro de produtos e fornecedores por empresa

**Recebimento e conferência de NF-e**
- [x] Pedido registrado na tela (comprador e gestor)
- [x] Upload do XML da nota e conferência de preços, quantidades, frete, impostos, totais e autenticidade
- [x] Regra de frete para fornecedores de Maceió/AL e parâmetros fiscais por empresa
- [x] Aceite ou recusa da nota (nota com erro só o gestor aceita, com justificativa)
- [ ] Consulta da situação da nota na SEFAZ (exige certificado digital)
- [ ] Validação integral do Decreto nº 72.101/2020 (depende do texto vigente e do contador, lei do estado de alagoas para empresas no setor de distribuição de medicamentos, falo com mais detalhes no FAQ)

<br>

## ✅ Pré-requisitos

Antes de começar, você vai precisar ter instalado em sua máquina:

- [Git](https://git-scm.com)
- [Python](https://www.python.org/) 3.11 ou superior (testado no 3.12)
- [Node.js](https://nodejs.org/en/) 22 ou superior (testado no 22) e npm
- [PostgreSQL](https://www.postgresql.org/) (opcional: só para produção; no desenvolvimento o SQLite basta)
- Um editor de código, como o [VSCode](https://code.visualstudio.com/)

<br>

## 📦 Instalação

```bash
# Clone este repositório
git clone https://github.com/seu-usuario/seu-repo.git

# Acesse a pasta do projeto
cd seu-repo
```

**Backend (`medcota/`)**

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

**Frontend (`medcota-web/`)**

```powershell
npm install
copy .env.example .env     # ajuste VITE_API_URL se a API não estiver em http://localhost:8000
npm run dev                # http://localhost:5173
```

<br>

## ⚙️ Configuração

**API:** crie o arquivo `.env` em `medcota/` com base no `.env.example` (`copy .env.example .env` no Windows, `cp .env.example .env` no Linux/macOS):

```env
# Aplicação
AMBIENTE=desenvolvimento            # desenvolvimento | teste | producao
DATABASE_URL=sqlite:///./medcota.db

# Autenticação (obrigatório: mínimo de 32 caracteres)
# Gere com: python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET=troque-por-um-segredo-aleatorio-com-pelo-menos-32-caracteres

# Origens permitidas do frontend (lista em JSON)
CORS_ORIGENS=["http://localhost:5173","http://localhost:3000"]

# Regras de negócio
ALCADA_APROVACAO=5000               # pedidos acima disso precisam do gestor
HORARIO_CORTE=17:00                 # fim da lista de faltas do dia
FUSO_HORARIO=America/Maceio
CODIGO_VALIDADE_DIAS=7              # validade do código de cadastro de funcionários

# Recebimento de NF-e
NFE_MAX_BYTES=2000000               # tamanho máximo do XML
```

O `.env.example` traz também limites de requisição, bloqueio de conta, tempo de sessão e nível de log.

**Frontend:** crie o `.env` em `medcota-web/`:

```env
# URL base da API (sem barra no final)
VITE_API_URL=http://localhost:8000
```


<br>

## ▶️ Como Usar

**1. Prepare o banco e (opcionalmente) crie dados de demonstração** — na pasta `medcota/`:

```bash
alembic upgrade head      # cria as tabelas
python -m app.seed        # só em desenvolvimento: empresa de exemplo
```

O `seed` cria a empresa **Distribuidora Demo** com um gestor, um comprador e um vendedor (`carla@`, `bruno@` e `ana@` + `medcota.com.br`), produtos, fornecedores e um código de validação. A **senha é gerada e mostrada uma única vez** no terminal (ou defina `SEED_SENHA`).

**2. Suba o backend** (`medcota/`):

```bash
uvicorn app.main:app --reload
```

**3. Suba o frontend** (`medcota-web/`):

```bash
npm run dev
```

Após rodar os comandos, a aplicação estará disponível em:

- Frontend: `http://localhost:5173`
- API e documentação interativa (Swagger): `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/saude`

### Primeiro uso (sem o seed)

1. Abra `/cadastro/empresa` e cadastre a empresa (você será o gestor).
2. Em **Equipe**, gere o **código de validação** e compartilhe com os funcionários.
3. Cada funcionário abre `/cadastro/funcionario`, informa o código, escolhe vendedor ou comprador e cria a própria senha.
4. Em **Cadastros**, registre produtos e fornecedores (informe o CNPJ do fornecedor para conferir as notas).
5. O vendedor lança faltas; o comprador consolida, cota, compara e fecha a compra. Quando a mercadoria chega, use **Recebimento** e envie o XML da nota.

### Exemplos de uso da API

Login (devolve o token de acesso):

```bash
curl -X POST http://localhost:8000/auth/login -d "username=bruno@medcota.com.br&password=SUA_SENHA"
```

Registrar um pedido e enviar a nota fiscal para conferência:

```bash
# registra o pedido
curl -X POST http://localhost:8000/recebimento/pedidos \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"fornecedor_id": 1, "frete_previsto": "0", "itens": [{"produto_id": 1, "quantidade": 10, "preco": "10.00"}]}'

# envia o XML da nota (campo multipart "arquivo")
curl -X POST http://localhost:8000/recebimento/pedidos/1/nfe \
  -H "Authorization: Bearer $TOKEN" -F "arquivo=@nfe.xml"
```

Resposta (resumo): o resultado da conferência e a lista de apontamentos.

```json
{
  "resultado": "reprovada",
  "decisao": "pendente",
  "erros": 1,
  "apontamentos": [
    {
      "severidade": "erro",
      "codigo": "FRETE_INDEVIDO",
      "mensagem": "Fornecedor de Maceió/AL não cobra frete na nota, mas a nota traz frete de R$ 50,00.",
      "esperado": "0,00",
      "encontrado": "50.00"
    }
  ]
}
```

Todos os endpoints, perfis e códigos de erro estão no [README do backend](./medcota/README.md).

<br>


## 🧪 Testes

```bash
# API (na pasta medcota/): 230 testes
pytest
ruff check .

# Frontend (na pasta medcota-web/): 84 testes
npm test
npm run lint
npm run build          # confere os tipos (tsc) e gera o build de produção
```

Destaques da cobertura:

- **Isolamento entre empresas:** duas empresas operando em paralelo, inclusive tentativas de acessar ou alterar dados da outra por ID.
- **Conferência fiscal:** cada regra é testada partindo de uma nota correta e injetando um defeito por vez.
- **Segurança do upload:** XML malicioso (XXE/DTD), arquivo grande, vazio, inválido e nota duplicada.
- **Permissões:** o vendedor é barrado em todas as rotas do módulo de recebimento.
- **Migrações:** upgrade sem divergência dos modelos, dados antigos preservados e downgrade completo.

<br>

## 🚀 Deploy

O repositório **ainda não inclui** Dockerfile nem pipeline de CI/CD. Para colocar em produção hoje:

```bash
# API: use PostgreSQL e as variáveis de produção
pip install -e ".[postgres]"
# .env: AMBIENTE=producao, DATABASE_URL=postgresql+psycopg://usuario:senha@host/medcota,
#       JWT_SECRET forte e CORS_ORIGENS com o domínio real (sem "*")
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers

# Frontend: gera os arquivos estáticos em medcota-web/dist
npm run build
```

Pontos de atenção:

- Atrás de proxy/Nginx, use `--proxy-headers` para o limite de requisições enxergar o IP real do cliente.
- O bloqueio contra compra duplicada (`SELECT ... FOR UPDATE`) só tem efeito no PostgreSQL.
- **Não rode o `seed` em produção** (ele recusa).
- Sirva a pasta `dist/` do frontend por um servidor estático e aponte `VITE_API_URL` para a API antes do build.





## 🤝 Como Contribuir

Contribuições são sempre bem-vindas!

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Faça o commit das suas alterações (`git commit -m 'feat: adiciona MinhaFeature'`)
4. Faça o Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

Antes de abrir o PR, confirme que tudo passa: `pytest` e `ruff check .` na API; `npm test`, `npm run lint` e `npm run build` no frontend. Mudanças no banco precisam de uma migração Alembic, e regras novas da conferência fiscal precisam de teste.

<br>

## ❓ FAQ

**Como a empresa e os funcionários entram no sistema?**
O gestor cadastra a empresa e gera o código de validação na tela *Equipe*. Os vendedores e compradores se cadastram em `/cadastro/funcionario` com esse código e criam a própria senha. O código é único por empresa, tem validade, pode ser renovado ou revogado e nunca permite criar um gestor.

**Qual é a regra de senha?**
Mínimo de 8 caracteres, com pelo menos uma letra maiúscula, uma minúscula e um número (máximo de 72 bytes).

**O vendedor enxerga a conferência de notas?**
Não. O módulo de recebimento é exclusivo de comprador e gestor, e também exige a permissão de ver preços e custos.

**O sistema garante que a nota está correta perante o Fisco?**
Não. É uma conferência automática de apoio: confere o que está **dentro do XML** (contas de impostos, totais, CFOP/CST, preços, frete, chave de acesso) e compara com o pedido. Ela **não consulta a SEFAZ** (cancelamento e denegação) e **não substitui o contador**.

**O que o sistema faz com o Decreto nº 72.101/2020 (Alagoas)?**
O decreto dá tratamento diferenciado de ICMS a atacadistas credenciados de medicamentos, e o ponto central é o recolhimento **mensal** do atacadista, que não aparece na nota. O sistema confere o que está destacado nela e avisa esse limite quando o fornecedor é marcado como credenciado. Nenhuma alíquota do decreto está gravada no código: elas ficam em **Parâmetros fiscais**, mantidos pelo gestor ou contador. O texto consolidado do decreto não pôde ser lido por inteiro durante o desenvolvimento, então valide as regras com o contador.

**Por que o frete de fornecedor de Maceió vira erro?**
É uma regra da operação da empresa (distribuidoras de Maceió não cobram frete na nota), baseada no código IBGE do município do emitente. Os municípios são configuráveis; uma lista vazia desliga a regra.

**O sistema aceita o CNPJ alfanumérico?**
Sim, no cadastro da empresa, no cadastro de fornecedores e na chave de acesso da nota.

**Posso usar outro banco além do SQLite?**
Sim. Use PostgreSQL em produção (`pip install -e ".[postgres]"` e ajuste `DATABASE_URL`).

<br>


## 📬 Contato

<div align="center">

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/márcio-henrique-dev/)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:marciomind19@gmail.com)


</div>
<br>

## 🙏 Agradecimentos

- [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://www.sqlalchemy.org/) e [Alembic](https://alembic.sqlalchemy.org/)
- [shadcn/ui](https://ui.shadcn.com/), [Radix UI](https://www.radix-ui.com/) e [Tailwind CSS](https://tailwindcss.com/) pela base da interface
- [TanStack Query](https://tanstack.com/query), [React Router](https://reactrouter.com/), [React Hook Form](https://react-hook-form.com/) e [Zod](https://zod.dev/)
- [Manual de Orientação do Contribuinte da NF-e](https://www.legisweb.com.br/legislacao/?id=405632) e a legislação do ICMS, base das regras de conferência

