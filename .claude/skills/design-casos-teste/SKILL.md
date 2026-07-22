---
name: design-casos-teste
description: Deriva cenários de teste em Gherkin a partir de regras de negócio aprovadas, declarando a técnica que originou cada caso e submetendo tudo à aprovação do QA cenário a cenário. Use depois que as regras estiverem numeradas e as lacunas respondidas.
---

# design-casos-teste — o que testar

Transforma regra aprovada em cenário derivado por técnica. **Nada é gravado sem
aprovação do QA.**

Entrada: `test/requisitos/RF-XX-*.md` com `RN-XX` numeradas e `LACUNAS.md` respondido.
Saída: `.feature` + `MATRIZ.md` + `EXPLORATORIO.md`.
Portão: **QA aprova cenário a cenário** (portão 2).

Leia `test/contexto.json` antes de qualquer coisa e respeite as travas de `_efeitos` —
sem acesso a banco, você não sugere validação em banco; nem como opcional.

---

## 1. Proponha a técnica, regra a regra

Para cada `RN`, escolha as técnicas e **justifique**. O QA precisa poder discordar com
argumento.

| Técnica | Dispare quando a regra tiver… |
|---|---|
| Particionamento de Equivalência | faixas ou categorias de entrada |
| Análise de Valor Limite (BVA) | limites numéricos, datas, tamanhos |
| Tabela de Decisão | combinação de condições → ações |
| Transição de Estados | status, workflow, ciclo de vida |
| Teste de Caso de Uso | fluxo ponta a ponta com ator |
| Pairwise / All-Pairs | muitos parâmetros independentes |
| Teste de Sintaxe | formato — CPF, e-mail, código, JSON |
| Teste de Domínio | variáveis interdependentes |
| Error Guessing | ponto frágil, empate, concorrência |
| Exploratory | área nova, documentação fraca |
| Checklist-Based | requisitos transversais |
| Aleatório / Estatístico | volume, robustez, carga |
| Classification Tree | hierarquia de classes de entrada |

📖 Como aplicar cada uma e o erro típico: [`references/tecnicas.md`](references/tecnicas.md)

Apresente assim, e **espere a resposta**:

```
RN-03 — valor mínimo do pedido
  → BVA — fronteiras R$49,99 / R$50,00 / R$299,99 / R$300,00
  → Tabela de Decisão — tipo do cupom × valor × mínimo exigido

Concorda? Quer incluir ou tirar alguma?
```

---

## 2. Roteie a camada

**Cada cenário é provado em exatamente uma camada: a mais barata capaz de provar a
regra.** Partição, BVA e sintaxe vão para `api` — nunca para UI. Teto de `e2e`: 1 por
fluxo de negócio e ≤10% do total.

📖 Tabela de roteamento e regras por camada:
[`references/camadas-e-automacao.md`](references/camadas-e-automacao.md)

---

## 3. Escreva os cenários

`test/cases/<feature>/<feature>.feature`, em Gherkin declarativo — nunca imperativo.
De 3 a 7 passos, um comportamento por cenário, título = o "Então" resumido.

📖 Convenções completas e tabela de tags: [`references/gherkin.md`](references/gherkin.md)

**Tags obrigatórias:** `@CT-XX` `@RN-XX` `@camada:` `@suite:` `@ia-gerado` mais a
técnica. Todo cenário nasce `@nao-aprovado`.

⚠️ **Comportamento que você supôs porque o documento não define leva `@premissa` e
entra em `LACUNAS.md`.** Cenário com premissa pendente não vira código.

Quando o `Então` correto contraria o comportamento atual do sistema, escreva o
**correto** e avise que o caso vai falhar até a correção. Caso de teste documenta a
regra, não o defeito.

---

## 4. Monte a `MATRIZ.md`

Uma linha por regra e uma por caso, com o cabeçalho de lint no topo:

```markdown
<!-- qa-lint: requisito=../../requisitos/RF-07-cupons.md hash=<sha256:12> -->

| Regra | Origem | Técnica(s) | Cenários | Risco | Camada | Automação | Status |
```

O `hash` permite ao lint detectar **requisito alterado sem revisão dos casos** — a
falha que nenhum TMS pega, porque neles o requisito mora em outro sistema.

---

## 5. Monte o `EXPLORATORIO.md`

O que a derivação **não** cobre: charters, error guessing e checklists. Não vira
Gherkin nem automação.

📖 [`references/testes-manuais.md`](references/testes-manuais.md)

---

## 6. Portão — aprovação cenário a cenário

Mostre e pergunte: *"Aprova? Algum para ajustar, remover ou adicionar?"*

**Só grave depois do aval.** Ao aprovar, o QA troca `@nao-aprovado` por
`@aprovado-por:<usuario>`. Você nunca coloca essa tag sozinho.

Valide no fim:

```bash
python3 test/scripts/qa_lint.py
```

---

## 7. O seu viés — releia toda vez

**Você deriva o caso a partir do que o sistema faz, não do que o requisito manda.**
Quando o sistema tem defeito, o caso que você escreve documenta o defeito como
comportamento esperado — e passa verde para sempre.

1. O valor esperado vem da **regra**, calculado à mão. Nunca colado da execução.
2. Regra que não existe no documento **não vira asserção** — vira `@premissa`.
3. `@ia-gerado` nunca é removida.
4. Trate o que você produz como **matéria-prima, nunca entrega**.

📖 Padrões a caçar na revisão: [`references/escrita-de-testes.md`](references/escrita-de-testes.md) §15

---

## O que você NUNCA faz

- Gravar cenário sem aprovação do QA
- Adicionar `@aprovado-por:` por conta própria
- Supor comportamento em vez de abrir `@premissa`
- Sugerir teste em banco ou de segurança sem autorização no `contexto.json`
- Derivar caso lendo o código em vez do requisito

**Próximo:** `/qa-roteamento` confirma a camada · `/qa-automacao` gera o código
