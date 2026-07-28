# Escrita de teste automatizado — teste limpo

Três arquivos, três perguntas:

- `.claude/skills/design-casos-teste/SKILL.md` → **o que** testar (técnicas de derivação)
- [`camadas-e-automacao.md`](camadas-e-automacao.md) → **onde** o cenário é provado
- este arquivo → **como** o teste é escrito

As convenções internas do time ([`docs/CONVENCOES-AUTOMACAO.md`](../../../../docs/CONVENCOES-AUTOMACAO.md):
caminhos, runner, lint, nomes de pasta) continuam sendo a fonte da verdade. Aqui está o
princípio por trás de cada regra, o catálogo de defeitos de escrita que a revisão de PR
precisa pegar, e os checklists que permitem reprovar um PR sem discussão de gosto pessoal.

---

## 1. O critério único

> **Um teste deve falhar se, e somente se, a intenção do sistema não for cumprida.**

Antes de escrever qualquer `expect`, responda: *quando este teste vai falhar?* Se a
resposta não for "quando o comportamento que eu quero garantir quebrar", a asserção está
errada.

Os dois modos de falha, igualmente graves:

| Falha | O que acontece | Como nasce |
|---|---|---|
| **Falso negativo** | Passa verde com o sistema quebrado | Asserção fraca, skip condicional, teste tautológico |
| **Falso positivo** | Falha sem existir defeito | Acoplamento a implementação, dado compartilhado, espera por tempo |

Um teste que nunca falha e um teste que falha sozinho são o mesmo problema visto de dois
lados: **perda de sinal**. Suíte sem sinal é custo puro.

### O teste do teste

Antes de aprovar qualquer teste — seu, de outra pessoa ou gerado por IA — **quebre o
comportamento de propósito e confirme que ele fica vermelho.** Trocar o valor esperado,
inverter uma condição, comentar a regra no serviço. Teste que continua verde com o sistema
quebrado não é teste, é decoração. Trinta segundos de verificação por caso novo.

### Um motivo para falhar

Não é "uma asserção por teste" — é **um comportamento por teste**. Três asserções sobre o
mesmo comportamento (status, corpo e efeito colateral da mesma operação) são um teste
saudável. Três asserções sobre três comportamentos diferentes são três testes.

---

## 2. Nome e estrutura

**O nome descreve comportamento, não método.** Testar por método público é granularidade
errada: `testCalcularDesconto()` não diz o que deveria acontecer e amarra o teste ao nome
interno da função — quando o método é renomeado, o teste mente.

```
❌ testa GetQuantitativeReportRawQuery
❌ teste 3 do cupom
✅ desconta o reservado do disponível
✅ recusa cupom expirado e mantém o valor original do pedido
```

Padrão de frase: **`<resultado observável>` quando `<condição>`**, em minúsculas, sem
jargão de implementação. Em Gherkin, o título do cenário é o "Então" em uma linha.

**Árvore legível:** `describe` (feature) › `describe` (sub-fluxo) › `test` (caso). Um
arquivo por feature, não um arquivo por micro-cenário.

**AAA (Arrange · Act · Assert)** visível pela estrutura — uma linha em branco separando as
três fases. Se o teste tem duas fases de Act, ele é dois testes.

---

## 3. Completo e conciso

Duas exigências que puxam para lados opostos e precisam ser satisfeitas juntas:

- **Completo:** tudo que o leitor precisa para entender o teste está no corpo dele.
- **Conciso:** nada além disso está no corpo dele.

**Mystery Guest** — o teste depende de algo que o leitor não vê: um registro que "já existe
no ambiente", uma fixture solta, um ID mágico. Quebra quando alguém mexe no ambiente e
ninguém entende por quê.

```ts
// ❌ de onde veio o 4321? por que esse pedido?
const pedido = await api.get('/pedidos/4321');

// ✅ o teste semeia o que precisa, e o leitor vê a condição
const pedido = await factory.pedido({ total: 299.99 });   // abaixo do mínimo do cupom
```

**General Fixture** — um `beforeEach` que monta o mundo inteiro porque algum teste do
arquivo precisa. Cada teste semeia só o que usa.

**Irrelevant Information** — payload com 12 campos quando 2 importam. O que está escrito no
teste é o que o leitor assume ser relevante.

---

## 4. Abstração — onde quase toda suíte apodrece

Depois de flaky, abstração errada é o que mais mata suíte de teste — e, diferente do flaky,
ela não dá sinal: a suíte continua verde enquanto fica progressivamente impossível de manter.

### 4.1 O espectro

```
ANA ─────────────── AHA ─────────────── DRY
sem                evite abstração      não repita
abstração          precipitada          nada
```

- **ANA (Absolutely No Abstraction):** copiar e colar. Dois testes de 60 linhas quase
  idênticos e ninguém consegue dizer o que muda entre eles.
- **DRY levado ao extremo:** um utilitário que serve a todos os casos, cheio de flags.
  Ninguém entende o que um teste faz sem abrir três arquivos.
- **AHA (Avoid Hasty Abstraction):** o meio. Abstraia quando a duplicação já revelou a
  forma certa — não antes.

> Alguém precisa de um teste novo → copia o mais parecido → **(ANA)** ajusta os 60 valores
> ou **(DRY)** acrescenta mais um `if` no helper → revisor vê verde e aprova → repete por
> dois anos.

### 4.2 O teste decisivo

> **Quão fácil é dizer qual é a diferença entre dois testes parecidos, e o que causa essa
> diferença?**

Se para responder isso você precisa comparar dois blocos de 60 linhas caçando o campo que
mudou, está em ANA. Se precisa abrir o helper, seguir três parâmetros e descobrir o que a
flag faz, está em DRY. O ponto certo é quando a diferença **salta aos olhos na primeira
leitura**.

### 4.3 As abstrações que quase sempre valem

**Test Object Factory / `setup(overrides)`** — defaults sensatos, e o teste sobrescreve
**apenas o que importa para a regra**:

```ts
// ❌ ANA: qual é a diferença entre este teste e o de baixo?
const pedido = { total: 200, cliente: {...15 campos...}, itens: [...], frete: {...} };

// ✅ AHA: a diferença é o total, e ela está gritando na tela
const pedido = await factory.pedido({ total: 299.99 });   // abaixo do mínimo
const pedido = await factory.pedido({ total: 300.00 });   // no limite
```

**Custom assertion** — asserção nomeada que expressa a regra: `expectDescontoNaoAplicado(pedido)`.

**Tabela de casos (`test.each` / `Esquema do Cenário`)** — para partição e BVA.

O critério não é "isso remove linhas?", é **"isso torna a diferença entre os testes mais
óbvia?"**.

### 4.4 Quando a abstração está errada — sinais objetivos

Qualquer um destes é motivo suficiente para reprovar em revisão:

- [ ] Helper com **parâmetro booleano ou flag**: `seedStock(x, { started, blocked })`.
- [ ] Precisa abrir **três arquivos** para entender um teste de dez linhas.
- [ ] Helper chamado **uma única vez** — abstração criada "para o futuro".
- [ ] Nome genérico: `utils`, `helpers`, `common`, `base`.
- [ ] **Wrapper que só renomeia a API da ferramenta** (`clicar(x)` → `page.click(x)`).
- [ ] **Herança** em objeto de teste (`BasePage` → `MainPage` → `CheckoutPage`).
- [ ] Asserção escondida dentro do helper.

Quando encontrar a abstração errada, **o caminho para a frente é para trás**: faça inline
do helper em cada chamador e, com os casos concretos à vista, derive a abstração certa — ou
nenhuma.

**Com dois ou três testes curtos no arquivo, qualquer abstração é prematura.**

### 4.5 Aninhamento, hooks e variável mutável

```ts
// ❌ para saber o valor de `pedido` no teste, você rastreia 3 beforeEach
describe('checkout', () => {
  let pedido;
  beforeEach(() => { pedido = criarPedido(); });
  describe('com cupom', () => {
    beforeEach(() => { pedido = aplicarCupom(pedido); });   // reatribuição
```

O problema não é estético: é ter que **manter na cabeça o valor das variáveis ao longo do
tempo** enquanto se lê o teste.

- Prefira **função `setup()` chamada dentro do teste** a `let` + `beforeEach`. `const`.
- **No máximo um nível** de `describe` aninhado além do da feature.
- `beforeEach` fica para o idêntico e sem intenção (autenticação, tenant, limpeza).
- **Nunca** reatribua no `beforeEach` de um nível interno.

### 4.6 Page Object: quando ajuda e quando é peso morto

O Page Object nasceu quando a única forma de montar estado era clicando na tela. Com setup
por API, **o motivo original desapareceu na maior parte dos casos**.

- Page object **expõe seletor e ação**. Nunca contém asserção, fluxo de negócio ou `if`.
- **Sem herança.** Composição, se precisar.
- **Sem page object para tela usada por um único teste.**
- Framework abstrato que uma pessoa entende é dívida com nome bonito.
- Em Cypress, classes instanciadas no meio do fluxo brigam com a fila assíncrona.

### 4.7 Custom commands, fixtures e step definitions

- **Custom command / fixture** é ótimo para o estável e sem intenção (`cy.login`,
  `factory.pedido`); ruim para o corpo do cenário (`cy.comprarComCupom()`).
- **Step definition acoplado à feature** gera explosão de steps. Organize por **conceito de
  domínio**, não por tela.
- **Sem step de conjunção.** `Dado que faço login e vou para o carrinho` é dois steps.
- Antes de escrever um step novo, procure o existente.

### 4.8 Framework caseiro

**Camada fina sobre ferramenta madura, nunca motor próprio.** Driver, sincronização,
inspetor, relatório e CI viram um segundo produto para manter.

---

## 5. Nada de lógica no teste

`if`, `for`, `while`, ternário e concatenação para montar o valor esperado são proibidos.
Lógica no teste precisa de teste — e ninguém testa o teste.

**O valor esperado é literal.** Repetir a fórmula do sistema dentro da asserção faz o teste
concordar com o bug:

```ts
// ❌ se a fórmula do sistema estiver errada, o teste erra junto
expect(total).toBe(preco * (1 - desconto));

// ✅ valor calculado à mão pelo autor do teste, com a intenção na mensagem
expect(total, 'R$200 com 10% = R$180').toBe(180);
```

**Data-driven é a exceção legítima:** tabela de casos derivada de partição/BVA.

**Skip condicional que passa verde é proibido.**

---

## 6. Assertions

- **Valor exato, mensagem com a intenção.**
- **Assertion Roulette:** várias asserções sem mensagem — falha no CI e ninguém sabe qual.
- **Asserção frouxa não conta como cobertura:** `toBeTruthy()`, `not.toBeNull()`,
  `expect([200,201]).toContain(status)`.
- **Sensitive Equality:** comparar objeto inteiro ou snapshot enorme.
- **Erro esperado:** asserte o código específico.
- **Mensagem de falha boa contém três coisas:** esperado, obtido e a intenção.

---

## 7. Estado, não interação

Asserte o **resultado observável**, não a sequência de chamadas.

- Depois do `POST`, faça o `GET` e asserte o recurso resultante.
- Não asserte nome de tabela, query, CTE, fila interna ou hash de commit.
- Se um comportamento só é observável por endpoint interno, o problema é de
  observabilidade do produto — leve ao time, não contorne no teste.

---

## 8. Dublês de teste

| Dublê | O que faz | Uso típico no QA |
|---|---|---|
| **Dummy** | Só preenche parâmetro obrigatório | Raro |
| **Stub** | Devolve resposta pré-definida | Mock server do parceiro (200/500/timeout) |
| **Spy** | Registra que foi chamado | Conferir que o webhook saiu |
| **Mock** | Verifica a interação e falha se não ocorrer | Só em efeito colateral externo relevante |
| **Fake** | Implementação leve mas funcional | Gateway em sandbox, banco em memória |

Ordem de preferência: **implementação real → fake → stub → mock.**

- **Prefira verificação de estado à de interação.**
- **Over-mocking é o pior caso:** mockar para devolver X e asserir que a resposta é X.
- Todo mock precisa de um **teste de contrato** correspondente.
- Mock que devolve outro mock está no nível errado.

---

## 9. Determinismo

> Teste não-determinístico é pior que inútil: contamina a suíte inteira e destrói a
> confiança na regressão. — Martin Fowler

| Causa | Tratamento |
|---|---|
| Falta de isolamento | Massa própria por teste, sem registro compartilhado |
| Assincronismo | Espera por **condição**, nunca por tempo |
| Serviço remoto | Stub/fake na regressão; contrato em execução separada |
| Tempo | Relógio injetado; virada de dia/mês, fuso, horário de verão |
| Vazamento de recurso | Cleanup na criação, teardown em ordem reversa |

- **Assincronismo é a maior fatia dos flaky.** `cy.wait(3000)` e `waitForTimeout` são falha
  de revisão.
- **Limpe antes, não só depois.** O `after` não roda quando o teste explode no meio.
- **Dado único por execução** (`testCode` previsível).
- **Verifique a independência de verdade:** rode sozinho (`.only`).
- **Quarentena com teto.** Meta abaixo de 1%; times maduros ficam em 0,1%.
- **Retry não é correção.**

---

## 10. Localizadores

1. **Papel + nome acessível** (`getByRole('button', { name: /pagar/i })`)
2. **Label, placeholder, texto** para campos de formulário
3. **`data-testid`** para o que não tem semântica

Proibidos: seletor acoplado a estilo (`.btn.btn-large`), XPath posicional, índice (`nth(3)`).

- O `data-testid` entra **durante** o desenvolvimento da história, não depois.
- **Login programático, uma vez**, exceto nos testes do próprio login.
- **Evidência sob demanda:** trace e vídeo na falha ou primeira retentativa.

---

## 11. Gherkin: declarativo, não imperativo

```gherkin
# ❌ imperativo — narra a mecânica, morre no próximo redesign
Dado que estou na página de login
Quando eu digito "joana@exemplo.com" no campo e-mail
E eu clico no botão "Entrar"

# ✅ declarativo — descreve a intenção; o "como" vive no step definition
Dado que estou autenticada como cliente com um pedido em aberto
Quando eu consulto meus pedidos
Então vejo o pedido em aberto com status "Aguardando pagamento"
```

- **Escreva como se não existisse UI.** Exceção: quando o comportamento da própria tela é o
  objeto do teste.
- **De 3 a 7 passos.**
- **Um comportamento por cenário.** O título é o "Então" resumido.
- **`Contexto` para pré-condição repetida.**
- **`Esquema do Cenário` com parcimônia:** ótimo para partição e BVA da mesma regra.
- **Steps organizados por conceito de domínio**, não por tela.
- **Sem passo de conjunção.**
- **O cenário não é script de automação.**

---

## 12. Massa, ambiente e segredos

- Massa por **API/factory**, alvo pela GUI.
- **Nada de ID hardcoded.** Dado de referência descoberto em runtime e **asserido**.
- **Toda criação registra cleanup.** Teardown em ordem reversa.
- **Segredo nunca no repositório.** Coleção exportada com token dentro é vazamento versionado.
- **Dado pessoal sempre anonimizado.**

---

## 13. Comentários

- ❌ Documentar o backend na spec: hash de commit, nome de CTE, tabela, serviço.
- ❌ Narrar o óbvio: `// cria o material`, `// faz o GET`.
- ✅ Uma linha, só para o **porquê** não-óbvio.

---

## 14. Cobertura mente — teste de mutação

Cobertura mede **quais linhas executaram**, não se alguém verificou o resultado.

| Score de mutação | Leitura |
|---|---|
| acima de 80% | Suíte forte |
| 60% a 80% | Aceitável, com lacunas conhecidas |
| abaixo de 60% | Asserções fracas; a cobertura está mentindo |

- Comece por **um módulo crítico** (o de dinheiro).
- Rode em **modo incremental**, fora do PR — nightly ou semanal.
- Mutantes sobreviventes são **pauta**: cada um é um caso de teste que falta.
- Não persiga 100% (existe mutante equivalente).

---

## 15. Revisão de teste gerado por IA

O portão de aprovação existe por um motivo técnico: **a IA escreve o teste a partir do que
o código faz, não do que o requisito manda.** Quando o código tem um defeito, o teste
gerado documenta o defeito como comportamento esperado — e passa verde para sempre.

Os padrões a caçar na revisão:

- **Asserção que espelha a implementação.** *De onde veio esse número — do requisito ou da
  execução?*
- **Asserção que espelha o mock.** Prova que o mock funciona.
- **Asserção decorativa.** "o campo existe", "status entre 200 e 299".
- **Ilusão de cobertura.** Cinco cenários no mesmo caminho feliz; limite e exceção de fora.
- **Caso inventado.** Regra que não existe no documento — deveria ter virado `@premissa`.
- **Nomes genéricos** (`testa fluxo principal`).

Regras de fluxo:

1. **O critério de aceite vem antes do teste.** Derivação a partir do requisito, nunca do
   código pronto.
2. **O valor esperado é calculado por uma pessoa**, a partir da regra. Nunca colado da
   execução.
3. **Todo teste gerado passa pelo "teste do teste"**: quebre o comportamento, confirme o
   vermelho.
4. **Módulo crítico passa por mutação.**
5. **A tag `@ia-gerado` nunca é removida.**

Suítes geradas por LLM apresentam score de mutação na casa dos 20% em funções complexas.
**Trate volume de testes gerados como matéria-prima, nunca como entrega.**

---

## 16. Catálogo de smells

| Smell | Sintoma | Correção |
|---|---|---|
| **Assertion Roulette** | Não dá para saber qual asserção quebrou | Mensagem em toda asserção |
| **Eager Test** | Verifica funcionalidade demais | Quebrar em condição única |
| **Lazy Test** | Vários cenários no mesmo `it` | Um cenário por teste |
| **Mystery Guest** | Depende de dado externo invisível | Semear no próprio teste |
| **General Fixture** | Setup monta mais que o necessário | Fixture mínima |
| **Irrelevant Information** | Detalhe que não afeta a regra | Builder com defaults |
| **Conditional Test Logic** | `if`/loop no corpo | Cenários separados |
| **Sleepy Test** | Espera por tempo fixo | Espera por condição |
| **Resource Optimism** | Assume recurso do ambiente | Semear ou asserir |
| **Sensitive Equality** | Compara objeto inteiro | Asserir campos da regra |
| **Dead Test** | Nunca falha | Quebrar o sistema e ver |
| **Tautological Test** | Asserta o que a implementação devolve | Valor do requisito |
| **Over-mocking** | Testa a configuração do dublê | Estado real ou fake |
| **Erratic / Flaky** | Passa e falha sem mudança | Quarentena + causa |
| **Fragile Test** | Quebra a cada refatoração | Asserir contrato |
| **Obscure Test** | Não dá para dizer o que testa | Nome, AAA e AHA |
| **Wrong Abstraction** | Helper com flags | Inline e rederivar |
| **Nested Setup** | Variável depende de 3 `beforeEach` | `setup()` e `const` |
| **Hard-coded Test Data** | ID fixo do ambiente | Factory e lookup |
| **For Testers Only** | Código de produção só para o teste | Rever design |

---

## 17. Checklist de revisão de PR

Itens binários. Qualquer "não" reprova.

**Intenção**
- [ ] O título diz o comportamento, sem nome de método ou jargão interno.
- [ ] Dá para responder "quando este teste vai falhar?" lendo só o teste.
- [ ] Um comportamento por teste.
- [ ] O teste foi visto **falhando** ao menos uma vez.

**Estrutura e abstração**
- [ ] AAA visível; uma única fase de Act.
- [ ] A diferença para os testes vizinhos salta aos olhos.
- [ ] Nenhum helper com flag booleana; nenhum helper usado uma vez só.
- [ ] Não é preciso abrir outro arquivo para entender o teste.
- [ ] Sem `describe` aninhado além de um nível e sem variável reatribuída em hook.
- [ ] Sem `if`, loop ou cálculo do valor esperado.

**Asserções**
- [ ] Valor exato, com mensagem de intenção nas não óbvias.
- [ ] Sem `toBeTruthy` / `toContain([200,201])` em resultado de negócio.
- [ ] Asserção sobre estado/contrato observável, não sobre chamada interna.
- [ ] O valor esperado veio do requisito, não da execução.

**Determinismo**
- [ ] Roda sozinho e em paralelo; sem depender de ordem.
- [ ] Sem espera por tempo fixo.
- [ ] Massa própria, com código único e cleanup registrado.
- [ ] Sem ID hardcoded e sem `skip` condicional verde.

**Camada, ferramenta e segurança**
- [ ] Está na camada mais barata possível.
- [ ] Localizador por papel/`data-testid`, nunca por estilo ou posição.
- [ ] Dublê no nível certo, com contrato correspondente se for de terceiro.
- [ ] Sem segredo no código.
- [ ] Tags de rastreabilidade presentes (`@CT-XX`, `@RN-XX`, `@camada:`, `@ia-gerado`).

**Comentários**
- [ ] Nenhum comentário narrando o óbvio ou documentando o backend.

---

## 18. Fontes

**Escrita e abstração**
- [AHA Testing](https://kentcdodds.com/blog/aha-testing) e [Avoid Nesting when you're Testing](https://kentcdodds.com/blog/avoid-nesting-when-youre-testing) — Kent C. Dodds
- [The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction) — Sandi Metz
- [Tests Too DRY? Make Them DAMP!](https://testing.googleblog.com/2019/12/testing-on-toilet-tests-too-dry-make.html) — Google Testing Blog
- [Test Behaviors, Not Methods](https://testing.googleblog.com/2014/04/testing-on-toilet-test-behaviors-not.html) — Google Testing Blog
- *Software Engineering at Google*, cap. 12
- [The Golden Rule of Assertions](https://www.epicweb.dev/the-golden-rule-of-assertions)
- [Por que hoje considero Page-Objects um antipadrão](https://dev.to/walmyrlimaesilv/why-nowadays-do-i-consider-page-objects-an-anti-pattern-in-web-test-automation-46ad) — Walmyr Filho

**Smells**
- [Assertion Roulette](http://xunitpatterns.com/Assertion%20Roulette.html) — Gerard Meszaros
- [Catálogo de test smells](https://testsmells.org/pages/testsmells.html)

**Dublês de teste**
- [Test Doubles — SWE at Google, cap. 13](https://abseil.io/resources/swe-book/html/ch13.html)
- [Don't Overuse Mocks](https://testing.googleblog.com/2013/05/testing-on-toilet-dont-overuse-mocks.html)
- [Prefer Fakes Over Mocks](https://tyrrrz.me/blog/fakes-over-mocks) — Oleksii Holub

**Determinismo**
- *Eradicating Non-Determinism in Tests* — Martin Fowler
- [Flaky tests — pytest](https://docs.pytest.org/en/stable/explanation/flaky.html)

**Ferramentas**
- [Best Practices — Playwright](https://playwright.dev/docs/best-practices)
- [Best Practices — Cypress](https://docs.cypress.io/app/core-concepts/best-practices)

**Gherkin**
- [Writing better Gherkin](https://cucumber.io/docs/bdd/better-gherkin/) — Cucumber
- [BDD 101: Writing Good Gherkin](https://automationpanda.com/2017/01/30/bdd-101-writing-good-gherkin/)

**Mutação e teste gerado por IA**
- [Practical Mutation Testing at Scale — Google](https://arxiv.org/pdf/2102.11378)
- [Reviewing AI-Generated Tests: A Code-Review Checklist](https://qaskills.sh/blog/reviewing-ai-generated-tests-checklist-2026)
- [AI-Generated Tests That Pass But Don't Assert Anything](https://getautonoma.com/blog/ai-generated-tests-pass-but-dont-assert)
