# Padrão — criação automática de BUG no RISE

Instalação: `https://ap.atlantex.com.br/index.php` · levantado em 21/07/2026
Tudo abaixo foi verificado contra a instalação real, criando e removendo tasks de teste.

> ## ✅ Resumo
>
> **Funciona.** A criação é feita pelos **endpoints internos** do RISE
> (`/tasks/save`), autenticando por sessão — não pela REST API do plugin, que
> nesta instalação é somente leitura.
>
> Script pronto: [`rise_bug.py`](../rise_bug.py)
>
> ```bash
> python3 rise_bug.py "Título do bug" "<p>Descrição</p>" --priority 3
> # → bug criado: #3495  projeto=9  coluna=BUGs  prioridade=Critica
> ```

---

## 1. Por que não pela REST API do plugin

A rota oficial (`POST /api/tasks`, documentada pela Themesic) **não existe** nesta
instalação:

```
POST /api/tasks   → {"status":false,"code":404,"message":"Route not found"}
GET  /api/tasks   → 200 OK
```

Testado exaustivamente, sempre com o mesmo resultado:
- 3 content-types (`multipart`, `json`, `urlencoded`)
- com e sem barra final
- 9 namespaces alternativos (`/api/v1/`, `/api/tasks/create`, `/api/task/add`…)
- **2 tokens diferentes** (o do `joao.andrade` e um novo criado no nome `QA`)

Não é permissão nem token — é a rota que não está registrada.

**Inventário:** das 216 rotas documentadas, esta instalação expõe **23, todas GET**.
Grupos inteiros ausentes: Milestones, Timesheets, Notes, Users, Contacts, Labels,
Expenses, Estimates, Proposals, Orders, Contracts, TicketComments…

**Diagnóstico provável:** plugin instalado (a pasta `RestApi` existe no servidor)
mas não ativado por completo, ou licença expirada. Corrigir exige admin
(`Settings → Plugins` → Forbidden para o usuário QA).

> A REST API **continua útil para leitura** — o script usa `GET /api/tasks` para
> conferência. Se o plugin for destravado no futuro, migrar a escrita é trocar
> uma função; o padrão de dados abaixo não muda.

### Também não é Ticket

A hipótese inicial era `POST /api/tickets`. Descartada:

| Verificação | Resultado |
|---|---|
| `POST /api/tickets` aceita `project_id`? | Não existe o campo |
| Existe ticket type "Bug"? | Não — só `[{id:1,"Suporte"}]` |
| Existem ticket labels? | Nenhuma |

A coluna "BUGs" é **coluna de kanban de tasks**, não agrupamento de tickets.

---

## 2. A solução: endpoints internos

São as rotas que a própria interface web usa. Descobertas inspecionando o
`data-action-url` do botão "Add tarefa" no board.

| Rota | Método | Uso |
|---|---|---|
| `/signin/authenticate` | POST | login → cookie de sessão |
| `/tasks/modal_form` | POST | devolve o formulário (fonte dos nomes de campo) |
| **`/tasks/save`** | **POST** | **cria/edita a task** |
| `/tasks/delete` | POST | remove (`id=N`) |
| `/tasks/project_tasks_kanban_data/:id` | POST | dados do board |

### Login

```
POST /signin/authenticate     email, password, redirect
  sucesso → 302 Location: /dashboard/view
  falha   → 302 Location: /signin
```

Não retorna JSON. **Detectar sucesso pela URL final do redirect.**

### Criação

```
POST /tasks/save
Content-Type: application/x-www-form-urlencoded
X-Requested-With: XMLHttpRequest
```

| Campo | Valor no padrão | Nota |
|---|---|---|
| `title` | `BUG - <resumo>` | prefixo automático no script |
| `description` | — | aceita HTML |
| `project_id` | `9` | WMS |
| `status_id` | **`5`** | coluna **BUGs** |
| `assigned_to` | `12` | Gabriel Logan (QA Lead) |
| `priority_id` | `2` | Alta |
| `context` | `project` | **obrigatório** |
| `points` | `1` | — |
| `id`, `add_type`, `client_id`, `ticket_id` | *vazios* | precisam existir no payload |
| `milestone_id`, `labels`, `collaborators` | *vazios* | opcionais |
| `start_date`, `start_time`, `deadline`, `end_time` | *vazios* | opcionais |

**Resposta de sucesso:** `{"success":true,"data":[...]}` — o `data` traz HTML
renderizado da linha; o ID sai do primeiro `data-id="NNNN"`.

> ✅ **Não exige CSRF token.** Testado sem `rise_csrf_token` — criou normalmente.
> Simplifica muito a automação (não precisa buscar token antes de cada POST).

---

## 3. IDs de referência

### Projeto
`project_id = 9` → **WMS** (client_id 2)

> ⚠️ Existe também **id 22 — "WMS IHS I-SYSTEMS"** (client 5). Projeto diferente.

### ✅ Colunas do kanban são GLOBAIS

Verificado nos projetos 9, 22, 31 e 13 — IDs idênticos.
**A automação atende qualquer projeto trocando só o `project_id`.**

| status_id | Coluna | No kanban |
|---|---|---|
| 4 | Backlog do Produto | oculta |
| 6 | Backlog | sim |
| **5** | **BUGs** ⬅️ alvo | sim |
| 7 | Em Desenvolvimento | sim |
| 8 | Em Code Review (PR aberto) | sim |
| 9 | Stage - DEV | sim |
| 10 | Homolog - QA | sim |
| 11 | Testado HOMOLOG | sim |
| 3 | Done | sim |
| 2 | In progress | oculta |
| 1 | To Do | oculta |

### Prioridades

| id | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| | Baixa | Alta | Critica | Bloqueada |

### Membros do projeto 9

| user_id | Nome | Papel |
|---|---|---|
| 1 | João Andrade | Suporte (leader) |
| 2 | Leo Nunes | CEO |
| 3 | Luciana Moraes | PM Lead |
| 4 | Adolfo Almeida | PM |
| **12** | **Gabriel Logan** | **QA Lead** ← default |
| 14 | Hiago Azevedo | QA |
| 16 | Thiago Carvalho | Front-end |
| 17 | Gabriel Ferreira | Desenvolvedor |
| 20 | Alandysson Rolim | Desenvolvedor |
| 37 | Pedro Henrique dos Santos | QA |
| 38 | Pedro Santos | QA |

### Convenção de título

Extraída das tasks reais da coluna:

```
BUG — Cliente em uso pode ser inativado, fornecedor em uso não
MELHORIA DE UX — Prevenir perda de dados ao utilizar BACK em modais
```

Prefixo em CAIXA ALTA + separador + descrição. O script aplica `BUG - ` (hífen
ASCII — ver armadilha 4.5).

---

## 4. ⚠️ Armadilhas

### 4.1 Erros retornam HTTP 200 — nunca confie no status code

```
authtoken inválido → HTTP 200 {"status":false,"message":"Wrong number of segments"}
sem authtoken      → HTTP 200 {"status":false,"message":"Token is not defined."}
rota inexistente   → HTTP 200 {"status":false,"code":404,"message":"Route not found"}
```

Um cliente que faz `if (res.ok)` trata **falha de autenticação como sucesso**.
➡️ Validar sempre o corpo (`success`/`status`), nunca só o código HTTP.

### 4.2 Sem paginação

`limit`, `offset`, `page`, `per_page` são todos ignorados.
`GET /api/tasks` devolve **4.1 MB** sempre; com `project_id=9`, 1.2 MB / 700 tasks.

### 4.3 Filtros que não funcionam

- `?status_id=5` → **ignorado**
- `?id=3283` → **ignorado**, e derruba o filtro de projeto (volta 4.1 MB)
- `?project_id=N` → **funciona** ✅ (único confiável)

### 4.4 Rotas de leitura quebradas

- `GET /api/tasks/:id` → `Route not found` (documentado, inexistente)
- Todos os `/search/:keyword` → **HTTP 500**

### 4.5 O travessão `—` derruba a conexão

`POST` com em-dash no `title` deu **HTTP 000** (conexão abortada, provável WAF).
Com hífen ASCII passou. ➡️ Usar `-`, não `—`.

### 4.6 Sessão expira

O cookie tem validade. Automação de longa duração precisa relogar ao detectar
redirect para `/signin`.

---

## 5. Uso do script

```bash
# criar
python3 rise_bug.py "Título do bug" "<p>Passos, esperado vs obtido</p>"

# outro projeto / prioridade / responsável
python3 rise_bug.py "Título" "Desc" --project 31 --priority 3 --assign 17

# remover
python3 rise_bug.py --delete 3495
```

Requer no `.env`:

```
RISE_BASE_URL=https://ap.atlantex.com.br/index.php
RISE_USER=<email>
RISE_PASSWORD=<senha>
RISE_AUTH_TOKEN=<token>    # opcional, só para leitura via REST API
```

---

## 6. Pendências

- [ ] **Trocar a senha** — foi usada em chat durante o levantamento
- [ ] **Revogar o token antigo** (`joao.andrade`) — vazou e continua ativo
- [ ] Pedir ao João a versão/licença do plugin REST API — se destravar, migrar a
      escrita de `/tasks/save` para `POST /api/tasks` (só troca a função `create_bug`)
- [ ] Definir o gatilho da automação (o que dispara a criação do bug)

---

## Anexo

Referência das 216 rotas documentadas pelo fabricante (≠ do que está instalado):
[`RISE_CRM_API_endpoints.md`](./RISE_CRM_API_endpoints.md)
