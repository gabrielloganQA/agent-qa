---
name: qa-roteamento
description: Define em qual camada cada cenário aprovado será provado — api, banco, contrato, e2e, performance, seguranca ou manual — e registra camada e suíte na matriz. Use depois que o QA aprovar os cenários e antes de automatizar qualquer coisa.
---

# qa-roteamento — onde cada cenário é provado

Entrada: cenários derivados pelo `/design-casos-teste`, aprovados ou não.
Saída: `@camada:` e `@suite:` na `MATRIZ.md` e no `.feature`.
Portão: QA confirma; o `qa-lint` valida o teto de E2E.

> **Por que a entrada não exige `@aprovado-por:`.** O `qa_lint` cobra `@camada:`
> e `@suite:` de **todo** cenário, então a camada tem de existir antes da
> aprovação — o `/design-casos-teste` já atribui uma no passo 2. Este comando
> **revisa e confirma** esse roteamento, e é o lugar certo para reclassificar
> quando o percentual de E2E estourar. Rodar antes ou depois do portão 2 é
> escolha do QA; o que não pode é o cenário chegar à automação sem camada
> confirmada.

📖 Regras completas por camada:
[`../design-casos-teste/references/camadas-e-automacao.md`](../design-casos-teste/references/camadas-e-automacao.md)

---

## Regra zero

> **Cada cenário é provado em exatamente UMA camada: a mais barata capaz de provar a regra.**

Duplicar a mesma regra em duas camadas não aumenta cobertura — aumenta manutenção e
produz dois testes que quebram juntos pelo mesmo motivo. Se um cenário parece precisar
de duas camadas, ele testa duas coisas e deve ser dividido.

---

## Tabela de roteamento — a primeira linha que casar decide

| Se o cenário… | Camada |
|---|---|
| valida formato, máscara, cálculo, faixa numérica, mensagem de erro de campo | `api` |
| verifica status, schema, paginação, filtro, ordenação, idempotência | `api` |
| verifica quem **pode** executar a ação | `api` + `seguranca` |
| exige confirmar dado gravado, contador, auditoria, evento publicado | `api` + `banco` |
| percorre transição de estados | `api` (matriz) + `e2e` (só o principal) |
| é jornada de negócio completa, com valor direto | `e2e` |
| tem número no requisito: tempo, volume, concorrência | `performance` |
| depende de terceiro fora do nosso controle | `contrato` + mock na regressão |
| depende de julgamento humano | `manual` |

⚠️ **Partição, BVA e sintaxe nunca viram cenário de UI.** 12 casos de limite custam 12
requisições, não 12 fluxos de tela. O número de casos derivados pela técnica não muda —
muda o custo de executá-los.

---

## Suíte

| `@suite:` | Roda quando | Teto |
|---|---|---|
| `smoke` | a cada deploy no ambiente de QA | 5 min |
| `regressao` | build aceito | 15 min |
| `nightly` | diária | sem limite |
| `release` | candidato a release | — |

**Estourou o teto? Reclassifique cenários para camada mais barata — nunca aumente o teto.**

---

## Tetos que o lint verifica

- `e2e` ≤ **max(1, 10%)** dos cenários da feature
- Distribuição de referência: `api+banco+contrato ~90%`, `e2e ≤10%`

`performance` e `seguranca` ficam fora dessa conta — entram conforme o requisito exigir.

---

## Ao apresentar ao QA

```
RN-03 · CT-007..CT-012  → api        (BVA, 6 casos de fronteira)
RN-05 · CT-015          → e2e        (jornada de pagamento — 1 por fluxo)
RN-05 · CT-014, CT-016  → api        (validação de campo e transição)
RN-01 · CT-006          → seguranca  (acesso sem autenticação)

e2e: 1 de 22 (4,5%) — dentro do teto
Confirma?
```

Mostre sempre o **percentual de e2e resultante**. É o número que denuncia migração
silenciosa da pirâmide.

---

## Depois de confirmado

1. Grave `@camada:` e `@suite:` nas tags do cenário
2. Atualize as colunas **Camada** e **Automação** (`pendente`) na `MATRIZ.md`
3. Rode `python3 test/scripts/qa_lint.py`

`@automacao:nao-automatizar` **exige motivo técnico escrito**. "Difícil" não é motivo;
"depende de OTP por SMS de terceiro" é.

**Próximo:** `/qa-automacao`
