# Simulação — um projeto do início ao fim

Exemplo trabalhado de ponta a ponta, do kick-off ao parecer assinado. É o material de
onboarding: mostra o sistema funcionando em vez de descrevê-lo.

Funcionalidade: **RF-12 — Transferência de material entre depósitos com conferência no
coletor.** Time: 1 QA, 1 SDET, 1 PO, 2 devs. Ciclo de duas semanas.

---

## Linha do tempo

| Dia | O que acontece | Comando | Artefato |
|---|---|---|---|
| 0 | Kick-off; documentação entra no repo **no mesmo dia** | — | `test/requisitos/RF-12-transferencia.md` |
| 1 | Requisito → regras numeradas e lacunas (40 min, era meio dia) | `/qa-intake` | `REGRAS.md` + `LACUNAS.md` |
| 1 | **Portão 1** — PO responde as 4 lacunas (20 min) | — | `LACUNAS.md` datado |
| 2 | Derivação dos cenários (1 h, era 1–2 dias) | `/design-casos-teste` | `.feature` + `MATRIZ.md` |
| 2 | **Portão 2** — QA aprova cenário a cenário (45 min) | — | `@aprovado-por:` `@data:` |
| 3 | Roteamento por camada (30 min) | `/qa-roteamento` | `@camada:` na matriz |
| 3–5 | Automação (1,5 dia, era 4–5 dias) | `/qa-automacao` | specs em `test/api/` |
| 5 | **Portão 3** — revisão de PR + suíte vista falhando (30 min) | — | PR aprovado |
| 6–8 | Execução no CI | `/qa-execucao` | `test/runs/*.json` |
| 8 | Defeito com vínculo RN ↔ CT ↔ run | `/qa-defeito` | card no AP |
| 9 | Rodada manual (1h40, era 5h) e exploratório | `/qa-manual` | `test/sessoes/` |
| 10 | **Portão 5** — parecer assinado | `/qa-relatorio` | `test/releases/v2.3.0.md` |

---

## Os dois momentos que justificam o sistema

### Dia 1 — a resposta do PO criou uma regra nova

```
L2 → Transferência parcial na conferência é permitida.
     Divergência gera pendência de conferência (regra nova: RN-07).
```

**RN-07 não estava no documento.** Apareceu porque alguém perguntou, no dia 1, antes de
existir uma linha de código.

Na matriz, a origem dessa regra **não é o requisito** — é a lacuna:

| Regra | Origem | Técnica | Cenários |
|---|---|---|---|
| RN-07 | **L2** | Tabela de decisão | CT-25..CT-28 |

### Dia 4 — o agente parou em vez de ajustar a asserção

```
PAREI. A RN-01 define disponível = físico − reservado = 6, e a RN-03 permite
quantidade ≤ disponível. O sistema recusou a transferência de 6 unidades com
SALDO_INDISPONIVEL. Ou o sistema usa "menor que" em vez de "menor ou igual",
ou a regra está errada. Não vou ajustar a asserção. Confirme qual dos dois.
```

Defeito clássico de fronteira (`<` em vez de `<=`), encontrado **no dia 4**, antes de
qualquer teste manual. No modelo antigo o teste teria sido escrito olhando o
comportamento do sistema, passaria verde, e o erro chegaria em produção.

---

## Antes × Agora

| Etapa | Antes | Agora | Tempo |
|---|---|---|---|
| Requisito → regras | Leitura e anotação | Regras numeradas + lacunas explícitas | 1 dia → 40 min |
| Ambiguidade | Preenchida por suposição | Bloqueia o cenário até o PO responder | — |
| Casos de teste | Digitados no TMS, sem técnica | Gherkin versionado, técnica declarada, matriz | 1–2 dias → 1 h |
| Aprovação | Não existia | Ato nominal com data; runner ignora o não aprovado | +45 min |
| Camada | Implícita; tudo virava tela | Decidida e verificada (E2E ≤10%) | +30 min |
| Automação | Escrita olhando o sistema | Escrita a partir da regra; divergência vira defeito | 4–5 dias → 1,5 dia |
| Revisão | Código | Código + **o teste é visto falhando** | +30 min |
| Execução | Marcada à mão | Histórico em arquivo, consultável | — |
| Defeito | Card com passos e evidência | Idem + vínculo RN ↔ CT ↔ run | igual |
| Manual | Rodada grande por hábito | Rodada por risco, com comparativo | 5 h → 1h40 |
| Exploratório | Acontecia, não ficava | Charter, folha e achados registrados | igual |
| Liberação | "Testes ok" no merge | Parecer assinado com ressalva e risco residual | +20 min |

> O tempo total cai — **mas não é o ponto**. O ponto é que, no dia 4, a regra de
> fronteira apareceu como defeito em vez de virar asserção errada; e no dia 1, quatro
> ambiguidades foram para o PO em vez de virarem suposição.

---

## Números para calibrar

| Medida | Valor observado | Serve para |
|---|---|---|
| Cenários por feature | 30 | Volume revisável por uma pessoa |
| Tempo de aprovação | 45 min para 28 cenários (~1,5 min cada) | **Banda de revisão** — o teto do sistema |
| Distribuição | 25 `api` · 1 `e2e` (3,4%) · 3 `manual` | Teto de E2E respeitado com folga |
| Rodada manual | 4 casos / 1h40 (era 11 / 5h) | Recorte por risco funciona |
| Tempo em preparação na sessão | 35% | Acima de 30% = investir em factory |
| Conversão da feature | 89% | Critério de saída |

**200 cenários por semana não é revisável.** Gere por feature, na ordem de risco.

---

## Onde isso dá errado

1. **O requisito chega ruim.** O agente não conserta requisito vago — devolve 12
   lacunas, e alguém precisa responder. Se o PO não responder, **o sistema trava de
   propósito.** É a intenção.
2. **A aprovação vira carimbo.** 30 cenários por feature é revisável; 200 por semana,
   não.
3. **O ambiente atrapalha.** 35% do tempo da sessão em preparação foi o maior
   desperdício da simulação, e nenhum agente resolve isso — resolve-se com factory e
   massa.

---

## Rastreabilidade — o teste dos seis meses

Daqui a seis meses alguém pergunta: *"por que existe o CT-25?"*

```
CT-25  →  RN-07  →  lacuna L2  →  resposta do PO em 24/07/2026
```

Três saltos, todos em arquivo versionado. É o que nenhum TMS entrega, porque neles o
requisito mora em outro sistema.
