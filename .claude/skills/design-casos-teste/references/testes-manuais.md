# Exploratório, rodada manual, UAT e evidência

Referência carregada antes de cada ciclo de execução humana.

---

## 1. O que continua manual — e por quê

Manual não é "o que ainda não automatizamos". É o que **não se automatiza por natureza**:

| Permanece manual | Motivo |
|---|---|
| Exploratório | O valor está na variabilidade humana |
| Usabilidade, texto, layout, percepção | Exige julgamento |
| UAT | Aceite é do negócio, não do QA |
| Fluxo que depende de dispositivo físico | Coletor, impressora, leitor |
| Cenário com custo de automação maior que o de executar sempre | Decisão econômica, registrada |

⚠️ **Manual não é depósito do difícil.** `@automacao:nao-automatizar` **exige motivo
técnico escrito**. "Difícil" não é motivo; "depende de OTP por SMS de terceiro" é.

O `qa-auditoria` pergunta toda semana: *quais casos manuais não encontram defeito há 6
ciclos?* Caso manual que nunca acha nada é candidato a automação ou a exclusão.

---

## 2. Sessão exploratória

### Charter — sem ele não é exploratório, é passeio

```
CHARTER
Explorar ......... aplicação de cupom no checkout
Com .............. usuários de perfis diferentes e cupons no limite da vigência
Para descobrir ... comportamento na virada de data e em concorrência
Time-box ......... 90 min
```

- **Time-box de 60 a 90 minutos.** Acima disso a atenção cai e a sessão vira execução
  de roteiro.
- **Não vira Gherkin.** Se você já sabe os passos, não é exploratório — é caso de teste.
- O achado vira **defeito** ou **`@CT-XX` novo** na matriz. Achado que não vira nenhum
  dos dois morreu na memória de quem testou.

### Folha de sessão

`test/sessoes/AAAA-MM-DD-<tema>.md`. Mínimo:

```markdown
# Sessão — cupons no checkout
Data: 22/07/2026 · Executor: <nome> · Time-box: 90 min
Build: api@2.3.1 front@1.4.0 · Ambiente: QA
Massa: cupons PROMO-A (vigente), PROMO-B (vence hoje)

## Charter
<o charter acima>

## O que foi tentado
- ...

## Achados
| # | O que aconteceu | Vira |
|---|---|---|
| 1 | Cupom vencido às 23:59 ainda aplica | defeito PROJ-123 |
| 2 | Mensagem de erro genérica no limite por CPF | CT-031 (novo) |

## Não coberto
<o que ficou de fora e por quê>

## Tempo em preparação
35 min de 90 (39%) — massa não estava pronta
```

O campo **"tempo em preparação"** é o que sustenta a conversa sobre investir em factory:
se metade da sessão é montar massa, o problema não é o QA.

---

## 3. Rodada manual

O roteiro sai da matriz, **não da lista completa de casos**. Entram apenas:

1. Casos `@camada:manual` permanentes
2. Casos `@automacao:pendente` de **risco alto**
3. Casos cuja regra foi tocada no ciclo
4. Retestes de defeito corrigido

Tudo mais é regressão automatizada — se está sendo executado à mão, é dívida registrada,
não rotina.

### Registro

`test/runs/manual/AAAA-MM-DD-rodada-N.json`, com `executado_por: "qa"`.

Status: `passou` · `falhou` · `bloqueado` · `nao_executado` · `nao_aplicavel`

> **`falhou` ≠ `bloqueado`.** Bloqueado não é culpa do produto — é impedimento
> (ambiente caiu, massa ausente, dependência). Misturar os dois faz o relatório mentir
> sobre a qualidade da entrega.

Toda rodada compara com a anterior: o que passou a falhar é regressão; o que passou a
passar é correção confirmada.

---

## 4. UAT

- **É do PO.** O QA apoia com massa, ambiente e roteiro — e **não aprova em nome do
  negócio**.
- Achado de UAT entra pelo mesmo trilho de defeito, com a RN violada.
- Se o PO reprovar algo que passou em todos os testes, isso é **lacuna de requisito**:
  vira entrada em `LACUNAS.md`, não discussão sobre quem errou.

---

## 5. Evidência

Caminho datado: `test/image/DD-MM-AAAA/<nome>.png`

- **Toda falha tem evidência.** Sem print, vídeo ou resposta capturada, o defeito volta
  do dev como "não reproduzi".
- Nomeie pelo caso: `ct-017-bypass-checkout.png`.
- **Sucesso não precisa de evidência** — exceto quando o critério de saída exigir
  (auditoria, cliente regulado).
- Evidência de execução automatizada (trace, vídeo) é **artefato de CI**, com política
  de retenção definida. Git guarda caso e parecer para sempre; vídeo, não.

---

## 6. Antes de qualquer ciclo manual

- [ ] Build identificado e registrado
- [ ] Ambiente estável, massa carregada
- [ ] Roteiro gerado da matriz, não da lista inteira
- [ ] Comparativo com a rodada anterior à mão
- [ ] Alguém sabe quanto tempo isso deveria levar (para detectar quando dobrar)

---

## 7. Métrica que só a execução manual dá

| Métrica | Para quê |
|---|---|
| Horas de regressão manual por ciclo | Subindo 2 ciclos seguidos = a automação parou de acompanhar o produto |
| % do tempo em preparação | Acima de 30% = investir em factory |
| Casos manuais sem defeito há 6 ciclos | Candidatos a automação ou exclusão |
| Achados de exploratório que viraram CT | Mede se a sessão alimentou a suíte ou morreu na folha |
