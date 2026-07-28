# Processo de QA — manual de operação

**Kit v1.3.0** · atualizado em 28/07/2026 · time: 2 QAs, assinaturas independentes

Este é o documento de **operação**: quem faz o quê, quando, com qual comando, e
como se sabe que terminou. Os outros documentos respondem outras perguntas:

| Documento | Responde |
|---|---|
| este | **como operamos** — o dia a dia, com os comandos reais |
| [`COMO-FUNCIONA.md`](COMO-FUNCIONA.md) | *como a conversa acontece* — o que o agente pergunta e por quê |
| [`SIMULACAO-RF-12.md`](SIMULACAO-RF-12.md) | *o ciclo inteiro num exemplo narrado* |
| [`MIGRACAO-QASE.md`](MIGRACAO-QASE.md) | *como sair do Qase sem perder nada* |
| [`GLOSSARIO.md`](GLOSSARIO.md) | *o vocabulário* — fonte única de tags, status e IDs |

---

## 1. A premissa

> **O agente escreve o teste a partir do que o sistema faz, não do que o
> requisito manda.** Quando o sistema tem defeito, o teste gerado documenta o
> defeito como comportamento esperado — e passa verde para sempre.

Todo o processo existe para conter isso. Por consequência:

- Tudo que o agente produz nasce `@ia-gerado @nao-aprovado`.
- Cinco portões humanos decidem o que atravessa.
- O valor esperado vem da **regra**, calculado à mão — nunca colado da execução.
- Quando o sistema diverge da regra, o agente **para**; não ajusta a asserção.

---

## 2. Os cinco portões

| # | Portão | Quem | O que trava | Como é garantido |
|---|---|---|---|---|
| 1 | Resposta às lacunas | PO | cenário com `@premissa` não vira cobertura | `qa_lint.py` |
| 2 | Aprovação do cenário | QA | `@nao-aprovado` fica fora da suíte oficial | **hook + lint** |
| 3 | Revisão do PR de teste | QA / SDET | código sem revisão não entra na suíte | `CODEOWNERS` |
| 4 | Sessão exploratória | QA | não é execução oficial | **hook + lint** |
| 5 | Parecer de release | QA leader | decisão de risco tem nome e data | assinatura |

Os portões 2 e 4 deixaram de ser convenção na v1.1.0.
`.claude/hooks/guarda_portao.py` **bloqueia** o agente que tenta escrever
`@aprovado-por:`, remover `@ia-gerado` ou gravar `executado_por: agente` em
`test/runs/`.

Na v1.2.0 o hook passou a cobrir também o **`Bash`**: até então `sed -i`,
`cat >` e `python3 -c` gravavam as mesmas tags por fora do portão, e o lint
não pega esse caso — ele cobra `@aprovado-por` quando a tag *falta*, nunca
valida quem a escreveu. Contar aprovação (`grep aprovado-por`, sem o valor)
continua liberado.

⚠️ Quando **você** edita o `.feature` no seu editor para aprovar, nada dispara.
**A assimetria é o portão** — aprovação é ato nominal de quem responde por ela.
Se o agente for bloqueado, o comportamento certo é apresentar os cenários e
pedir a aprovação, não procurar outro caminho.

---

## 3. O ciclo de uma feature

Tempos de referência vindos da simulação da RF-12 — calibre com os seus.

### 3.1 Abertura — `/qa-intake` (~40 min)

Cole a documentação da feature (texto, arquivo ou link). O agente:

1. aponta as **ambiguidades antes de qualquer pergunta**;
2. faz 8 perguntas clicáveis (ambiente, banco, logs, contrato, cache/fila,
   segurança, cobertura, projeto no AP);
3. grava `test/contexto.json` com o bloco `_efeitos` — o que cada resposta travou;
4. extrai `REGRAS.md` (RN numeradas) e `LACUNAS.md` (perguntas ao PO).

Mande as lacunas ao PO e **siga trabalhando**. Não espere.

> ⚠️ Não rode o lint aqui esperando verde. A pasta ainda não tem `.feature` — ele
> nasce no desenho. `pasta sem nenhum .feature` é o estado **correto** entre o
> intake e o desenho.

**Pronto quando:** os quatro arquivos existem, as RN estão numeradas e
confirmadas por você, e cada lacuna tem dono e data.

### 3.2 Desenho — `/design-casos-teste` (~1h + 45 min de revisão)

O agente propõe a técnica **regra a regra, com justificativa**, e espera resposta.
Depois escreve os cenários em Gherkin declarativo e pergunta *"aprova? algum para
ajustar, remover ou adicionar?"*.

**Este é o momento que define se o processo funciona ou vira teatro.** Leia os
cenários um a um — cerca de 1,5 min cada. Na simulação, o QA rejeitou 1
duplicado, corrigiu 1 que assumia herança de permissão (virou lacuna nova) e
**acrescentou 1 de próprio punho**. Isso é o portão funcionando, não falha do
agente.

Depois abra o `.feature` **no seu editor** e troque `@nao-aprovado` por
`@aprovado-por:<usuario> @data:<AAAA-MM-DD>`.

```bash
python3 test/scripts/qa_lint.py
git add test/cases && git commit -m "feat: casos da RF-XX aprovados"
```

**Pronto quando:** lint verde, todo cenário com `@aprovado-por:` ou
`@nao-aprovado` consciente, e os que dependem de lacuna aberta marcados
`@premissa`.

### 3.3 Roteamento — `/qa-roteamento` (~30 min)

Cada cenário é provado em **exatamente uma camada: a mais barata capaz de provar
a regra**. O agente apresenta o agrupamento com o **percentual de e2e
resultante**:

```
RN-03 · CT-007..CT-012  → api        (BVA, 6 casos de fronteira)
RN-05 · CT-015          → e2e        (jornada de pagamento — 1 por fluxo)

e2e: 1 de 22 (4,5%) — dentro do teto
Confirma?
```

Teto: `e2e ≤ max(1, 10%)`. Estourou? **Reclassifique para camada mais barata —
nunca aumente o teto.** O lint reprova.

**Pronto quando:** `@camada:` e `@suite:` em todo cenário, matriz atualizada,
lint verde.

### 3.4 Automação — `/qa-automacao` (~1,5 dia)

Cinco perguntas de framework antes da primeira linha. Depois, **um teste por
vez**: escreve → roda → mostra a saída real → você aprova como revisora.

⚠️ **A spec tem que citar o `@CT-XXX` no título.** É o que o `qa_ingest.py` casa
depois. Sem isso o teste roda e não entra no histórico.

O momento que justifica o processo é quando o agente para:

```
PAREI. A RN-01 define disponível = físico − reservado = 6, e a RN-03 permite
quantidade ≤ disponível. O sistema recusou 6 unidades com SALDO_INDISPONIVEL.
Ou o sistema usa "<" em vez de "<=", ou a regra está errada. Não vou ajustar
a asserção. Confirme qual dos dois.
```

Antes do merge: **quebre o comportamento de propósito e confirme o vermelho.**
Trinta segundos por caso novo.

**O lint lê a spec, não só o nome dela.** Até a v1.2.0 os guarda-corpos paravam
no Gherkin: o `.feature` era policiado por uma dúzia de regras e o código que
implementa o cenário só era conferido para provar que `@automacao:feito` não era
fantasma. Dava para o cenário dizer *"o total deve ser 90,00"* e a spec dizer
`expect(total).toBeTruthy()`.

Reprova o PR: bloco sem nenhuma asserção forte · dois status HTTP aceitos ·
`.skip` num caso **aprovado** · `.only`.
Avisa: asserção fraca ao lado de fortes · espera fixa · timeout acima de 30s.

Se o teste reprova e você acha que o certo é afrouxar, **é aí que se para** —
não é a asserção que está errada, é o sistema ou a regra, e quem decide qual
tem nome. Cenário que legitimamente não pode rodar se marca `@nao-aprovado` no
`.feature`, com a lacuna aberta: aí o `.skip` é coerente e o lint aceita.

**Pronto quando:** PR revisado com o checklist, suíte vista falhando,
`@automacao:feito:<PR>` na matriz.

### 3.5 Execução

**Automatizada — o único caminho oficial:**

```bash
npx playwright test --reporter=junit --output-file=resultados.xml
python3 test/scripts/qa_ingest.py --junit resultados.xml --rodada 1 --criar --build "#4471"
```

Grava com `executado_por: ci`. Um CT citado em vários testes recebe a **pior
notícia**: se qualquer um falhou, o caso falhou. `skipped` vira `nao_executado`,
nunca `passou`.

**Manual — só o recorte de risco**, nunca a lista completa:

```bash
python3 test/scripts/qa_run.py --init 2 --manual --data 2026-07-31 \
  --executor "Nome" --feature "RF-XX" --versao "v2.4.0" --ambiente "QA"
python3 test/scripts/qa_run.py --executar 2
```

Modo interativo, caso a caso: `[p]assou` `[f]alhou` `[b]loqueado`
`[n]ao executado` `[x]` não aplicável `[s]air`. Falha pede o que aconteceu,
evidência e número do bug.

Entram na rodada manual **apenas**: casos `@camada:manual` permanentes, casos
`@automacao:pendente` de risco alto, casos cuja regra foi tocada no ciclo, e
retestes de defeito corrigido. O `--init --manual` já exclui os
`@automacao:feito` — o CI é dono deles — e o `--executar` respeita esse recorte.

> **Use o MESMO número de rodada do CI.** Uma rodada tem dois donos e dois
> arquivos: `runs/rodada-N.json` (CI) e `runs/manual/<data>-rodada-N.json` (QA).
> Escrever separado é o que impede o agente de tocar no histórico oficial; na
> **leitura**, o painel e o parecer fundem os dois pelo número. Numerar a rodada
> manual como 2 quando o CI foi 1 cria dois ciclos onde houve um só, e o parecer
> passa a contar o ciclo pela metade.
>
> Quando o mesmo caso tem resultado nos dois arquivos, **a pessoa vence**: você
> reexecuta um caso justamente quando desconfia do verde da suíte, e é você quem
> assina o parecer.

> **`falhou` ≠ `bloqueado`.** Bloqueado não é culpa do produto — é impedimento.
> Misturar os dois faz o relatório mentir sobre a qualidade da entrega.
> Se ninguém executou, é `nao_executado`. **Nunca `passou` presumido.**

**Pronto quando:** toda falha tem evidência em `test/image/DD-MM-AAAA/` e bug
cadastrado.

### 3.6 Defeito — `/qa-defeito`

**Sem RN violada, não abre.** Regra não documentada vira lacuna; preferência vira
sugestão de melhoria.

```bash
python3 test/scripts/rise_bug.py --template > bugs/ct-007-saldo.json
# edite; a severidade PRECISA começar com S1..S4
python3 test/scripts/rise_bug.py --file bugs/ct-007-saldo.json --rodada 1
```

Três perguntas clicáveis (severidade, prioridade, projeto), preview e
confirmação. **Severidade e prioridade são eixos independentes** — um bug pode
ser S1 com prioridade Baixa.

`--rodada N` grava o número do bug dentro do caso na rodada. **Use sempre**: é o
elo que sempre se perde no passo manual.

### 3.7 Fechamento — `/qa-relatorio`

```bash
python3 test/scripts/qa_dashboard.py --snapshot
python3 test/scripts/qa_report.py --fase "Funcional" --release "v2.4.0" \
  --build "#4471" --responsavel "Nome / Cargo"
```

O agente calcula os critérios e **propõe** GO / GO com ressalvas / NO-GO com os
números que sustentam. Você decide, escreve o parecer em
[`../test/releases/TEMPLATE.md`](../test/releases/TEMPLATE.md) e assina. O `.docx`
no modelo Atlante sai dele.

**O agente nunca assina.**

### 3.8 Auditoria — `/qa-auditoria` (semanal)

Não conserta nada: **produz backlog priorizado**. Responde o que o TMS respondia
sozinho — quais regras não têm caso, quais casos nunca rodaram, quais testes
estão verdes há meses sem nunca ter falhado, e onde a pirâmide está derivando.

### 3.9 O painel — o que o PO e o PMO abrem

`qa_dashboard.py` gera um HTML estático e autocontido: sem CDN, sem servidor,
abre offline com duplo clique. É o substituto do painel do Qase, com uma
diferença de natureza — lá era um serviço lendo o banco deles, aqui é
**derivado**, recalculado do repositório a cada execução. Por isso
`test/dashboard.html` não é versionado.

| Onde | Quando |
|---|---|
| **GitHub Pages** — `https://<org>.github.io/<repo>/` | a cada push na `main` |
| artefato do run | em todo PR |
| local | `python3 test/scripts/qa_dashboard.py` |

> ⚠️ **Confirme o plano antes do primeiro deploy do Pages.** Publicar a partir de
> repositório privado exige plano pago, e restringir o **site** aos membros da
> organização só existe no Enterprise Cloud. Nos demais planos ele fica
> **público**, e o painel expõe nomes de feature, lacunas em aberto e contagem de
> defeitos. Para desligar, apague o job `paginas` de `.github/workflows/qa.yml` —
> o artefato continua entregando o mesmo arquivo.

A série histórica é gravada por um **job diário às 8h**, que roda `--snapshot` e
commita `test/metricas/`. Não depende mais de alguém lembrar na auditoria:
métrica sem série responde "como estamos", nunca "melhoramos?".

---

## 4. Convenções do time

### 4.1 Reserva de bloco de `CT` — duas pessoas, dois branches

`qa_lint.py --proximo-ct` só enxerga o que está na máquina de quem rodou. Se os
dois abrem feature na mesma segunda, **ambos recebem o mesmo número**. O lint
pega no merge, mas pega tarde.

**Quem abre a feature reserva um bloco e anota no cabeçalho da `MATRIZ.md`:**

```
RF-14 → CT-100..CT-149  (Ana)
RF-15 → CT-150..CT-199  (Bruno)
```

`git pull` antes de abrir feature nova resolve o resto. `CT` é global e **nunca
reciclado** — caso aposentado vira `@obsoleto:<data>` e o número não volta.

### 4.2 Higiene de sessão

Duas regras, e só:

1. **`/clear` entre as fases.** Intake numa sessão, desenho em outra, automação
   em outra. As fases se comunicam por arquivo, não por contexto — o kit foi
   desenhado assim.
2. **MCP de navegador só em exploratório com charter escrito.** Cada
   `browser_snapshot` devolve a árvore inteira da página. Quem só testa API deve
   recusar os MCPs na primeira abertura.

### 4.3 A banda de revisão é o teto do sistema

| Medida | Referência |
|---|---|
| Cenários por feature | ~30 |
| Tempo de aprovação | ~1,5 min por cenário |
| Cenários por semana | **não passe de ~60** |

**Gere por feature, na ordem de risco. Nunca em lote.** Acima disso a aprovação
vira carimbo — e um catálogo em que ninguém confia é exatamente o defeito do TMS
que saímos para evitar.

---

## 5. O que é automático e o que exige julgamento

Metade do ciclo **não passa pelo modelo**. São scripts Python determinísticos,
biblioteca padrão, sem `pip install`:

| Trabalho | Como | Custo |
|---|---|---|
| Consistência dos casos | `qa_lint.py` | script |
| Resultado da suíte → histórico | `qa_ingest.py` | script |
| Rodada manual interativa | `qa_run.py --executar` | script |
| Painel para PO e PMO | `qa_dashboard.py` | script |
| Relatório no modelo Atlante | `qa_report.py` | script |
| Cadastro de defeito no AP | `rise_bug.py` | script |
| Importação do Qase | `qa_import_qase.py` | script |
| **Derivar caso a partir de regra** | `/design-casos-teste` | **julgamento** |
| **Achar ambiguidade no requisito** | `/qa-intake` | **julgamento** |
| **Diagnosticar falha vermelha** | `/qa-automacao` | **julgamento** |
| **Decidir risco, severidade, liberação** | **pessoa** | **nunca o agente** |

Se você se pegar pedindo ao agente algo que tem script, pare e rode o script.

---

## 6. Quando o sistema trava — e por que isso é certo

| Trava | Quem destrava | O que fazer enquanto isso |
|---|---|---|
| Lacuna sem resposta há +5 dias | PO | aprove o resto; `@premissa` só no que depende |
| Cenário sem aprovação | QA | automatize o que já está aprovado |
| PR de teste na fila | SDET / QA leader | revise por risco: alto primeiro |
| Ambiente instável | Dev / infra | **registre a indisponibilidade em horas** |
| Suíte vermelha sem defeito | QA | quarentena imediata, com prazo |
| Requisito mudou (hash) | QA | revise os casos das RN afetadas, depois `--fix-hash` |

> Se o PO não responder, **o sistema trava de propósito.** Cobertura construída
> sobre suposição é pior que cobertura ausente, porque parece pronta.

---

## 7. Migração do Qase — o essencial

Passo a passo completo em [`MIGRACAO-QASE.md`](MIGRACAO-QASE.md). O que não pode
ser esquecido:

- **Uma suíte por vez**, fechando o ciclo até o parecer antes de trazer a
  próxima. 400 casos importados num dia são 400 casos que ninguém revisou.
- **Sempre `--dry-run` primeiro.**
- Caso importado nasce `@RN-PENDENTE`, `@nao-aprovado` e `@camada:manual`,
  porque **o Qase não guarda regra de negócio nem decisão de camada**.
- 10% a 30% do acervo típico não liga a regra nenhuma. Esses devem ser
  **apagados**, não migrados — já não testavam nada lá, só que não aparecia.
- **A migração termina quando `@RN-PENDENTE` chega a zero**, não quando os
  arquivos existem. Declare prazo por suíte e acompanhe no painel.

---

## 8. Estado de verificação — o que foi provado e o que não

Honestidade sobre o kit v1.3.0, para ninguém depender do que não foi testado.

**Verificado, com execução real:**

- o lint reprova as violações que promete (testado quebrando de propósito)
- ciclo importação → lint → `qa_ingest` → painel, ponta a ponta
- os hooks negando e liberando, com o payload real — inclusive por `Bash`
- **`qa_report.py` gerando o `.docx`**: ciclo completo com dados de exemplo,
  `.docx` válido, sumário e tabela de critérios preenchidos
- 90 testes do kit, verdes
- **as regras de spec, por mutação**: cada peça da checagem foi desligada uma a
  uma e 9 das 10 derrubam a suíte — a décima é atalho de desempenho, anotada
  como tal. Regra que ninguém invoca é comentário, e este kit já teve uma
  (`qa_run.py --executar`, na v1.0.0)

**Ainda não verificado contra a realidade:**

| O quê | Risco | Como resolver |
|---|---|---|
| O `.docx` com dados **reais** de uma release | o exemplo cobre a mecânica, não o seu conteúdo | gere uma vez e leia antes de mandar ao PMO |
| Formato real do export do Qase | está no caminho da migração | `--dry-run` e confira o que ele entendeu |
| `rise_bug.py` contra o AP real | precisa de credencial | primeiro bug com `--dry-run` |
| **O processo rodando numa feature de verdade** | é o que decide se o time adota | leve uma feature pequena do intake ao parecer |

---

## 9. Como saber se está funcionando

Quatro perguntas, uma vez por mês:

1. **Consigo responder "por que este caso existe?"** para um caso sorteado, em
   três saltos? (`CT → RN → lacuna → resposta do PO`)
2. **O `@RN-PENDENTE` está caindo?** Se estiver parado, a migração empacou.
3. **Alguém já foi bloqueado por um portão esta semana?** Se nunca, ou o time é
   perfeito, ou os portões estão sendo contornados.
4. **A aprovação ainda leva ~1,5 min por cenário?** Se caiu para 20 segundos,
   virou carimbo.

```bash
python3 test/scripts/qa_dashboard.py --snapshot
```

O painel mostra cobertura de RN, conversão por feature, casos nunca executados,
lacunas por idade e a curva da migração. **Nunca agregue entre features** — a
média é onde a feature crítica com 20% se esconde.

---

## 10. Manutenção do kit

O kit é atualizado por caminho explícito, sem tocar no seu trabalho:

```bash
git fetch kit --tags
git checkout kit/v1.3.0 -- \
  .claude/skills .claude/hooks .claude/settings.json .claude/prompts \
  test/scripts docs templates .github CLAUDE.md .mcp.json
echo "1.3.0" > VERSION
git commit -am "chore: atualiza kit de v1.2.0 para v1.3.0"

python3 test/scripts/qa_lint.py --check-kit
python3 -m unittest discover -s test/scripts/tests
```

`test/cases/`, `test/runs/`, `test/sessoes/`, `test/metricas/`, `test/releases/` e
`bugs/` — o que é seu — não são tocados. Detalhe em
[`VERSIONAMENTO.md`](VERSIONAMENTO.md).

---

## 11. Resumo em uma frase

**O agente pergunta o que só o humano sabe, propõe o que consegue derivar, e para
quando os dois discordam.** Tudo que ele produz nasce `@ia-gerado @nao-aprovado`;
o que atravessa os cinco portões tem nome e data de quem assumiu.
