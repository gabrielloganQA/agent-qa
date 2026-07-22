# Convenções de Testes Automatizados — AtlanteX

> Contrato do time para escrever, organizar e revisar testes automatizados.
> Vale para **toda** spec nova ou refatorada. PRs que ferirem estas regras voltam.

Stack de referência: **Playwright** (projetos `api` e `e2e`). Infra compartilhada em
`tests/support/`. Se o projeto usar outro framework, os **princípios continuam
valendo** — adapte apenas caminhos, runner e plugin de lint.

---

## Regra de ouro (o princípio que rege todas as outras)

> **Um teste deve falhar se, e somente se, a intenção do sistema não for cumprida.**
> — [The Golden Rule of Assertions](https://www.epicweb.dev/the-golden-rule-of-assertions)

Antes de escrever um `expect`, pergunte: **"quando este teste vai falhar?"**
Se a resposta não for *"quando o comportamento que eu quero garantir quebrar"*, a
assertion está errada. Consequências práticas:

- Asserir no **resultado/contrato**, nunca em *como* o backend faz (nome de serviço,
  query, hash de commit — isso não é do teste).
- Nada de skip/condicional que faça o teste passar **sem** exercitar a intenção.
- Assertion específica sobre **valor exato**, com mensagem que explica a intenção.

---

## 1. Independência

Cada teste roda **sozinho, em qualquer ordem, em paralelo**, sem depender de outro.

- **Prepare o estado no `beforeEach`/fixture**, não no teste anterior. Nunca assuma
  que um teste deixou algo pronto para o próximo.
- **Massa via API, alvo via GUI.** A pré-condição (usuário, produto, saldo) é criada
  pela via mais barata — a `factory`/`fresh-tenant` (API). A tela é usada **só** para
  o que está sendo testado. Criar massa clicando é lento, frágil e proibido.
- **Login uma vez** (`global-setup`) com token compartilhado; testes que exercitam o
  próprio login usam usuário dedicado (frota `qa.bot`) para não despejar a sessão.
- **Sem `describe.serial`** — exceto contenção física real e comprovada (ex.: escrita
  concorrente na mesma localização). Quando usar, comente **uma linha** com o porquê.
  Serial nunca é desculpa para um teste depender do estado deixado por outro.

```ts
// ✅ cada teste semeia o seu; roda isolado
test.beforeEach(async ({ factory }) => { material = await factory.material(); });
```

---

## 2. Sem condicionais (cenários separados, não `if`)

Ramificação em teste só em caso **extremo**. Cenários diferentes = **testes
diferentes**, não `if/else` no corpo.

- ❌ **Proibido `test.skip("precondição ausente: ...")` que passa verde.** Um teste
  que se auto-desliga quando falta massa não testa nada e mente no relatório. **Semeie
  a pré-condição via API.** Se o estado for genuinamente não-montável na camada de API
  (job assíncrono, fluxo multipart, passo do operador no coletor), então **o cenário
  não é um teste de API** — ele pertence ao E2E, ou não existe. Não deixe green-skip.
- ❌ **Proibido `if (semDado) return`** para escapar.
- Precondição que é **dado de referência** (existe sempre no ambiente: UoM, NCM, tipo
  de OS) → trate como *lookup* e **asserte** que existe (`expect(x).toBeTruthy()`).
  Vermelho por ambiente quebrado é resultado legítimo; skip silencioso não.
- Um seed/ato que falhou (`!res.ok()`) é **falha do teste** → `expect(res.ok())`, não skip.

```ts
// ❌  const dep = await findDeposit(); test.skip(!dep, "sem depósito");
// ✅  const dep = await freshStock.deposit();  // semeia o que precisa
//     expect(dep.id, "tenant fresh sempre provisiona um depósito").toBeTruthy();
```

---

## 3. Estrutura e nomes das suítes

Organize em árvore legível: **`describe` (feature) › `describe` (sub-fluxo) › `test`
(caso)**. O nome do teste descreve **o comportamento**, não o método.

```
describe  Autenticação de Usuário
  describe  Login
    test    realiza login com credenciais válidas
    test    exibe erro ao tentar login com senha incorreta
  describe  Registro
    test    registra novo usuário com dados válidos
    test    exibe erro ao registrar e-mail já usado
```

- **Um arquivo por feature**, não um arquivo por micro-cenário. Testes da mesma
  feature moram juntos, agrupados por `describe`.
- Título de teste = frase de comportamento em minúsculas: *"desconta o reservado do
  disponível"*, não *"testa GetQuantitativeReportRawQuery"*.

---

## 4. Nível dos testes (a pirâmide)

Muitos testes rápidos embaixo (API), poucos e caros em cima (E2E). Alvo: **~80% API,
~20% E2E**.

> A API testa se o sistema **faz** a coisa certa.
> A UI testa se a tela **deixa o usuário fazer e ver** a coisa certa.
> Nunca teste a mesma regra nas duas camadas.

- Regra/cálculo/persistência/estado/RBAC → **API**.
- "Aparece na tela / o clique dispara / o form dá feedback" → **E2E**.

---

## 5. Abstração

Siga a regra de ouro (topo). Assertion focada na **intenção** é naturalmente mais
legível e some com o teste frágil. Não asserte detalhe de implementação; asserte o
contrato observável (status, corpo, o que a tela mostra).

### The Wrong Abstraction (Sandi Metz)

> **"Duplicação é muito mais barata que a abstração errada."**
> **"Prefira a duplicação a uma abstração errada."**
> — [The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction)

O ciclo que produz a abstração errada: alguém vê duplicação e extrai um helper; o
requisito muda e o helper fica *quase* certo; em vez de refazer, o próximo adiciona um
**parâmetro/flag/condicional**; repita — o helper vira um novelo de `if`s que ninguém
entende. Some a isso o **custo afundado** (dá dó apagar código que deu trabalho) e o
novelo nunca é removido.

Recomendação da Sandi (e nossa regra): quando encontrar a abstração errada, **o caminho
para a frente é para trás** — reintroduza a duplicação: faça *inline* do helper de volta
em cada chamador, e só então, com os casos concretos à vista, derive a abstração certa
(ou nenhuma). **Está tudo bem duplicar enquanto a abstração certa não estiver óbvia.**

Aplicado a testes (e helpers de `_helpers.ts`/factory):

- **Semelhança não é igualdade de intenção.** Dois testes que parecem iguais hoje podem
  divergir amanhã — não os funda num helper só porque o código coincide.
- **Um helper de teste que ganha parâmetro booleano/flag para servir dois chamadores é o
  sinal da abstração errada.** Faça inline e deixe cada teste explícito. `seedStock(x)`
  bom; `seedStock(x, { started, blocked, withReserve })` ruim.
- **DAMP > DRY em teste** (*Descriptive And Meaningful Phrases*). O teste deve ser
  legível de cima a baixo **sozinho**; um pouco de repetição explícita é preferível a
  ter que caçar o que um helper faz. Abstraia só o que é **estável e sem intenção**
  (login, montar payload padrão, criar massa base), nunca o *corpo do cenário*.
- Consolidar arquivos (regra 3) **não** é DRY do conteúdo: os testes moram no mesmo
  arquivo, mas cada um continua explícito e independente.

---

## 6. Assertions

- **Específicas e descritivas.** Valor exato + mensagem ligada ao objetivo.
- Verifique **comportamento** (estado + o que o sistema faz), não só "não deu erro".

```ts
// ❌ vago
expect(res.ok()).toBeTruthy();
expect([200, 201]).toContain(res.status());     // "aceita qualquer um"

// ✅ específico, com a intenção na mensagem
expect(res.status(), "criar contraparte PJ válida").toBe(201);
expect(rep.available, "disponível = físico − reservado").toBe(N - RESERVE);
// e2e — comportamento visível
await expect(page).toHaveURL(/\/dashboard/);
await expect(page.getByRole("heading", { name: /bem-vindo/i })).toBeVisible();
```

---

## 7. Massa via API (rápida e barata)

A criação da massa deve ser **tão ou mais rápida** que o próprio teste. Use `factory`
e `fresh-tenant` para materializar qualquer estado (`counterparty` criado, saldo
injetado, tenant do zero) por chamada de API — nunca pela tela. Isso evita
over-testing, mantém o teste focado e mata o flaky.

- Toda massa nasce com **código único** (`testCode`/`data.key()`) → sem colisão em
  ambiente compartilhado.
- Toda criação registra **cleanup**; o teardown roda em ordem reversa.
- IDs de referência são **descobertos em runtime** (`lookups`), nunca hardcoded.

---

## 8. Curto vs. longo

- **API — curto e focado:** uma funcionalidade isolada, rápido, fácil de diagnosticar.
  A maioria da suíte.
- **E2E — longo e abrangente:** fluxo de usuário ponta-a-ponta (login → cadastra na
  tela → vê na listagem). Poucos, caros, semeados via API, testando só o passo de tela.

Ambos são necessários; cada um no seu papel.

---

## 9. Convenções de arquivo, lint e AAA

### Estrutura de pastas
```
tests/
  support/        infra (auth, fixtures, factory, lookups, fresh-tenant)
  api/<módulo>/   testes de integração HTTP  (kebab-case, .spec.ts)
  e2e/<módulo>/   fluxos no browser          (kebab-case, .spec.ts)
```
- **Nomes em kebab-case**, descritivos e completos: `stock-adjustments.spec.ts`,
  nunca `registrationscounterpartie.spec.ts` (truncado/ilegível).
- Helpers de módulo em `_helpers.ts`. Nada de arquivos `_probe*`/sondas versionados.

### AAA (Arrange · Act · Assert)
Todo teste segue as três fases, visíveis pela estrutura (linha em branco separando).
Comentário `// Arrange`/`// Act`/`// Assert` **só** quando o teste é longo e a fronteira
não é óbvia.

```ts
test("desconta o reservado do disponível", async ({ freshStock, factory }) => {
  const material = await factory.material({ productFamilyId: freshStock.familyId });
  await freshStock.seedStock(material, 10);

  await freshStock.reserve(material, 4);

  const stock = await freshStock.report(material);
  expect(stock.reserved, "reserva ativa da OS").toBe(4);
  expect(stock.available, "disponível = físico − reservado").toBe(6);
});
```

### Lint (convenções da ferramenta)
- `eslint-plugin-playwright` no CI: barra `no-conditional-in-test`,
  `no-skipped-test` mal-justificado, `no-wait-for-timeout`, `expect-expect`.
- Rodar `npm run lint` antes de subir; CI reprova o merge se falhar.

---

## Comentários — disciplina

**O teste se explica pelo título + pelas assertions.** Se precisa de um parágrafo para
entender o que ele faz, o teste está mal escrito — conserte o teste, não adicione
comentário.

- ❌ **Não** documente o backend na spec: hash de commit, nome de CTE/serviço/tabela,
  "o fix 97c8ee49 adicionou reserved_aggregates...". Isso apodrece e polui.
- ❌ **Não** narre o óbvio: `// cria material`, `// faz o GET`.
- ✅ Comente **só o "porquê" não-óbvio**: uma decisão contra-intuitiva, uma pegadinha
  do ambiente, o motivo de um `serial`. Uma linha.

```ts
// ❌ ANTES — 20 linhas de docstring explicando a query do backend
/**
 * Cobre o fix backend 97c8ee49 ("desconta reservado em AvailableQuantity")...
 *   StockDAO.GetQuantitativeReportRawQuery ganhou a CTE `reserved_aggregates`...
 */

// ✅ DEPOIS — uma linha de intenção; o resto é o próprio teste
/** Relatório de estoque: disponível desconta o reservado por OS ativa. */
```

---

## Estrutura-alvo (consolidação)

Specs fragmentadas (um arquivo por micro-cenário) devem ser agrupadas por feature em
um `describe` com sub-suítes.

> Consolidar ≠ amontoar: cada teste continua **independente** (seu próprio seed no
> `beforeEach`/fixture). O ganho é navegação e a árvore de suítes da regra 3.

---

## Como rodar

```bash
npm run test:api      # camada de API — gate rápido de PR
npm run test:e2e      # E2E no Chromium (npx playwright install chromium)
npm run test:pw       # tudo
npm run test:report   # último relatório HTML
npm run lint          # convenções (linguagem + Playwright)
```
