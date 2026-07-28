# Migração do Qase para o modelo do kit

Guia operacional para o QA que tem um acervo no Qase e vai passar a trabalhar
neste repositório. Responde: **o que vem junto, o que não vem, e em que ordem
fazer** — para ninguém descobrir no meio do caminho que perdeu alguma coisa.

> **A regra que evita a maior dor:** não migre tudo de uma vez. Migre uma suíte,
> feche o ciclo dela até o parecer, e só então traga a próxima. Um acervo de 400
> casos importado num dia é um acervo de 400 casos que ninguém revisou.

---

## 1. O que o Qase guarda e onde isso cai aqui

| No Qase | Aqui | Vem no import? |
|---|---|---|
| Suite / pasta | `test/cases/<feature>/` | **sim** |
| Case: título | `Cenário:` no `.feature` | **sim** |
| Case: steps (action) | `Quando` / `E` | **sim** |
| Case: expected result | `Então` | **sim** |
| Case: preconditions | `Dado` | **sim** |
| Case: priority | `@prioridade:` | **sim** |
| Case: id | `@migrado:qase-<id>` | **sim**, para sempre |
| Case: status (deprecated) | ignorado por padrão | opcional |
| Case: layer | hint no `MIGRACAO.md` | **não** vira `@camada:` |
| Case: automation status | ignorado | **não** |
| **Regra de negócio que o caso prova** | `@RN-XX` | **não existe no Qase** |
| Test run / resultado histórico | `test/runs/` | **não** — ver seção 6 |
| Defeito ligado ao caso | `bugs/` + AP | **não** — ver seção 6 |

### As três colunas que não vêm — e por quê

**Regra de negócio.** O Qase não tem esse campo. Cada caso importado nasce
`@RN-PENDENTE`, e ligar caso a regra é o trabalho de verdade da migração. Isso
não é limitação da ferramenta nova: é a informação que nunca existiu, e que era
o motivo de ninguém conseguir responder *"por que este caso existe?"*.

**Camada.** O `layer` do Qase é campo de organização, não a decisão de "qual é a
forma mais barata de provar esta regra". Tudo entra como `@camada:manual` e o
`/qa-roteamento` decide. Aceitar o valor do Qase importaria a pirâmide invertida
junto com os casos.

**Status de automação.** O Qase diz "automated" sem exigir que exista código
apontando para o caso. Aqui, `@automacao:feito` só é aceito se uma spec neste
repositório citar o `@CT-XXX` — o lint reprova o contrário. Casos marcados
automatizados lá entram como `pendente` e aparecem contados no `MIGRACAO.md`.

---

## 2. Antes de importar — 20 minutos que economizam uma semana

- [ ] **Faça uma limpeza no Qase primeiro.** Todo caso obsoleto que você importar
      vai precisar ser revisado aqui. Apagar lá é mais barato.
- [ ] **Decida o recorte.** Uma suíte, não o projeto inteiro.
- [ ] **Tenha a documentação da feature em mãos** (Jira, Confluence, ata). Sem
      ela você não consegue numerar as RN, e a migração empaca no passo 3.
- [ ] **Combine com o PO** que vão existir perguntas. A migração revela as
      ambiguidades que o acervo antigo escondia.

### Exportando

Na interface do Qase: **Project → Test Cases → ⋯ → Export → CSV**. Marque todas
as colunas. Se preferir a API:

```bash
curl -s -H "Token: $QASE_TOKEN" \
  "https://api.qase.io/v1/case/SEUPROJETO?limit=100" > casos.json
```

O importador aceita os dois formatos e é tolerante a variação de cabeçalho — se
uma coluna não for reconhecida, ele segue sem ela em vez de abortar.

---

## 3. O caminho, em seis passos

### Passo 1 — importar

```bash
python3 test/scripts/qa_import_qase.py --csv export-qase.csv --dry-run
python3 test/scripts/qa_import_qase.py --csv export-qase.csv
```

Sempre `--dry-run` primeiro: ele mostra quais features seriam criadas e quantos
casos em cada uma, sem gravar nada.

Saem, por suíte: `.feature`, `MATRIZ.md`, `REGRAS.md` (vazio), `LACUNAS.md` e
**`MIGRACAO.md`** — a lista de pendência daquela feature.

```bash
python3 test/scripts/qa_lint.py     # deve passar, com avisos de @RN-PENDENTE
git add test/cases && git commit -m "chore: importa suíte X do Qase"
```

> O lint **avisa** e não reprova os `@RN-PENDENTE` de propósito: a dívida da
> migração precisa ser commitável para poder ser paga aos poucos.

### Passo 2 — registrar o requisito

```
/qa-intake
```

Cole a documentação da feature. Ele grava `test/requisitos/RF-XX-*.md` com hash,
preenche `REGRAS.md` com as `RN` numeradas e abre `LACUNAS.md` com as
ambiguidades. Depois ajuste o cabeçalho da `MATRIZ.md` para apontar para o
requisito real e rode:

```bash
python3 test/scripts/qa_lint.py --fix-hash
```

### Passo 3 — ligar caso a regra (o trabalho de verdade)

Troque cada `@RN-PENDENTE` pela `RN-XX` correspondente. Três desfechos possíveis,
e **todos os três são resultado válido**:

| O caso… | O que fazer |
|---|---|
| prova uma RN que existe | troque a tag. Migrado. |
| prova algo que não está em nenhuma RN | é **lacuna**: o requisito não cobre. Entra em `LACUNAS.md` para o PO. |
| não prova nada que alguém consiga enunciar | **apague**. Ele já não testava nada no Qase; aqui isso fica visível. |

O terceiro caso é o mais valioso e o mais desconfortável. Um acervo típico tem
entre 10% e 30% de casos que ninguém consegue justificar — e a migração é a
única hora em que isso é barato de resolver.

### Passo 4 — rotear

```
/qa-roteamento
```

Sai de `@camada:manual` para a camada mais barata capaz de provar cada regra.
É aqui que o teto de `e2e ≤ 10%` passa a valer — e o lint reprova se estourar.

### Passo 5 — aprovar

```
/design-casos-teste
```

Revisão cenário a cenário. O QA troca `@nao-aprovado` por
`@aprovado-por:<usuario> @data:<AAAA-MM-DD>` **no editor dele** — o agente é
bloqueado por hook se tentar escrever essa tag.

**Não aprove 200 cenários numa tarde.** A banda de revisão humana é o teto do
sistema: ~30 por feature, ~60 por semana. Acima disso a aprovação vira carimbo, e
você terá recriado o Qase com outra sintaxe.

### Passo 6 — fechar o ciclo

```bash
npx playwright test --reporter=junit --output-file=resultados.xml
python3 test/scripts/qa_ingest.py --junit resultados.xml --rodada 1 --criar
python3 test/scripts/qa_dashboard.py --snapshot
```

A suíte alimenta o histórico sozinha, e o painel mostra onde a migração está.

---

## 4. Como saber que terminou

```bash
python3 test/scripts/qa_dashboard.py
```

A migração de uma feature está **completa** quando:

- [ ] zero `@RN-PENDENTE`
- [ ] `REGRAS.md` preenchido e `MATRIZ.md` com hash real (não `PENDENTE`)
- [ ] toda RN tem ao menos um CT, ou um `@sem-caso:` justificado
- [ ] nenhum cenário em `@camada:manual` por omissão — só por decisão
- [ ] todo cenário com `@aprovado-por:` ou `@nao-aprovado` consciente
- [ ] `qa_lint.py` verde

O painel mostra a barra de progresso por feature. **Arquivo existir não é
migração terminada** — é migração começada.

---

## 5. O que muda no dia a dia

| | Qase | Aqui |
|---|---|---|
| Onde o caso mora | banco de dados do fornecedor | arquivo no git |
| Quem aprova | campo de status | pessoa, com nome e data na tag |
| Requisito mudou | ninguém percebe | lint reprova por hash |
| Resultado da suíte | reporter oficial | `qa_ingest.py` (JUnit XML) |
| Ver o estado | interface web | `qa_dashboard.py` → HTML |
| Histórico de quem mudou o quê | audit log do plano pago | `git blame`, de graça |
| Relatório para o PMO | export | `.docx` no modelo Atlante |
| Custo por assento | mensal, por pessoa | zero |

### O que você perde — e vale dizer em voz alta

- **Interface web para editar caso.** Aqui é editor de texto e git. Para quem não
  usa terminal, isso é atrito real; o `qa_dashboard.py` cobre a **leitura**, não
  a edição.
- **Notificação e atribuição dentro da ferramenta.** Passa a ser PR e code owner.
- **Botão de "rodar caso manual" com cronômetro.** Vira `qa_run.py --executar N`.

Se alguma dessas for inegociável para o seu time, é melhor saber agora do que
depois de importar 400 casos.

---

## 6. Histórico e defeitos: por que não migramos

**Resultado de execução histórica não vem.** Não porque seria difícil — porque
seria mentira. Um `passou` do Qase de março se refere a um caso que aqui ainda
não foi aprovado, cuja regra ninguém enunciou e cuja camada ninguém decidiu.
Importar isso encheria `test/runs/` de verde que nenhuma pessoa e nenhuma suíte
deste repositório produziu.

O histórico do Qase continua lá, somente leitura, enquanto a assinatura durar.
Se você precisa dele para auditoria, **exporte o CSV das runs e guarde como
anexo** — fora de `test/runs/`.

**Defeitos não vêm** porque já vivem no AP, que continua sendo o rastreador. O
que o kit acrescenta é o vínculo: `RN → CT → run → bug`, gravado quando você usa
`rise_bug.py --rodada N`.

---

## 7. Erros que a gente já viu

| Erro | O que acontece | O certo |
|---|---|---|
| Importar o projeto inteiro de uma vez | 400 casos `@nao-aprovado`, ninguém revisa, o lint vira ruído | uma suíte por vez |
| Aprovar em lote para "limpar" o lint | carimbo: você recriou o Qase | aprove o que leu |
| Usar `--manter-camada` sem pensar | a pirâmide invertida do Qase vem junto | rode `/qa-roteamento` |
| Marcar `@automacao:feito` na importação | o lint acusa automação fantasma | só depois da spec existir |
| Editar o requisito para "melhorar" | quebra o hash e apaga a evidência do que foi lido | o requisito é fonte, não rascunho |
| Deixar `@RN-PENDENTE` por meses | a migração nunca termina e vira o normal | prazo declarado, acompanhado no painel |

---

## 8. Rota curta

```bash
# 1. exporte do Qase (CSV) e confira o que viria
python3 test/scripts/qa_import_qase.py --csv export.csv --dry-run

# 2. importe e commite a dívida
python3 test/scripts/qa_import_qase.py --csv export.csv
python3 test/scripts/qa_lint.py

# 3. abra a feature no modelo novo
#    /qa-intake  →  troque os @RN-PENDENTE  →  /qa-roteamento  →  /design-casos-teste

# 4. acompanhe
python3 test/scripts/qa_dashboard.py --snapshot
```

