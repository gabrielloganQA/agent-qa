---
name: qa-auditoria
description: Varredura periódica do sistema de QA — cruza requisito × matriz × código × execução e responde o que um TMS respondia sozinho: quais regras não têm caso, quais casos nunca rodaram, quais testes estão verdes há meses sem nunca ter falhado.
---

# /qa-auditoria — a varredura semanal

O `qa-lint` verifica **consistência estrutural** (o ID existe dos dois lados) e roda em
todo PR. Esta auditoria verifica **saúde do sistema** e roda uma vez por semana. São
coisas diferentes: o lint impede a deriva; a auditoria encontra o que já derivou.

Saída: pauta da reunião semanal. Não conserta nada sozinho — **produz backlog**.

---

## 1. Rode o lint primeiro

```bash
python3 test/scripts/qa_lint.py
```

Se falhar, pare. Auditoria sobre base inconsistente produz número errado.

---

## 2. As sete perguntas

Cruze `test/requisitos/`, `test/cases/*/MATRIZ.md`, `test/runs/` e `bugs/`.

### 2.1 Quais regras não têm caso?
RN no requisito sem nenhum `CT` na matriz, e sem `@sem-caso:` justificado.
**É lacuna de cobertura, não de execução.** A mais grave das sete.

### 2.2 Quais casos nunca foram executados?
`CT` na matriz que não aparece em nenhum `test/runs/*.json`.
Caso escrito e nunca rodado é documentação, não teste.

### 2.3 Quais testes estão verdes há muito tempo sem nunca ter falhado?
Cruze o histórico de runs. Um teste que **nunca** ficou vermelho em 6 meses é
suspeito: ou a regra não muda nunca, ou o teste não verifica nada (Dead Test).

➡️ Candidatos ao **teste do teste**: quebre o comportamento e confirme o vermelho.
Se continuar verde, é decoração — apague ou conserte.

### 2.4 Qual a taxa de flaky por caso?
`CT` que aparece como `flaky` ou alterna pass/fail entre runs sem mudança de código.
Meta abaixo de 1%. Acima disso as pessoas apertam retry no reflexo e a suíte deixa de
ser sinal.

Verifique o teto de quarentena: **≤ 2, com prazo definido**.

### 2.5 A distribuição por camada está derivando?
Percentual em cada `@camada:`. Alvo: `api+banco+contrato ~90%`, `e2e ≤10%`.
**Migração silenciosa de cenários para o E2E** é o padrão de deriva mais comum — a
suíte fica lenta um cenário por vez, e ninguém percebe até estourar o tempo.

### 2.6 Quais lacunas estão abertas há muito tempo?
`LACUNAS.md` com data. Lacuna aberta há mais de **5 dias** significa que ninguém está
respondendo — e todo `@premissa` que depende dela continua fora da suíte oficial.

Reporte: **quantos cenários estão bloqueados por lacuna sem resposta.** Isso converte
"o PO não respondeu" em número.

### 2.7 Qual a conversão, por feature?
`@automacao:feito` sobre cenários aprovados, **por feature, nunca global**.
A média esconde a feature crítica com 20%.

---

## 3. Apresente assim

```
AUDITORIA — semana de DD/MM

Cobertura
  RN sem caso ................ 1  (RN-08, desde 15/07)
  Casos nunca executados ..... 3  (CT-023, CT-024, CT-031)
  Lacunas abertas >5d ....... 2  (L-02, L-04) → 5 cenários bloqueados

Confiança
  Flaky .................... 0,4%  (CT-031)
  Em quarentena .............. 1  (CT-031, prazo 28/07)
  Verdes há >6 meses sem falhar  7 → candidatos ao teste do teste

Roteamento
  api 77% · seguranca 14% · e2e 9%     teto respeitado

Conversão por feature
  saucedemo ................. 0%   ← risco alto, prioridade
  checkout .................. 82%

PAUTA
  1. RN-08 sem caso desde 15/07 — quem escreve?
  2. L-02 e L-04 travando 5 cenários — escalar com o PO
  3. 7 testes nunca vermelhos — rodar teste do teste em 2 por semana
```

Ordene por **impacto em risco**, não por quantidade.

---

## 4. O que NÃO fazer

- **Não conserte durante a auditoria.** A saída é backlog priorizado; corrigir no meio
  faz você perder a visão do todo e o relatório sai incompleto.
- **Não reporte só o que está bom.** Suíte verde com flaky alto e conversão baixa não
  significa qualidade — significa que ninguém está olhando.
- **Não agregue métrica entre features.** A média é onde a feature crítica se esconde.
- **Não trate "nunca falhou" como sucesso.** É o sinal mais forte de Dead Test.

---

## 5. Ao reportar, diga sempre o que ficou de fora

Toda auditoria termina com a lista do que **não** está coberto e em qual camada a
lacuna ficou. Um sistema que só reporta o verde recria o pior defeito do TMS antigo:
um catálogo em que ninguém confia.
