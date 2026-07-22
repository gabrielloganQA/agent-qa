---
name: qa-relatorio
description: Gera o Relatório de Testes no modelo padrão Atlante (.docx) para o PMO e o QA Leader, com métricas calculadas, critérios de saída avaliados e proposta de GO/NO-GO.
---

# qa-relatorio — parecer de release

Só ao fechar a feature: casos executados, defeitos cadastrados, retestes feitos.

## 0. São dois artefatos, não um

| Artefato | O que é | Público |
|---|---|---|
| `test/releases/v<X.Y.Z>.md` | **a fonte** — parecer versionado, assinado, com riscos residuais e o que ficou de fora | o repositório, a auditoria |
| `Relatorio_de_Testes_*.docx` | **o entregável formal**, gerado da fonte, na identidade Atlante | PMO e QA Leader, por e-mail |

**Escreva o `.md` primeiro.** Ele é o que fica versionado e o que responde, daqui a seis
meses, quem liberou o quê e com qual ressalva. O `.docx` é a apresentação.

Modelo: [`../../../test/releases/TEMPLATE.md`](../../../test/releases/TEMPLATE.md)

## 1. Gere o .docx a partir dele

```bash
python3 test/scripts/qa_report.py --fase "Funcional" --release "vX.Y" \
  --build "#1234" --responsavel "Nome / Cargo"
```

Preenche `templates/Relatorio_de_Testes_Atlante.docx`, **preservando logo,
cabeçalho, rodapé (CNPJ + ISO 9001:2015 DNV), fontes e estilos**. Nunca recrie o
documento do zero — a identidade visual é obrigatória.

Saída: `test/Relatorio_de_Testes_<Projeto>_rodada-N.docx`

## 2. O que sai calculado

| Seção | Origem |
|---|---|
| 1. Sumário — taxas, defeitos, proposta GO/NO-GO | `test/runs/` + `bugs/` |
| 3. Resultados — planejado/executado/aprovado/reprovado/bloqueado | `test/runs/` |
| 4. Defeitos — contagem S1..S4 e lista dos abertos | `bugs/*.json` |
| 5. Critérios de saída — avaliados contra as metas | calculado |
| 7. Ambiente e ferramentas | `test/contexto.json` |

**Critérios de saída e suas metas:**

| Critério | Meta |
|---|---|
| Casos críticos executados | 100% |
| Taxa de aprovação geral | ≥ 95% |
| Defeitos S1 em aberto | 0 |
| Defeitos S2 em aberto | ≤ 2 |
| Cobertura de requisitos | ≥ 90% |
| Regressão automatizada | 100% |

**A recomendação é proposta, não decisão:** `NO-GO` se houver S1 aberto ou 3+
critérios falhando; `GO com ressalvas` se algum falhar; `GO` se todos passarem.

⚠️ **Confirme com AskUserQuestion, opções clicáveis** — mostre a proposta calculada e
o que a sustenta, e deixe o QA decidir:

| Opção | Descrição a exibir |
|---|---|
| `LIBERAR` | Todos os critérios de saída atendidos. Nenhuma ressalva registrada. |
| `LIBERAR com ressalva` | Segue com defeito conhecido. **Exige impacto, contorno e data de correção preenchidos** para cada item — sem isso o item não pode ser aprovado. |
| `NÃO LIBERAR` | Critério bloqueante não atendido. Registre qual e o que precisa mudar para reverter. |

Sempre inclua na descrição os números que sustentam a proposta: *"86% de aprovação
(meta ≥95%), 1 S2 aberto, conversão 0%"*.

**Quem decide é o QA. Você nunca assina o parecer.**

## 3. O que fica `[PREENCHER]` — e por quê

Campos que exigem julgamento humano, não cálculo:

- decisão final GO/NO-GO e a justificativa
- módulos e cobertura de requisitos (seção 2)
- itens fora de escopo, risco assumido e **quem aceitou**
- riscos residuais, plano de rollback, monitoramento pós-deploy
- impacto de negócio e contorno de cada defeito
- nomes de QA Leader e PMO

Percorra esses campos **com o QA** antes de distribuir. O template avisa: *"Sem
impacto de negócio, contorno e data de correção preenchidos, o item não pode ser
aprovado para produção."*

## 4. Avisos do script — leve a sério

- `defeito(s) sem severidade S1..S4 definida` → a tabela da seção 4 sai zerada e o
  relatório subestima a gravidade. Classifique antes de enviar.
- `criterios NAO atendidos` → confira se a justificativa cobre cada um.
- Se todos os casos foram executados por automação, diga isso ao QA: **ninguém
  olhou com olho humano**, e o PMO precisa saber.

O gerador **recusa** relatório sem execução. Relatório dizendo "100% aprovado"
sobre caso que ninguém rodou é pior que relatório nenhum.

## 5. Distribuição

O documento vai por e-mail ao **PMO** e ao **QA Leader**.

Não há MCP de e-mail configurado neste kit — monte o texto do e-mail (assunto,
corpo com o resumo executivo e a recomendação, documento anexado) e entregue ao
QA para enviar. Se um MCP de e-mail for conectado depois, use-o, mas **sempre
confirme destinatários e conteúdo antes de enviar**.

Assunto sugerido:
`[QA] Relatório de Testes — <Projeto> <Release> — <GO / GO com ressalvas / NO-GO>`
