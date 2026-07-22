# Parecer de release — v<X.Y.Z>

<!-- Portão 5. Gerado por /qa-relatorio a partir de test/runs/, MATRIZ.md e bugs/.
     Assinado por pessoa. Este .md é a FONTE; o .docx no modelo Atlante é o
     documento formal enviado por e-mail ao PMO e ao QA Leader. -->

**Recomendação:** LIBERAR · LIBERAR com ressalva · NÃO LIBERAR

---

## Critérios de saída

| Critério | Meta | Real | |
|---|---|---|---|
| Cenários de risco alto executados | 100% | | |
| Suítes `api` / `banco` / `contrato` verdes | 100% | | |
| `e2e @suite:smoke` verde | 100% | | |
| Defeitos S1 abertos | 0 | | |
| Defeitos S2 abertos | ≤ 2, com workaround | | |
| Conversão da feature | ≥ 80% | | |
| Testes em `@quarentena` | ≤ 2, com prazo | | |
| Regressão de p95 vs. baseline de QA | ≤ 10% | | |
| Sessões exploratórias das áreas de risco alto | executadas | | |

Exceção a qualquer critério exige **justificativa escrita e aprovação nominal** — não
silêncio.

---

## Segue para produção

Defeito que vai junto com a release. **Sem impacto de negócio, contorno e data de
correção preenchidos, o item não pode ser aprovado.**

| ID | Título | Sev. | Impacto | Contorno | Correção |
|---|---|---|---|---|---|
| | | | | | |

---

## Riscos residuais

| # | Risco | Probab. | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | | | | |

**Plano de rollback:**
**Monitoramento pós-deploy:** (métricas e janela)

---

## Não coberto

O que ficou de fora e em qual camada a lacuna ficou. Um parecer que só reporta o verde
recria o pior defeito do TMS antigo.

- Matriz de dispositivos:
- Cenários bloqueados por lacuna aberta:
- Casos `@automacao:pendente` de risco alto:

---

## Ambiente e evidências

- **Build:** api@ · front@ · schema@
- **Ambiente:** QA
- **Período:** a
- **Runs:** `test/runs/…`
- **Indisponibilidade do ambiente no ciclo:** h

---

**Assinado:** <nome> · <papel> · <AAAA-MM-DD>

> A assinatura é o portão 5. Decisão de risco tem nome e data — o merge não é a
> liberação.
