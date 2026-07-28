---
name: qa-automacao
description: Escreve e revisa testes automatizados seguindo o contrato AtlanteX — questionário de frameworks, geração de specs (API/E2E/performance) e revisão de PR contra as convenções. Use ao automatizar casos ou revisar specs existentes.
---

# /qa-automacao — testes automatizados

⚠️ **Processo delicado.** O essencial dos três contratos do time está **neste
arquivo**: a regra zero (camada), as sete travas, a escrita e o checklist de PR.
Os documentos completos são **consulta pontual, não leitura de partida**:

| Abra… | Só quando |
|---|---|
| [`docs/CONVENCOES-AUTOMACAO.md`](../../../docs/CONVENCOES-AUTOMACAO.md) | for montar o projeto do zero, ou precisar divergir de pasta, nome ou runner |
| [`references/camadas-e-automacao.md`](../design-casos-teste/references/camadas-e-automacao.md) | a camada do cenário não sair da tabela da regra zero, abaixo |
| [`references/escrita-de-testes.md`](../design-casos-teste/references/escrita-de-testes.md) | precisar do porquê de uma das sete travas, ou de um exemplo longo |

**PRs que ferirem estas regras voltam** — mas abrir os três de saída custa cerca
de 15 mil tokens e consome o orçamento da sessão antes da primeira linha de
código. Abra o que a dúvida pedir, quando ela aparecer.

---

# 0. Regra zero — a camada vem antes do código

> **Cada cenário é provado em exatamente UMA camada: a mais barata capaz de provar a regra.**

Roteie **antes** de escrever. A primeira linha que casar define a camada:

| Se o cenário… | Camada |
|---|---|
| valida formato, máscara, cálculo, faixa numérica, mensagem de erro de campo | `api` (data-driven) |
| verifica status, schema, paginação, filtro, ordenação, idempotência | `api` |
| verifica quem **pode** executar a ação | `api` + `seguranca` |
| exige confirmar dado gravado, contador, auditoria, evento publicado | `api` + `banco` |
| percorre transição de estados | `api` (matriz) + `e2e` (só o principal) |
| é jornada de negócio completa, com valor direto | `e2e` |
| tem número no requisito: tempo, volume, concorrência | `performance` |
| depende de terceiro fora do nosso controle | `contrato` + mock na regressão |
| depende de julgamento humano | `manual` |

**Teto duro: no máximo 1 E2E por fluxo de negócio e ≤10% dos cenários automatizados.**
Partição, BVA e sintaxe **nunca** viram cenário de UI — 12 casos de limite custam 12
requisições, não 12 fluxos de tela.

Se a regressão estourar o tempo, **reclassifique cenários para camadas mais baratas** —
não aumente o teto.

---

# 1. Questionário de frameworks

⚠️ **AskUserQuestion, UMA pergunta por chamada, com opções clicáveis.**
Faça antes de escrever qualquer spec.

| # | Pergunta | Opções |
|---|---|---|
| 1 | Framework **web/E2E** | Playwright · Cypress · Não haverá E2E |
| 2 | Framework **API** | Playwright (`request`) · Supertest · Cypress · Newman (collection Postman) |
| 3 | **Performance** | k6 · Não haverá |
| 4 | Projeto já existe? | Repositório existente (seguir estrutura atual) · Do zero |
| 5 | Onde os testes moram? | Mesmo repo do produto · Repo separado de QA |

**A organização não muda com o framework.** As regras deste contrato valem
igualmente para **API e E2E**, em Playwright, Cypress, Supertest ou Newman:
mesma árvore de `describe`, mesmos nomes de comportamento, mesmo AAA, mesma
proibição de skip condicional, mesma independência entre testes. O que muda é
apenas a sintaxe do runner.

Equivalências de infraestrutura:

| Conceito | Playwright | Cypress | Supertest |
|---|---|---|---|
| fixture/massa | `test.extend` / factory | `cy.task` / commands | helper + `beforeEach` |
| login único | `global-setup` + storageState | `cy.session` | token no `beforeAll` |
| lint | `eslint-plugin-playwright` | `eslint-plugin-cypress` | regras genéricas |

Se houver **Newman**, a collection vem de `test/collection-postman/` e os testes de
contrato moram nos scripts da própria request.

---

# 2. A regra de ouro — aplique antes de cada `expect`

> **Um teste deve falhar se, e somente se, a intenção do sistema não for cumprida.**

Pergunte: **"quando este teste vai falhar?"** Se a resposta não for *"quando o
comportamento que eu quero garantir quebrar"*, a assertion está errada.

- Asserir no **resultado/contrato** — nunca em como o backend faz (nome de serviço,
  query, hash de commit).
- Assertion sobre **valor exato**, com mensagem explicando a intenção.
- Nada que faça o teste passar **sem** exercitar a intenção.

```ts
// ❌ expect(res.ok()).toBeTruthy();
// ❌ expect([200, 201]).toContain(res.status());
// ✅ expect(res.status(), "criar contraparte PJ válida").toBe(201);
// ✅ expect(rep.available, "disponível = físico − reservado").toBe(N - RESERVE);
```

---

# 3. As sete travas — verifique em cada spec que escrever

**1. Independência.** Estado no `beforeEach`/fixture, nunca herdado do teste
anterior. Roda sozinho, em qualquer ordem, em paralelo.

**2. Zero green-skip.** `test.skip("precondição ausente")` é **proibido** — mente no
relatório. Semeie via API. Se o estado não é montável na API (job assíncrono,
multipart, passo no coletor), o cenário **não é teste de API**: vai para E2E ou não
existe. `if (semDado) return` também é proibido. Seed que falhou é falha do teste:
`expect(res.ok())`, não skip.

**3. Massa via API, alvo via GUI.** Pré-condição pela via mais barata; a tela só para
o que está sendo testado. Criar massa clicando é proibido.

**4. Pirâmide ~80% API / ~20% E2E.** Regra, cálculo, persistência, estado, RBAC →
API. "Aparece na tela, o clique dispara, o form dá feedback" → E2E.
**Nunca teste a mesma regra nas duas camadas.**

**5. DAMP > DRY.** Duplicação é mais barata que a abstração errada. Helper que ganha
parâmetro booleano para servir dois chamadores é o sinal — faça inline. Abstraia só o
estável e sem intenção (login, payload padrão, massa base), nunca o corpo do cenário.

**6. Sem `describe.serial`**, exceto contenção física comprovada — com uma linha de
comentário justificando. Serial nunca é desculpa para dependência entre testes.

**7. Massa com código único** (`testCode`), **cleanup registrado** (teardown em ordem
reversa) e **IDs de referência descobertos em runtime**, nunca hardcoded.

---

# 4. Escrita

## Estrutura

```
tests/
  support/        auth, fixtures, factory, lookups, fresh-tenant
  api/<módulo>/   kebab-case.spec.ts
  e2e/<módulo>/   kebab-case.spec.ts
```

**Um arquivo por feature**, não por micro-cenário. Árvore:
`describe` (feature) › `describe` (sub-fluxo) › `test` (caso).

Título do teste = frase de comportamento em minúsculas: *"desconta o reservado do
disponível"*, nunca *"testa GetQuantitativeReportRawQuery"*.

Nomes de arquivo descritivos e completos: `stock-adjustments.spec.ts`, nunca
`registrationscounterpartie.spec.ts`.

## AAA visível pela estrutura

Linha em branco separando Arrange · Act · Assert. Comentário `// Arrange` só quando o
teste é longo e a fronteira não é óbvia.

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

## Comentários

O teste se explica pelo título e pelas assertions. Se precisa de parágrafo,
**conserte o teste**. Não documente o backend na spec (hash de commit, nome de
CTE/tabela) — apodrece. Comente só o **porquê não-óbvio**, uma linha.

## Ligação com os casos manuais

Quando a spec automatiza um caso de `test/cases/*.feature`, cite o `@CT-XXX` no
título do `describe` ou numa linha de intenção. Assim a rastreabilidade
caso ↔ spec ↔ bug ↔ relatório se mantém.

---

# 5. Ciclo por teste — escrever · rodar · verde · aprovar

**Nenhum teste é entregue sem passar por este ciclo, um a um.**

```
1. você escreve a spec
2. você RODA a spec
3. você faz passar  (ver a regra abaixo — é onde se erra)
4. o QA aprova, como revisor
```

Não escreva a suíte inteira e mostre no fim. Vá por teste, ou por `describe`
pequeno. O QA revisa o que já está verde, não uma pilha de código não executado.

Ao apresentar para aprovação, mostre sempre:

- o código da spec
- a **saída real da execução** (verde, com tempo)
- qual `@CT-XXX` ela automatiza
- as decisões que você tomou: por que API e não E2E, por que duplicou em vez de
  extrair helper, por que aquele seletor

## ⚠️ "Fazer passar" tem um único significado legítimo

Verde só vale se o **sistema estiver certo e o teste estiver certo**. Existem três
motivos para uma spec ficar vermelha, e só um deles você conserta:

| Vermelho porque… | O que fazer |
|---|---|
| **A spec está errada** — seletor frágil, seed incompleto, assertion apontando para o campo errado, espera mal feita | Conserte a spec. É o único caso de "fazer passar". |
| **O sistema está errado** | **É bug.** Não toque na assertion. Registre com `/qa-defeito` e apresente a spec vermelha ao QA, explicando que ela documenta a regra correta. |
| **O ambiente está quebrado** — serviço fora, massa de referência ausente | Vermelho legítimo. Não mascare com skip. Reporte ao QA. |

🚫 **Proibido virar verde afrouxando a intenção:** trocar `toBe(201)` por
`toBeTruthy()`, aceitar `[200,201]`, remover a assertion que estava falhando,
adicionar `skip` ou `if`, aumentar timeout até "dar certo". Isso é fraude de teste
— viola a regra de ouro e a trava 2.

Se você se pegar mexendo na assertion para o teste passar, **pare e pergunte ao QA**.

**Isto não depende mais da sua disciplina.** O `qa_lint.py` lê o conteúdo da
spec e reprova o PR:

| Reprova | |
|---|---|
| `spec-sem-assercao-forte` | bloco cujas assertions são todas do tipo que passa com qualquer valor (`toBeTruthy`, `toBeDefined`, `toBeOK`, `assert x` nu) |
| `spec-status-ambiguo` | `[200, 201]` e parentes |
| `spec-desligada` | `.skip`/`xit`/`@pytest.mark.skip` num caso **aprovado**, ou `.only` em qualquer caso |

| Avisa | |
|---|---|
| `spec-assercao-fraca` | assertion fraca ao lado de fortes — confira se não é ela que prova a RN |
| `spec-espera-cega` | `waitForTimeout`, `time.sleep` |
| `spec-timeout-alto` | timeout acima de 30s |

Só vale para bloco que cita um `@CT-XXX` conhecido. Cenário travado por lacuna
aberta está `@nao-aprovado` no `.feature` — nesse, `.skip` é aceito, porque o
relatório já o conta como não coberto. Desligar a spec de um caso **aprovado**
é o que o lint impede: ele some do relatório como se estivesse coberto.

## A forma esperada

```ts
test.describe('RF-07 cupom no checkout — RN-01 valor mínimo', () => {
  // BVA sobre o piso de R$ 50,00. Os três casos existem porque o defeito que
  // esta regra costuma esconder é o ">" onde deveria haver ">=".

  test('CT-002 aceita o cupom no valor exato do mínimo', async () => {
    const pedido = await criarPedido({ total: 50.0 })
    const r = await aplicarCupom(pedido, 'PROMO10')

    expect(r.status()).toBe(200)
    // 50,00 − 10% = 45,00. Da regra, não da resposta.
    expect((await r.json()).total).toBe(45.0)
  })
})

test.describe('RF-07 — RN-07 empate com promoção', () => {
  // CT-011 está @nao-aprovado no .feature: a L-03 pergunta ao PO qual origem
  // prevalece no empate, e ninguém respondeu. Desligar aqui é coerente porque
  // o relatório já o conta como não coberto. Desligar um caso APROVADO é o que
  // o lint impede.
  test.skip('CT-011 mantém o cupom quando o desconto empata', async () => {
    /* ... */
  })
})
```

Repare no que ela **não** faz: nenhum número colado da execução — cada valor
esperado saiu da regra, e o comentário mostra a conta. Nenhuma asserção frouxa,
nenhum status ambíguo, nenhuma espera pelo relógio. O `@CT-XXX` no título é o
elo que sustenta a rastreabilidade caso ↔ spec ↔ bug ↔ relatório.

---

## O teste do teste — obrigatório antes de submeter

Depois de verde, **quebre o comportamento de propósito e confirme que o teste fica
vermelho.** Troque o valor esperado, inverta a condição. Teste que continua verde com o
sistema quebrado não é teste, é decoração. Trinta segundos por caso novo.

Relate ao QA que fez isso e o que quebrou para ver o vermelho.

## ⚠️ O seu viés — leia toda vez

**Você escreve o teste a partir do que o código faz, não do que o requisito manda.**
Quando o código tem defeito, o teste que você gera documenta o defeito como comportamento
esperado e passa verde para sempre. Esse é o risco central deste fluxo.

Regras que reduzem isso na origem:

1. **O valor esperado vem do requisito, calculado à mão** — nunca colado da execução.
   Pergunte-se: *de onde veio esse número?*
2. **Regra que não existe no documento não vira asserção** — vira `@premissa` para o QA
   confirmar.
3. **Todo teste que você escrever leva `@ia-gerado`, e a tag nunca é removida.** Ela
   permite, depois de um escape de defeito, perguntar se a origem tem correlação.
4. Suítes geradas por LLM apresentam score de mutação na casa de 20% em funções
   complexas. **Trate o que você produz como matéria-prima, nunca como entrega.**

Padrões que você deve caçar no próprio código antes de submeter: asserção que espelha a
implementação, asserção que espelha o mock, asserção decorativa ("o campo existe"), cinco
cenários no mesmo caminho feliz enquanto o limite ficou de fora, nome genérico.

---

# 6. Revisão de PR

Ao revisar spec (própria ou de terceiro), verifique nesta ordem. Qualquer item
marcado é **motivo de devolução**:

- [ ] Alguma assertion falha por motivo diferente da intenção do teste?
- [ ] `test.skip` condicional, `if/return` ou assertion frouxa (`toBeTruthy` em status,
      `toContain([200,201])`)?
- [ ] Teste depende de estado deixado por outro? `describe.serial` sem justificativa?
- [ ] Massa criada pela tela em vez da API?
- [ ] Regra de negócio testada em E2E que já é coberta na API (ou vice-versa)?
- [ ] Helper com flag booleana servindo dois chamadores?
- [ ] Título descreve método em vez de comportamento?
- [ ] Arquivo por micro-cenário em vez de por feature? Nome truncado?
- [ ] IDs hardcoded? Massa sem código único? Cleanup ausente?
- [ ] Comentário documentando o backend ou narrando o óbvio?
- [ ] AAA ilegível?

Antes de subir: `npm run lint` — o CI reprova o merge se falhar
(`no-conditional-in-test`, `no-skipped-test`, `no-wait-for-timeout`, `expect-expect`).

---

# 7. Performance (k6) — só se contratado no questionário

Teste de carga não entra na pirâmide funcional. Trate como suíte à parte, com meta
numérica explícita (ex.: `p95 < 800ms`), senão não há critério de passa/falha —
a mesma armadilha do critério de aceite sem número.

---

# 8. O que você NUNCA faz

- Escrever spec antes do questionário de frameworks
- Deixar `test.skip` que passa verde
- Criar massa pela interface
- Asserir detalhe de implementação
- Extrair helper com flag para reaproveitar corpo de cenário
- Duplicar a mesma regra em API e E2E
- Commitar sonda (`_probe*`) ou arquivo de depuração
- Entregar spec sem ter rodado
- Afrouxar assertion para virar verde
- Escrever a suíte inteira antes de submeter o primeiro teste à aprovação
