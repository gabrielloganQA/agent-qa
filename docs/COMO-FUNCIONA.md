# Como o processo funciona na prática

Documento de interação. Responde: **o que o agente pergunta, quando pergunta, e o que
acontece com cada resposta.**

Os outros documentos dizem *o que* testar (`design-casos-teste`), *onde* provar
(`camadas-e-automacao`) e *como* escrever (`escrita-de-testes`). Este diz **como a
conversa acontece**.

---

## 1. Os três tipos de pergunta

Nem toda pergunta é igual. O sistema usa três, e a escolha entre elas não é estética —
é o que decide se o QA responde em 3 segundos ou abandona no meio.

| Tipo | Quando | Como |
|---|---|---|
| **Escolha clicável** | opção fechada, conjunto conhecido | `AskUserQuestion`, **uma por vez**, com o efeito de cada opção escrito |
| **Texto livre** | nome, justificativa, o que aconteceu | pergunta em prosa |
| **Aprovação em lote** | revisar N itens de uma vez | mostra tudo, pergunta "aprova? o que ajustar?" |

**Regra:** se as opções cabem numa lista, é clicável. Fazer o QA digitar `Homolog`
quando existem quatro ambientes possíveis é atrito sem ganho.

E toda opção clicável traz **o efeito da escolha** na descrição:

> *"Não tenho acesso ao banco → não vou sugerir nenhum caso de validação em banco.
> RN-05 e RN-10 serão testadas só pelo comportamento externo."*

O QA precisa saber o que está liberando ou travando **antes** de clicar.

---

## 2. Quem pergunta o quê

| Comando | Pergunta clicável | Pergunta em texto | Portão |
|---|---|---|---|
| `/qa-intake` | **8** — ambiente, banco, logs, contrato, arquitetura, segurança, cobertura, projeto AP | nome do executor | **PO responde as lacunas** |
| `/design-casos-teste` | — | aprova técnicas · aprova cenários | **QA aprova cenário a cenário** |
| `/qa-roteamento` | — | confirma a camada de cada grupo | QA confirma |
| `/qa-automacao` | **5** — framework E2E, framework API, performance, projeto novo/existente, onde os testes moram | aprova cada spec | **revisão de PR** |
| `/qa-execucao` | — | — | automático; falha bloqueia |
| `/qa-manual` | — | resultado de cada caso, em lote | **QA executa e assina** |
| `/qa-defeito` | **3** — severidade S1–S4, prioridade, projeto | confirmação final do ticket | QA revisa antes de abrir |
| `/qa-relatorio` | **1** — LIBERAR / com ressalva / NÃO LIBERAR | preenche riscos e o não coberto | **QA assina** |
| `/qa-auditoria` | — | — | pauta semanal |

Total: **17 perguntas clicáveis** em todo o ciclo, concentradas em três momentos —
abertura, escolha de ferramenta e classificação de defeito.

---

## 3. O ciclo, passo a passo

### Abertura — `/qa-intake`

1. **Peça a documentação.** Texto colado, arquivo ou link. Sem documento, o agente
   inventa — e a primeira coisa que ele diz é isso.
2. **Aponte as ambiguidades antes de qualquer pergunta.** Regra sem desfecho, fronteira
   mal fechada, conflito entre regras, critério sem número.
3. **Faça as 8 perguntas**, uma por vez, clicáveis.
4. **Grave** `test/contexto.json` com o bloco `_efeitos` — o que cada resposta travou.
5. **Extraia** `REGRAS.md` (RN numeradas) e `LACUNAS.md` (perguntas ao PO).

> **Portão 1.** O PO responde. Enquanto não responder, o cenário que depende da lacuna
> leva `@premissa` e fica fora da suíte oficial.
>
> A resposta pode **criar uma regra nova**. Quando isso acontece, ela entra em
> `REGRAS.md` com origem na **lacuna**, não no documento.

### Desenho — `/design-casos-teste`

1. **Proponha a técnica, regra a regra, com justificativa.** Espere a resposta.
2. **Escreva os cenários** em Gherkin declarativo, com todas as tags.
3. **Mostre e pergunte:** *"Aprova? Algum para ajustar, remover ou adicionar?"*

> **Portão 2.** Só grave depois do aval. O QA troca `@nao-aprovado` por
> `@aprovado-por:<usuario> @data:<AAAA-MM-DD>`. **O agente nunca coloca essa tag.**

Na simulação, o QA rejeitou 1 cenário duplicado, corrigiu 1 que assumia herança de
permissão (virou lacuna nova) e **acrescentou 1 de próprio punho** — isolamento entre
tenants, que o agente não tinha como saber. Isso é o portão funcionando, não falha do
agente.

### Roteamento — `/qa-roteamento`

Apresente o agrupamento com o **percentual de E2E resultante**, e confirme.

### Automação — `/qa-automacao`

1. **5 perguntas de framework**, antes da primeira linha.
2. **Um teste por vez:** escreve → roda → verde legítimo → QA aprova como revisor.
3. Ao submeter, mostre o código, **a saída real da execução**, qual `@CT-XX` automatiza,
   e as decisões tomadas.

> **Quando o sistema diverge da regra, o agente PARA.** Não ajusta a asserção, não
> afrouxa, não adiciona skip. Reporta e pergunta qual dos dois está errado.

> **Portão 3.** Revisão de PR com o checklist. Antes do merge, quebre a regra de
> propósito e confirme que os testes ficam vermelhos.

### Execução — `/qa-execucao` e `/qa-manual`

O CI roda a suíte determinística e escreve em `test/runs/`.
O QA executa o que é manual; o agente pergunta o resultado e grava.

> **Portão 4.** Sessão exploratória. Agente conduzido pelo QA vira folha em
> `test/sessoes/` — **nunca** run oficial.

### Defeito — `/qa-defeito`

1. **Sem RN violada, não abre.** Regra não documentada vira lacuna; preferência vira
   sugestão.
2. **3 perguntas clicáveis:** severidade (S1–S4), prioridade (campo do AP), projeto.
3. Mostra o ticket montado e pede a confirmação final.

### Fechamento — `/qa-relatorio`

1. Calcula os critérios de saída e **propõe** a recomendação.
2. **Pergunta clicável:** LIBERAR · com ressalva · NÃO LIBERAR, com os números que
   sustentam a proposta.
3. Escreve `test/releases/v<X.Y.Z>.md`; o `.docx` Atlante sai dele.

> **Portão 5.** O QA assina. O agente nunca assina.

---

## 4. O que o agente pergunta quando não sabe

Além das perguntas fixas, existem quatro situações em que ele **tem que** parar:

| Situação | O que faz |
|---|---|
| O documento não define o comportamento | Abre `@premissa` + entrada em `LACUNAS.md`. **Não supõe.** |
| O sistema diverge da regra | Para, reporta, pergunta qual está errado. **Não ajusta a asserção.** |
| Faria falhar um caso por contaminação de setup | Refaz pela interface antes de reportar |
| A escolha é de risco, severidade ou liberação | Pergunta. **Nunca decide.** |

---

## 5. O que o agente nunca pergunta

Simetricamente, existe coisa que **não** é para perguntar — perguntar aqui é empurrar
trabalho de volta:

- Qual técnica de teste usar (ele propõe com justificativa; o QA aprova ou corta)
- Como escrever o Gherkin (as convenções estão em `references/gherkin.md`)
- Em que camada provar (ele roteia pela tabela; o QA confirma)
- Se deve rodar o lint (roda sempre)
- Se pode gravar sem aprovação (não pode; não é pergunta)

---

## 6. O ritmo — a banda de revisão é o teto

| Medida | Referência | Fonte |
|---|---|---|
| Cenários por feature | ~30 | revisável por uma pessoa |
| Tempo de aprovação | 45 min para 28 cenários (~1,5 min cada) | simulação RF-12 |
| Cenários por semana | **não passe de ~60** | acima disso a aprovação vira carimbo |

**Gere por feature, na ordem de risco. Nunca em lote.** Nenhuma feature nova entra em
desenho enquanto houver cenário aprovado sem automação de risco alto.

Sinal de alerta: mais cenários aprovados por dia do que alguém consegue ler com atenção.

---

## 7. Quando o sistema trava — e por que isso é certo

| Trava | Quem destrava | O que fazer enquanto isso |
|---|---|---|
| Lacuna sem resposta há +5 dias | PO | Aprovar o resto da feature; `@premissa` só no que depende |
| Cenário sem aprovação | QA | Automatizar o que já está aprovado |
| PR de teste na fila | SDET / QA leader | Revisar por risco: alto primeiro |
| Ambiente instável | Dev / infra | **Registrar a indisponibilidade em horas** |
| Suíte vermelha sem defeito | QA | Quarentena imediata com issue |

> Se o PO não responder, **o sistema trava de propósito.** É a intenção: cobertura
> construída sobre suposição é pior que cobertura ausente, porque parece pronta.

---

## 8. Resumo em uma frase

**O agente pergunta o que só o humano sabe, propõe o que ele consegue derivar, e para
quando os dois discordam.**

Tudo que ele produz nasce `@ia-gerado @nao-aprovado`. O que atravessa os cinco portões
tem nome e data de quem assumiu a responsabilidade.
