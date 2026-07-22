# Camadas de teste e automação — QA

Este arquivo responde a uma pergunta: **um cenário aprovado vira teste automatizado em
qual camada, e sob quais regras?**

- `.claude/skills/qa-casos/SKILL.md` → *o que* testar (técnicas de derivação)
- este arquivo → *onde* aquilo é provado
- [`TESTE-LIMPO.md`](TESTE-LIMPO.md) → *como* o teste é escrito

**Escopo:** camadas executadas pelo QA/SDET, **todas contra o ambiente de QA**. O que roda
dentro do pipeline do desenvolvedor, antes do deploy, não é tratado aqui.

## Regra zero

> **Cada cenário é provado em exatamente UMA camada: a mais barata capaz de provar a regra.**

Duplicar a mesma regra em camadas diferentes não aumenta cobertura — aumenta manutenção e
produz dois testes que quebram juntos pelo mesmo motivo. Se um cenário parece precisar de
duas camadas, ele está testando duas coisas e deve ser dividido.

Na prática, "mais barata" quase sempre significa **API**. A UI é a última opção.

## Camadas

| Camada | Prova o quê | Ferramenta de referência |
|---|---|---|
| `api` | Contrato, status, regra de negócio, autorização, robustez | `cy.request` / `request` |
| `banco` | Efeito colateral que a API não devolve (gray box) | Consulta somente leitura |
| `contrato` | Compatibilidade com terceiro ou outro squad | Pact / WireMock / MSW |
| `e2e` | Jornada de negócio ponta a ponta, na UI real | Cypress / Playwright / Maestro |
| `performance` | Tempo de resposta, vazão, estabilidade sob carga | k6 |
| `seguranca` | Autorização, IDOR, token, exposição de dado | Casos de API + OWASP ZAP |
| `manual` | Exploratório, UAT, o que exige julgamento humano | Sessão com charter |

---

## 1. Regra de roteamento — do cenário para a camada

Aplique na ordem. **A primeira linha que casar define a camada.**

| Se o cenário… | Camada |
|---|---|
| valida formato, máscara, cálculo, faixa numérica ou mensagem de erro de campo | `api` (data-driven) |
| verifica status HTTP, schema, paginação, filtro, ordenação, idempotência | `api` |
| verifica quem **pode** executar a ação (perfil, dono do recurso, token) | `api` + `seguranca` |
| exige confirmar dado gravado, contador, log de auditoria ou evento publicado | `api` (ação) + `banco` (verificação) |
| percorre transição de estados | `api` (matriz completa) + `e2e` (só caminho principal) |
| é jornada de negócio completa, com valor direto (pagar, contratar, cadastrar) | `e2e` |
| tem número no requisito: tempo, volume, usuários simultâneos, tamanho de arquivo | `performance` |
| depende de serviço de terceiro fora do nosso controle | `contrato` + mock na regressão |
| depende de julgamento humano (usabilidade, texto, layout) ou é charter | `manual` |

### Regra da primeira linha

Partição de equivalência, BVA e teste de sintaxe **não viram cenário de UI**. Viram teste
de API parametrizado: 12 casos de limite custam 12 requisições, não 12 fluxos de tela.

### Teto de E2E

**No máximo 1 cenário E2E por fluxo de negócio da feature, e no máximo 10% dos cenários
automatizados.** Variação de dado, caminho negativo, limite e permissão ficam em `api` —
sempre. Se a suíte E2E passa de 10 minutos ou a matriz mostra mais de 10% em `e2e`, o
problema é de roteamento, não de infraestrutura.

```
api + banco + contrato   ~90%
e2e                      ≤10%
performance + seguranca  o que o requisito exigir, fora da conta
```

---

## 2. Tags e rastreabilidade

| Tag | Valores | Função |
|---|---|---|
| `@camada:` | `api`, `banco`, `contrato`, `e2e`, `performance`, `seguranca`, `manual` | Onde a regra é provada |
| `@suite:` | `smoke`, `regressao`, `nightly`, `release` | Quando roda no pipeline |
| `@automacao:` | `pendente`, `feito:<PR>`, `nao-automatizar:<motivo>` | Estado da conversão |

`nao-automatizar` exige motivo escrito. "Difícil" não é motivo; "depende de OTP enviado por
SMS de terceiro" é.

A `MATRIZ.md` ganha duas colunas:

| Regra | Origem | Técnica(s) | Cenários | Risco | **Camada** | **Automação** | Status |
|---|---|---|---|---|---|---|---|
| RN-03 | RF-07 | Particionamento + BVA | CT-07..CT-12 | Alto | api | feito:#412 | Aprovado |

```
conversão = cenários @automacao:feito / cenários aprovados (excluindo nao-automatizar)
```

Acompanhe por feature, não global — a média esconde a feature crítica com 20%.

---

## 3. Regras por camada

### 3.1 `api` — onde a maior parte dos cenários deve cair

Para cada endpoint sob teste, cubra seis eixos:

| Eixo | O que asserir |
|---|---|
| Status | 200/201/204, 400, 401, 403, 404, 409, 422, 429 |
| Schema | Contra JSON Schema ou OpenAPI — não campo a campo |
| Regra | Os campos de negócio que a RN determina |
| Efeito colateral | O que mudou no banco, na fila ou no parceiro |
| Autorização | Matriz perfil × recurso, incluindo IDOR |
| Robustez | Payload malformado, campo ausente, tipo errado, unicode, string longa |

- Massa por API ou factory, **nunca por SQL direto** — SQL burla validação e mascara defeito.
- Cada teste independente e paralelizável.
- Token obtido no setup, nunca fixo no repositório.
- Asserção de tempo aqui é sanidade grosseira (< 3 s), não performance.
- **Contrato quebrado é defeito, não ajuste de teste.** Abre-se o defeito antes de
  atualizar o schema do teste.

### 3.2 `banco` — verificação gray box

**Testar:** o que a API não devolve mas a regra exige — flag de auditoria, log de uso,
contador de limite por CPF, soft delete, evento publicado.
**Não testar:** o que já está na resposta da API.

- A ação sempre passa pela aplicação; o banco só entra na **verificação**.
- Consulta somente leitura, com usuário sem permissão de escrita.
- Se a verificação exige três joins e schema interno, peça um endpoint ou evento observável.

### 3.3 `contrato`

**Testar:** compatibilidade de requisição/resposta com o terceiro — campos obrigatórios,
tipos, enums, versionamento.
**Não testar:** a regra de negócio do terceiro.

- Na regressão roda **mock server** alimentado pelo contrato; o sandbox real fica em
  execução agendada separada.
- **Todo mock precisa de um teste de contrato correspondente.** Mock sem contrato é
  suposição verde.
- Cobrir os erros que a nossa regra trata: timeout, 500, 429, resposta fora do schema.

### 3.4 `e2e`

**Testar:** jornada crítica no caminho feliz, integração real, autenticação e sessão,
navegação, e no máximo um caminho de erro quando faz parte do valor do fluxo.
**Não testar:** variação de dado, limites, matriz de permissão, validação de campo.

- **Setup pela API, verificação pela UI.**
- Seletores por `data-testid`. CSS, XPath e texto visível proibidos.
- Espera automática da ferramenta. `sleep`/`waitForTimeout` fixo é falha de revisão.
- Massa própria por execução.
- `retries: 1` no CI. Teste que só passa na segunda vez entra em quarentena.
- **Política de flaky:** intermitente 2 vezes em 10 → `@quarentena`, sai da suíte de
  bloqueio, prazo de 5 dias úteis.
- Evidência obrigatória em falha: trace, vídeo, screenshot.
- Executar contra build fixo e identificado.

### 3.5 `performance`

Nunca execute sem **baseline do ambiente de QA** e **SLO do requisito**.

| Tipo | Pergunta | Perfil |
|---|---|---|
| Smoke de carga | O script está correto? | 1–5 VUs, 1 min |
| Carga | Aguenta o volume esperado dentro do SLO? | Pico previsto, 10–30 min |
| Estresse | Onde quebra e como se comporta? | Rampa até degradar |
| Pico | Sobrevive à campanha? | Salto abrupto e retorno |
| Resistência | Vaza memória ao longo do tempo? | Carga média, 2–8 h |

Medir sempre os quatro: **latência** (p95/p99, nunca média), **vazão**, **erro**
(distribuição de status), **saturação** (CPU, memória, pool, fila, GC).

- **O número absoluto não vale como previsão de produção.** Vale a comparação com a
  própria baseline. Todo relatório declara o fator de escala.
- **Regressão acima de 10% no p95 contra a baseline anterior é defeito**, mesmo com SLO
  atendido.
- **Janela exclusiva agendada.** Funcional rodando junto contamina os dois.
- Volume de tabela proporcional e distribuição real de chaves.
- Descartar a janela de aquecimento — ou medi-la, se cold start for o risco.
- Terceiros mockados com latência simulada.
- Critério vive como threshold no código, não no relatório.

### 3.6 `seguranca` — a fatia funcional

Escopo: matriz de autorização por perfil; IDOR em todo endpoint com identificador na rota;
manipulação de token (expirado, assinatura inválida, escopo trocado, ausente); injeção nos
campos livres; exposição de dado sensível em resposta e log; rate limiting na autenticação.

Fora do escopo: pentest, SAST/DAST, hardening, criptografia em repouso.

**Todo endpoint novo com `{id}` na rota nasce com um caso de IDOR. Sem exceção.**

### 3.7 `manual` — exploratório e UAT

- Charter com time-box de 60–90 min e anotação de sessão. Não vira Gherkin nem automação:
  o valor está na variabilidade.
- UAT é do PO; o QA não aprova em nome do negócio.
- Toda sessão registra build, ambiente e massa — sem isso o defeito não é reproduzível.

---

## 4. Ambiente de QA — regras

- **Build identificado.** Resultado sem versão não entra em relatório.
- **Deploy controlado.** Deploy durante a suíte invalida a rodada — reexecute.
- **Massa é responsabilidade do QA.** Seed versionado, recriável por comando.
- **Cada teste cria e limpa o que usa.**
- **Terceiros mockados por padrão.**
- **Dado pessoal anonimizado** (LGPD).
- **Indisponibilidade é registrada** com data, duração e impacto.
- **Um ambiente, uma finalidade por janela.**

---

## 5. Critérios de entrada e saída

**Entrada — build em teste:** pipeline do dev verde e artefato publicado; versão
identificada com release notes; ambiente estável e massa carregada.

**Entrada — automatizar um cenário:**
1. Cenário com `@aprovado-por:<usuario>` — nenhum `@ia-gerado @nao-aprovado` vira código.
2. Sem `@premissa` pendente.
3. Camada definida na `MATRIZ.md`.
4. Massa e credenciais disponíveis.

**Saída — parecer do QA para liberar a release:**

| Critério | Meta |
|---|---|
| Cenários de risco alto executados | 100% |
| Suítes `api`, `banco`, `contrato` verdes | 100% |
| `e2e @suite:smoke` verde | 100% |
| Defeitos S1 abertos | 0 |
| Defeitos S2 abertos | ≤ 2, com workaround documentado |
| Conversão nas features de risco alto | ≥ 80% |
| Testes em `@quarentena` | ≤ 2, com prazo |
| Regressão de p95 vs. baseline de QA | ≤ 10% |
| Sessões exploratórias das áreas de risco alto | Executadas e registradas |

Exceção exige justificativa escrita e aprovação nominal — não silêncio.

---

## 6. Pipeline no ambiente de QA

| Gatilho | Suíte | Tempo máximo | Bloqueia? |
|---|---|---|---|
| Deploy no ambiente de QA | `api @suite:smoke` | 5 min | Sim |
| Build aceito | `api` + `banco` (regressão) | 20 min | Sim |
| Diária (noturna) | `e2e` completo + `seguranca` | Sem limite | Abre issue |
| Semanal | `performance` + `contrato` real | Janela exclusiva | Abre issue |
| Candidato a release | Tudo + estresse e pico + exploratório + UAT | — | Sim |

Se a regressão passar do teto de tempo, a correção é **reclassificar cenários para camadas
mais baratas** — não aumentar o teto.

---

## 7. Ferramentas

**Uma ferramenta de E2E por repositório.**

| Critério | Cypress | Playwright |
|---|---|---|
| Depuração | Melhor: time travel, runner interativo | Boa: trace viewer |
| Gherkin `.feature` | `@badeball/cypress-cucumber-preprocessor`, maduro | Sem suporte oficial |
| Múltiplas abas, domínios, iframe | Sofre | Nativo |
| Paralelismo | Por arquivo de spec | Por worker |
| Camada `api` | `cy.request` | `request` fixture |
| Mobile nativo | Não | Não — use Maestro |

**Regra de corte:** se alguma jornada crítica passa por checkout em iframe, login de
terceiro ou abre outra aba, use **Playwright**. Fora disso, se o time já escreve Gherkin e
valoriza depuração, Cypress é mais confortável.

### Camada `api` — qual runner

| | `cy.request` / PW `request` | Supertest | Newman |
|---|---|---|---|
| Runner adicional | Não | Sim | Sim |
| Revisão em PR | Boa | Boa | Ruim — diff de JSON ilegível |
| Data-driven | Nativo | Nativo | `--iteration-data` (CSV) |
| Quem mantém | Quem escreve código | Quem escreve código | QA sem código também |
| Reuso de helper | Alto | Alto | Baixo |

**Governança: no máximo dois runners — um de E2E e um de API.**

- Se a suíte E2E já é Cypress ou Playwright, **use o `request` da própria ferramenta**.
- **Supertest** só se a suíte já vive em Jest/Mocha. Contra URL remota ele é praticamente
  superagent com asserção.
- **Newman** entra quando a coleção Postman já existe e é usada na exploração manual. Papel
  dele é `@suite:smoke` e sanidade de contrato — a regressão completa fica em código.

### Regras do Newman

- Coleção e environment **versionados e revisados em PR**.
- **Nenhum segredo no environment.** Token entra por `--env-var` do cofre do CI.
- Pastas espelham `@suite:`; nome de cada request começa com o `@CT-XX`.
- Partição e BVA por `--iteration-data`, um CSV por RN.
- Todo `pm.test` afirma algo verificável.
- Schema com `pm.response.to.have.jsonSchema`.
- Relatórios `junit` (CI) e `htmlextra` (evidência).
- `newman run -n 100` **não é teste de performance**.

### Regras do Supertest

- Sempre a URL do ambiente de QA por variável. `request(app)` está fora deste escopo.
- `.expect(status)` como primeira barreira, mas a asserção de regra fica explícita no corpo.
- Token obtido em `beforeAll` por autenticação real.

### Regras do Cypress

- `cy.wait(3000)` proibido — use `cy.intercept()` + `cy.wait('@alias')` ou `should`.
- Crie `cy.getByTestId()` e proíba `cy.get('.classe')` na revisão.
- `testIsolation` ligado. Login com `cy.session()`.
- `retries: { runMode: 1, openMode: 0 }`.
- **No máximo 2 cenários E2E por spec** (paralelismo é por arquivo).
- Em caso negativo, `failOnStatusCode: false`.
- Schema com `chai-json-schema` ou `ajv` via `cy.task`.

### Regras do Playwright

- `page.getByTestId()` com `testIdAttribute` = `data-testid`.
- Setup por API com a fixture `request`, reaproveitando `storageState`.
- `fullyParallel: true` e `workers` fixos no CI.
- `trace: 'retain-on-failure'` e `video: 'retain-on-failure'`.

### O portão de aprovação vive no runner

```bash
# Cypress + cucumber preprocessor
npx cypress run --env tags="@camada:e2e and @suite:regressao and not @nao-aprovado and not @quarentena"

# Playwright
npx playwright test --grep "@camada:api" --grep-invert "@nao-aprovado|@quarentena"
```

**Cenário sem `@aprovado-por` não executa na suíte oficial.**

---

## 8. Antipadrões

- Automatizar na UI o que a API provaria.
- Cenário E2E com 15 passos cobrindo quatro regras.
- Preparar estado por SQL direto.
- Rodar performance junto com a suíte funcional.
- Tratar número de performance do ambiente de QA como previsão de produção.
- Ajustar o teste ao comportamento novo sem discutir se ele é correto.
- `sleep` fixo ou `cy.wait(3000)`.
- Teste dependente de ordem ou de usuário fixo.
- Retry escondendo flaky.
- Coleção Postman com token dentro, ou que só existe no workspace de uma pessoa.
- Reportar suíte verde sem dizer o que ficou de fora.

---

## 9. Métricas

| Métrica | Fórmula | Para quê |
|---|---|---|
| Conversão | automatizados / aprovados | Quanto da cobertura existe de fato |
| Distribuição por camada | % em cada `@camada:` | Detecta migração silenciosa para E2E |
| Taxa de flaky | intermitentes / total | Confiança na suíte |
| Escape de defeito | produção / (produção + teste) | Eficácia do desenho de casos |
| Tempo de feedback | duração da regressão | Custo da automação |
| Deriva de performance | p95 atual / p95 da baseline | Regressão silenciosa |
| Indisponibilidade | horas paradas por ciclo | Sustenta conversa sobre prazo |

Uma suíte verde com flaky alto e conversão baixa não significa qualidade — significa que
ninguém está olhando. **Ao reportar, diga sempre o que não foi coberto e em qual camada a
lacuna ficou.**
