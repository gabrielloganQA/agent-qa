# Glossário — a fonte única dos termos

Todo outro documento e script **cita este arquivo** em vez de redefinir termo localmente.
Vocabulário disperso é o inimigo da rastreabilidade: se o mesmo conceito tem três
grafias, nada atravessa a corrente. Foi o que aconteceu com `@manual`, `@camada:manual`,
`modo: manual` e `@automacao:pendente` — quatro grafias, três donos, nenhum acordo.

Acrescentar termo é mudança MENOR do kit; **renomear é MAIOR** — invalida artefato
existente e exige seção de migração no `CHANGELOG.md`. Ver
[`VERSIONAMENTO.md`](VERSIONAMENTO.md).

Os nomes dos comandos (`/qa-intake`, `/design-casos-teste`) ficam como estão — são
identificadores de skill, não vocabulário de domínio.

---

## 1. Identificadores

| Prefixo | O que é | Mora em | Exemplo |
|---|---|---|---|
| `RF-XX` | documento de requisito da feature | `test/requisitos/` | `RF-12-transferencia.md` |
| `RN-XX` | regra de negócio, extraída do requisito | `REGRAS.md` | `RN-06` |
| `CT-XXX` | caso de teste — um cenário | `.feature` | `CT-017` |
| `L-XX` | lacuna: ambiguidade em aberto, esperando o PO | `LACUNAS.md` | `L-03` |

**ID nunca é reciclado.** Caso aposentado vira `@obsoleto:<data>` e o número não volta.
É isso que permite comparar cobertura entre releases sem mentir.

## 2. Artefatos

| Arquivo | O que guarda |
|---|---|
| `test/requisitos/RF-XX-<slug>.md` | a fonte crua, sem edição, com hash tirado pelo lint |
| `test/cases/<feature>/REGRAS.md` | as `RN-XX` numeradas, extraídas do requisito |
| `test/cases/<feature>/LACUNAS.md` | ambiguidades, com dono, data e impacto |
| `test/cases/<feature>/<feature>.feature` | os cenários, em Gherkin |
| `test/cases/<feature>/MATRIZ.md` | regra → técnica → cenário → camada → automação |
| `test/cases/<feature>/EXPLORATORIO.md` | charters e checklists — nunca automatizados |
| `test/cases/<feature>/DECISOES.md` | decisões tomadas, o porquê, e o que travaram |
| `test/cases/<feature>/MIGRACAO.md` | pendência da migração daquela feature — só existe em feature importada |
| `test/contexto.json` | as respostas do intake e as travas que elas impõem |
| `test/runs/*.json` | execução de CI (`executado_por: ci`) |
| `test/runs/manual/*.json` | execução do QA (`executado_por: qa`) |
| `test/sessoes/*.md` | sessões exploratórias — nunca execução oficial |
| `test/metricas/AAAA-MM-DD.json` | snapshot das métricas; é o que cria a série histórica |
| `test/dashboard.html` | painel derivado, gerado pelo `qa_dashboard.py`. Não versionado |
| `bugs/*.json` | rascunhos de defeito, antes de irem para o rastreador |

## 2.1 `executado_por` — dois valores, e só

| Valor | Quem | Onde |
|---|---|---|
| `ci` | a suíte determinística, gravada pelo `qa_ingest.py` | `test/runs/` |
| `qa` | pessoa executando à mão, pelo `qa_run.py --executar` | `test/runs/`, `test/runs/manual/` |
| `agente` | agente conduzido pelo QA | **só** `test/sessoes/` |

`agente`, `claude` ou `ia` em `test/runs/` fazem o `qa_lint` reprovar o build, e
um hook bloqueia a escrita antes disso. Um agente decide em runtime como
interagir com o sistema: duas execuções do mesmo cenário podem seguir caminhos
diferentes, e o resultado deixa de ser comparável entre builds.

## 3. Tags

Tudo que o lint lê. Cenário sem tag obrigatória reprova o PR.

### Obrigatórias em todo cenário

| Tag | Valores |
|---|---|
| `@CT-XXX` | o ID do caso |
| `@RN-XX` | a regra de negócio que ele prova |
| `@camada:` | `api` · `banco` · `contrato` · `e2e` · `performance` · `seguranca` · `manual` |
| `@suite:` | `smoke` · `regressao` · `nightly` · `release` |
| `@ia-gerado` | origem — **nunca removida** |
| técnica | ver a lista abaixo |

### Aprovação e estado

| Tag | O que significa |
|---|---|
| `@nao-aprovado` | fora da suíte oficial até o QA aprovar |
| `@aprovado-por:<usuario>` | quem assumiu a responsabilidade. **O agente nunca escreve esta tag.** |
| `@data:<AAAA-MM-DD>` | quando foi aprovado |
| `@premissa` | comportamento suposto porque o documento não define. Espera uma `L-XX`. Nunca vira código. |
| `@prioridade:` | `alta` · `media` · `baixa`, por risco |
| `@automacao:` | `pendente` · `feito:<PR>` · `nao-automatizar:<motivo>` |
| `@quarentena` | flaky, com prazo |
| `@obsoleto:<data>` | aposentado; o ID não volta a ser usado |
| `@sem-caso:RN-XX` | declarado na matriz, com motivo, quando uma regra intencionalmente não tem caso |
| `@observado:CT-XXX` | declarado na matriz: o valor esperado deste caso veio de **observação do sistema**, não do requisito. Obriga `@premissa` no cenário. |
| `@RN-PENDENTE` | caso importado de outra ferramenta, ainda **sem regra de negócio vinculada**. O lint avisa e conta; não reprova. Migração termina quando chega a zero. |
| `@migrado:qase-<id>` | origem externa do caso. **Nunca removida** — é o que responde, um ano depois, "este caso veio do Qase ou nasceu aqui?" |

### Técnicas

`@particionamento` · `@bva` · `@tabela-decisao` · `@transicao-estados` · `@caso-de-uso` ·
`@pairwise` · `@sintaxe` · `@dominio` · `@error-guessing` · `@exploratorio` ·
`@checklist` · `@aleatorio` · `@classification-tree`

## 4. Status de execução

| Status | O que significa |
|---|---|
| `passou` | o produto fez o que a regra manda |
| `falhou` | o produto fez outra coisa. **Sempre culpa do produto.** |
| `bloqueado` | não deu para testar — massa, ambiente, permissão. **Nunca culpa do produto.** |
| `nao_executado` | ninguém rodou. Nunca presuma `passou`. |
| `nao_aplicavel` | fora do escopo desta rodada, com motivo |

Misturar `falhou` com `bloqueado` faz o relatório mentir sobre a qualidade da entrega. É
a confusão mais cara de todo o vocabulário.

## 5. Modo de execução

| Modo | Quem executa |
|---|---|
| `auto` | o CI. Só quem tem `@automacao:feito:<PR>`. |
| `manual` | o QA, à mão. `@automacao:pendente` e `nao-automatizar` caem aqui. |

Sem tag de automação, o caso é `pendente` — ninguém sai da rodada manual por omissão.

## 6. Severidade — a escala do QA, usada no relatório do PMO

| | O que significa |
|---|---|
| `S1` | Crítico — impede o uso, corrompe dado ou expõe informação. **Interrompe o ciclo.** |
| `S2` | Alto — funcionalidade importante quebrada, com contorno. Teto de 2 em aberto para liberar. |
| `S3` | Médio — funciona com defeito perceptível; contorno simples. |
| `S4` | Baixo — cosmético ou de baixa frequência. |

**Severidade é o tamanho do estrago técnico; prioridade é a urgência da correção.** São
eixos independentes: um bug pode ser `S1` com prioridade baixa quando quebra feio num
fluxo que ninguém usa. Por isso são sempre duas perguntas, nunca uma.

## 7. ⚠️ Termos que NÃO são traduzidos nem alterados

O campo de prioridade do AP (Atlante Project) é **valor nativo de um sistema externo**.
O `rise_bug.py` mapeia essas strings para os ids do rastreador:

```
Baixa · Alta · Critica · Bloqueada
```

Não existe "Média" no AP. Defeito que o QA classificaria como médio é registrado como
`Alta`, com a observação escrita no corpo do ticket.

## 8. Palavras-chave do Gherkin

Os `.feature` são escritos em português (`# language: pt`):

`Funcionalidade` · `Contexto` · `Cenário` · `Esquema do Cenário` · `Exemplos` ·
`Dado` · `Quando` · `Então` · `E` · `Mas`

O corpo do cenário é declarativo: descreve comportamento, nunca clique. Escreva como se
não existisse interface. Quem precisa entender é o PO, não o runner.
