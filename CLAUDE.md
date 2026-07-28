# Instruções do projeto — sistema de QA

Este repositório **é** o sistema de qualidade: casos, execução, defeitos e
parecer. Não existe TMS por trás. O que não está aqui não existe.

Estas regras valem em **toda** conversa, com ou sem comando `/qa-*`. Elas
existem porque o risco central deste fluxo é conhecido:

> **A IA escreve o teste a partir do que o sistema faz, não do que o requisito
> manda.** Quando o sistema tem defeito, o teste gerado documenta o defeito como
> comportamento esperado — e passa verde para sempre.

---

## As seis invariantes

**1. Nunca escreva `@aprovado-por:`.** Nem com o nome do QA, nem a pedido dele
nesta conversa. Aprovação é ato nominal de quem assume a responsabilidade, feito
no editor da pessoa. Um hook bloqueia a tentativa — se você foi bloqueado, o
comportamento correto é apresentar os cenários e pedir a aprovação, não procurar
outro caminho para gravar a tag.

**2. `@ia-gerado` nunca é removida.** É o que permite, depois de um escape de
defeito, perguntar se a origem tem correlação.

**3. O valor esperado vem da regra, calculado à mão — nunca colado da execução.**
Antes de escrever qualquer asserção, responda: *de onde veio este número?* Se a
resposta é "da tela" ou "da resposta da API", ele é `@premissa`, não asserção.

**4. Comportamento que o documento não define vira `@premissa` + entrada em
`LACUNAS.md`.** Nunca suposição silenciosa. Cobertura construída sobre suposição
é pior que cobertura ausente, porque parece pronta.

**5. Quando o sistema diverge da regra, PARE.** Não ajuste a asserção, não
afrouxe (`toBeTruthy`, `[200,201]`), não adicione skip, não aumente timeout.
Reporte e pergunte qual dos dois está errado — o sistema ou a regra.

**6. `test/runs/` é execução oficial e aceita `executado_por` `ci` ou `qa`.**
Nada que você executar entra ali. Sessão conduzida por agente é evidência de
exploração e vai para `test/sessoes/`.

---

## Antes de gravar em `test/cases/`

```bash
python3 test/scripts/qa_lint.py --feature <nome>
```

Não apresente ao QA cenário que o lint reprova. Um hook roda isso após cada
edição e devolve o erro — leia e corrija antes de seguir.

## Alocando ID de caso

```bash
python3 test/scripts/qa_lint.py --proximo-ct
```

`CT` é **global e nunca reciclado**. Não conte os casos da pasta e chute o
próximo — dois QAs em branches diferentes geram o mesmo número assim.

---

## Onde as coisas moram

| Preciso de… | Está em |
|---|---|
| o processo do time, ponta a ponta | [`docs/PROCESSO.md`](docs/PROCESSO.md) — manual de operação |
| vocabulário: tags, status, IDs | [`docs/GLOSSARIO.md`](docs/GLOSSARIO.md) — **fonte única** |
| como a conversa acontece | [`docs/COMO-FUNCIONA.md`](docs/COMO-FUNCIONA.md) |
| vim do Qase, e agora | [`docs/MIGRACAO-QASE.md`](docs/MIGRACAO-QASE.md) |
| onde provar o cenário | `.claude/skills/design-casos-teste/references/camadas-e-automacao.md` |
| como escrever o teste | `.claude/skills/design-casos-teste/references/escrita-de-testes.md` |

**Antes de escrever o primeiro cenário de uma feature, rode o lint** — ele
reprova a forma errada e a mensagem diz o que falta:

```bash
python3 test/scripts/qa_lint.py --feature <nome>
```

---

## Os comandos

| Comando | Quando |
|---|---|
| `/qa-intake` | abrir a feature: requisito, regras, lacunas |
| `/design-casos-teste` | derivar cenários por técnica |
| `/qa-roteamento` | decidir a camada de cada cenário |
| `/qa-automacao` | escrever a spec |
| `/qa-execucao` | abrir a rodada |
| `/qa-manual` | rodada humana e exploratório |
| `/qa-defeito` | registrar defeito com RN violada |
| `/qa-relatorio` | parecer de release |
| `/qa-auditoria` | varredura semanal |

## Scripts

```bash
python3 test/scripts/qa_lint.py               # consistência — roda em todo PR
python3 test/scripts/qa_ingest.py --junit r.xml --rodada N   # CI → histórico
python3 test/scripts/qa_run.py --executar N   # rodada manual, interativa
python3 test/scripts/qa_dashboard.py          # painel para PO/PMO
python3 test/scripts/qa_report.py             # .docx no modelo Atlante
python3 test/scripts/rise_bug.py --file b.json --rodada N    # defeito no AP
python3 test/scripts/qa_import_qase.py --csv export.csv      # migração
```

**Nenhum precisa de `pip install`.** Só biblioteca padrão — se você se pegar
propondo uma dependência, essa é a decisão errada.

---

## O que nunca decidir sozinho

O que é risco aceitável · o que uma ambiguidade de requisito significa · se a
release pode sair · se um defeito é aceitável em produção · se um cenário deixou
de fazer sentido · severidade e prioridade de um defeito.

Você propõe com justificativa. **Quem decide tem nome e data.**
