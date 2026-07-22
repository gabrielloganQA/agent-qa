---
name: qa-manual
description: Prepara e registra execução humana — monta o roteiro da rodada manual a partir da matriz, conduz sessão exploratória com charter e produz a folha de sessão. Use antes de cada ciclo e sempre que houver exploratório.
---

# qa-manual — execução humana

Entrada: `MATRIZ.md` + release em teste.
Saída: roteiro da rodada, folha de sessão em `test/sessoes/`, resultados em
`test/runs/manual/`.
Portão: **o QA executa e assina** (portão 4 — sessão exploratória).

📖 [`../design-casos-teste/references/testes-manuais.md`](../design-casos-teste/references/testes-manuais.md)

---

## 1. Roteiro da rodada — sai da matriz, não da lista completa

Entram **apenas**:

1. Casos `@camada:manual` permanentes
2. Casos `@automacao:pendente` de **risco alto**
3. Casos cuja regra foi tocada no ciclo
4. Retestes de defeito corrigido

Tudo mais é regressão automatizada. Se está sendo executado à mão, é **dívida
registrada**, não rotina — e o `qa-auditoria` vai perguntar por quê.

Gere o roteiro agrupado para o QA não refazer login a cada caso: blocos por
pré-condição, com o que fazer e o esperado literal em cada linha. Ele abre no segundo
monitor, não no editor de `.feature`.

---

## 2. Sessão exploratória

**Charter primeiro** — sem ele não é exploratório, é passeio:

```
Explorar ......... <área>
Com .............. <recursos, perfis, dados>
Para descobrir ... <tipo de risco>
Time-box ......... 60–90 min
```

Se você já sabe os passos, **não é exploratório** — é caso de teste, e deve ir para o
`.feature`.

### Quando o agente conduz a sessão

O QA dirige, você é as mãos e o caderno:

1. **Não navegue por conta própria.** Sugira o próximo passo, pergunte antes de executar.
2. **Relate o que observou, não o que concluiu.**
3. **Capture evidência** a cada passo relevante.
4. **No fim, proponha a colheita:** cada achado vira defeito, `@CT-XX` novo, ou nada.

⚠️ Sessão conduzida por agente é **exploração**, nunca regressão. O resultado vai para
`test/sessoes/`, com `executado_por: "agente"` — e **não** conta como execução oficial.
📖 [`../design-casos-teste/references/testes-com-mcp.md`](../design-casos-teste/references/testes-com-mcp.md)

---

## 3. Folha de sessão

`test/sessoes/AAAA-MM-DD-<tema>.md`, com: charter, build, ambiente, massa usada, o que
foi tentado, achados (e no que cada um virou), o que não foi coberto, e **tempo gasto em
preparação**.

O tempo de preparação é a métrica que sustenta a conversa sobre investir em factory: se
metade da sessão é montar massa, o problema não é o QA.

---

## 4. Registro dos resultados

**Você pergunta, o QA responde, você grava.** Aceite resposta em lote — *"1, 2 e 4
passaram, 3 e 5 falharam, 7 bloqueado"* — e confirme o entendimento antes de gravar.

Para cada falha: o que aconteceu, evidência, e se já existe defeito.
Para cada bloqueio: por que não deu para testar.

Grave em `test/runs/manual/AAAA-MM-DD-rodada-N.json` com `executado_por: "qa"`.

```bash
python3 test/scripts/qa_run.py --init N --data AAAA-MM-DD --executor "Nome" \
  --feature "..." --versao "..." --ambiente "..."
python3 test/scripts/qa_run.py --status
```

> **`falhou` ≠ `bloqueado`.** Bloqueado não é culpa do produto — é impedimento.
> Misturar os dois faz o relatório mentir sobre a qualidade da entrega.

Se ninguém executou, é `nao_executado`. **Nunca `passou` presumido.**

---

## 5. Compare com a rodada anterior

O que passou a falhar é **regressão**. O que passou a passar é **correção confirmada** —
e é o que o PMO quer ver no relatório.

Avise se houver caso `falhou` sem defeito registrado.

---

## O que você NUNCA faz

- Inventar resultado de execução
- Marcar `passou` sem alguém ter executado
- Gravar sessão de agente como execução oficial
- Usar `bloqueado` para esconder falha, ou `falhou` para impedimento de ambiente
- Montar roteiro com a lista completa de casos em vez do recorte da matriz
