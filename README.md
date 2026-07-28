# Sistema de Qualidade — QA + IA

> Repositório único de casos, automação, execução e decisão de qualidade.
> Substitui o TMS por arquivos versionados, agentes com portões humanos e verificação
> automática.

| | |
|---|---|
| **Fonte da verdade** | Este repositório. O que não está aqui não existe. |
| **Ambiente de teste** | QA (único) |
| **Linguagem dos casos** | Gherkin, português |
| **Camada padrão** | `api` — E2E é exceção com teto de 10% |
| **Portões humanos** | 5, dois deles travados por hook |
| **Verificação** | `qa-lint` em todo PR, mais 90 testes do próprio kit |
| **Vindo do Qase?** | [`docs/MIGRACAO-QASE.md`](docs/MIGRACAO-QASE.md) |

---

## Começando

Este repositório é **template**. Cada QA clona e ele vira o projeto de QA daquele
produto.

```bash
git clone <url-do-kit> qa-wms
cd qa-wms

# o kit vira a fonte de ATUALIZAÇÃO, não o destino dos seus commits
git remote rename origin kit
git remote add origin <url-do-seu-repositorio>
git push -u origin main

claude
```

⚠️ **Abra o Claude dentro desta pasta.** Se abrir na pasta de cima, os comandos ficam
escopados e não aparecem no `/`.

Configure sua identidade antes do primeiro commit:

```bash
git config user.name "Seu Nome"
git config user.email "voce@atlanteti.com"
```

Depois, digite `/qa-intake` e cole a documentação da sua feature. O resto ele conduz.

**Antes disso, leia [`docs/PROCESSO.md`](docs/PROCESSO.md)** — o ciclo inteiro
de uma feature, do requisito ao parecer, com os comandos reais e os cinco
portões. Quinze minutos que valem mais que qualquer descrição do processo.

### Se você está migrando do Qase

```bash
python3 test/scripts/qa_import_qase.py --csv export-qase.csv --dry-run
```

O passo a passo, o que vem junto, o que **não** vem e por quê:
[`docs/MIGRACAO-QASE.md`](docs/MIGRACAO-QASE.md). Leia antes de importar — a
regra que evita a maior dor é migrar uma suíte por vez, não o projeto inteiro.

### Recebendo correção do kit

Você não perde seu trabalho: o `checkout` traz **só** as pastas da ferramenta.

```bash
git fetch kit --tags
git checkout kit/v1.3.0 -- \
  .claude/skills .claude/hooks .claude/settings.json .claude/prompts \
  test/scripts docs templates .github CLAUDE.md .mcp.json
echo "1.3.0" > VERSION
git commit -am "chore: atualiza kit de v1.2.0 para v1.3.0"
```

`test/cases/`, `test/runs/`, `test/sessoes/`, `test/metricas/`, `test/releases/` e
`bugs/` — o que é seu — não são tocados. Detalhe em
[`docs/VERSIONAMENTO.md`](docs/VERSIONAMENTO.md).

### Pré-requisitos

| | Necessário para | Quando |
|---|---|---|
| **Python 3** | os scripts em `test/scripts/` | sempre |
| **Node 18+** | os MCPs de navegador e mobile | só para testar UI ou app |

**Nenhum `pip install`.** Os scripts usam só biblioteca padrão.

### Configure o `.env`

```bash
cp .env.example .env
```

Preencha `RISE_BASE_URL`, `RISE_USER`, `RISE_PASSWORD` e `RISE_AUTH_TOKEN` — usados para
cadastrar defeito no AP. O `.env` está no `.gitignore`; **nunca commite credencial**.

### Os MCPs vêm junto

`.mcp.json` declara `playwright` (web) e `mobile` (app). Na primeira abertura o Claude
pede aprovação. Baixam sozinhos via `npx`. Se você só vai testar API, pode recusar.

> **Notion — avaliado e descartado por ora.** O MCP oficial da Notion
> (`https://mcp.notion.com/mcp`) funciona, mas **recusa conta de convidado**:
> quem não for *membro* do workspace recebe *"você é um convidado e não pode se
> conectar"*. Se o seu time for membro, vale adicionar.
>
> De todo modo, ler do Notion **não substitui versionar**: a regra tem de acabar
> gravada em `test/requisitos/RF-XX-*.md`, porque é do arquivo que o lint tira o
> `sha256` que detecta "requisito mudou sem revisão dos casos". Regra que vive só
> no Notion muda sem ninguém saber, e os casos seguem verdes provando o que não
> existe mais.

Para web, na primeira execução: `npx playwright install chromium`

> O `.mcp.json` fixa `--browser chromium` de propósito. Sem isso o MCP procura o
> **Chrome instalado no sistema** (`/opt/google/chrome/chrome`), que o comando
> acima não cria — e a primeira tentativa de abrir uma página falha com
> `Chromium distribution 'chrome' is not found`, sem dizer que o problema é o
> canal e não a instalação.

---

## Os 9 comandos

| Comando | Entrada | Saída | Portão |
|---|---|---|---|
| `/qa-intake` | documento, história, ata, contrato | `REGRAS.md` + `LACUNAS.md` | **PO responde** |
| `/design-casos-teste` | regras aprovadas | `.feature` + `MATRIZ.md` + `EXPLORATORIO.md` | **QA aprova cenário a cenário** |
| `/qa-roteamento` | cenários aprovados | `@camada:` e `@suite:` na matriz | QA confirma; lint valida o teto |
| `/qa-automacao` | cenário aprovado + camada | spec versionada + PR | **revisão de PR** |
| `/qa-execucao` | suíte + ambiente | `test/runs/*.json` | automático; falha bloqueia |
| `/qa-manual` | matriz + release | roteiro + folha de sessão | **QA executa e assina** |
| `/qa-defeito` | falha ou achado | defeito com RN violada, no AP | QA revisa antes de abrir |
| `/qa-relatorio` | runs + matriz + defeitos | parecer + `.docx` para o PMO | **QA assina** |
| `/qa-auditoria` | repositório inteiro | divergências e lacunas | pauta semanal |

---

## Os cinco portões

| # | Portão | Quem | O que trava | Mecanismo |
|---|---|---|---|---|
| 1 | Resposta às lacunas | PO | Cenário com `@premissa` não vira cobertura | `qa-lint` |
| 2 | Aprovação do cenário | QA | `@nao-aprovado` não entra na execução oficial | **hook + lint** |
| 3 | Revisão do PR de teste | QA / SDET | Código sem revisão não vai para a suíte | `CODEOWNERS` |
| 4 | Sessão exploratória | QA | Não automatizável por definição | **hook + lint** |
| 5 | Parecer de release | QA leader | Decisão de risco tem nome e data | assinatura |

Os portões 2 e 4 deixaram de ser convenção: `.claude/hooks/guarda_portao.py`
**bloqueia** o agente que tenta escrever `@aprovado-por:`, remover `@ia-gerado`
ou gravar `executado_por: agente` em `test/runs/` — pelas ferramentas de edição
**e pelo `Bash`**, porque `sed -i` e `cat >` gravam a mesma tag.

Quando você, pessoa, edita o `.feature` no seu editor para aprovar, nada
dispara. **A assimetria é o portão** — aprovação é ato nominal de quem responde
por ela.

**A IA nunca decide:** o que é risco aceitável, o que significa uma ambiguidade de
requisito, se a release pode sair, se um defeito é aceitável em produção, e se um
cenário deixou de fazer sentido.

---

## Estrutura

```
CLAUDE.md                as invariantes, carregadas em TODA conversa

test/
├── cases/<feature>/     .feature · REGRAS.md · LACUNAS.md · MATRIZ.md · EXPLORATORIO.md
├── requisitos/          origem versionada dos casos
├── api/ e2e/ performance/ support/     automação
├── sessoes/             exploratório e manual, uma folha por sessão
├── runs/                execução OFICIAL (ci) · runs/manual/ (qa)
├── metricas/            snapshot por data — a série que sustenta a conversa
├── releases/            parecer assinado por versão — TEMPLATE.md
├── image/DD-MM-AAAA/    evidências datadas
├── collection-postman/  collection + ambiente
└── scripts/             qa_lint · qa_run · qa_ingest · qa_dashboard ·
                         qa_report · qa_import_qase · rise_bug · tests/

.claude/
├── skills/              os 9 agentes (+ references/ carregadas sob demanda)
├── hooks/               os portões 2 e 4, em código
├── prompts/             prompts recorrentes, versionados
└── settings.json        registro dos hooks (versionado, do time)

bugs/                    rascunhos de defeito antes do cadastro no AP
docs/                    contratos do time e onboarding
templates/               modelo .docx do relatório (identidade Atlante)
.github/workflows/       o lint e os testes rodando em todo PR
```

---

## Documentação

| Documento | Leia quando |
|---|---|
| [`docs/PROCESSO.md`](docs/PROCESSO.md) | **primeiro** — o manual de operação: quem faz o quê, quando, com qual comando |
| [`docs/COMO-FUNCIONA.md`](docs/COMO-FUNCIONA.md) | o que o agente pergunta, quando e por quê |
| [`docs/MIGRACAO-QASE.md`](docs/MIGRACAO-QASE.md) | você tem acervo no Qase e vai trocar |
| [`docs/GLOSSARIO.md`](docs/GLOSSARIO.md) | fonte única de tags, status e IDs |
| [`docs/SIMULACAO-RF-12.md`](docs/SIMULACAO-RF-12.md) | ver o ciclo inteiro num exemplo real |
| [`docs/CONVENCOES-AUTOMACAO.md`](docs/CONVENCOES-AUTOMACAO.md) | contrato do time para automação |
| [`docs/PADRAO-BUG-WMS.md`](docs/PADRAO-BUG-WMS.md) | como o cadastro no AP funciona |
| [`CLAUDE.md`](CLAUDE.md) | as invariantes que valem em toda conversa |
| `.claude/skills/design-casos-teste/references/` | técnicas · gherkin · camadas · escrita · manuais · MCP |

---

## Comandos de manutenção

```bash
# consistência
python3 test/scripts/qa_lint.py              # roda em todo PR
python3 test/scripts/qa_lint.py --fix-hash   # após revisar casos de requisito alterado
python3 test/scripts/qa_lint.py --check-kit  # valida o próprio kit: links e ponteiros
python3 test/scripts/qa_lint.py --proximo-ct # aloca o próximo @CT livre (global)

# execução
python3 test/scripts/qa_ingest.py --junit r.xml --rodada 3 --criar   # CI → histórico
python3 test/scripts/qa_run.py --executar 3  # rodada manual, interativa
python3 test/scripts/qa_run.py --status      # matriz de rodadas

# saída
python3 test/scripts/qa_dashboard.py --snapshot       # painel HTML + métrica do dia
python3 test/scripts/qa_report.py                     # .docx no modelo Atlante
python3 test/scripts/rise_bug.py --file bugs/x.json --rodada 3   # AP + link na rodada

# migração e manutenção do kit
python3 test/scripts/qa_import_qase.py --csv export.csv --dry-run
python3 -m unittest discover -s test/scripts/tests
```

### O painel — o que o Qase dava como URL

`qa_dashboard.py` gera um HTML **estático e autocontido**: sem CDN, sem
servidor, sem build. Abre com duplo clique, inclusive offline, e tem tema claro
e escuro. Sete indicadores no topo — casos · aprovados por pessoa · cobertura de
RN · conversão em automação · nunca executados · lacunas abertas · defeitos S1 —
e, abaixo, o detalhe por feature, camada, lacuna, caso nunca executado, defeito
aberto e a série histórica.

A diferença para o Qase é de natureza: lá era um serviço lendo o banco deles;
aqui é **derivado**, recalculado de `test/cases`, `test/runs` e `bugs/` a cada
execução. Por isso `test/dashboard.html` está no `.gitignore` — versionar
arquivo derivado é convite a ficar desatualizado.

**Onde ele vive.** O CI publica em **GitHub Pages** a cada push na `main`
(`https://<org>.github.io/<repo>/`), e anexa o arquivo como artefato nos PRs.

> ⚠️ **Confirme o plano antes do primeiro deploy.** Publicar Pages a partir de
> repositório privado exige plano pago, e restringir o **site** aos membros da
> organização só existe no Enterprise Cloud. Nos demais planos o site é
> **público** — e o painel expõe nomes de feature, lacunas em aberto e contagem
> de defeitos. Para desligar sem mexer no resto, apague o job `paginas` de
> `.github/workflows/qa.yml`: o artefato continua entregando o mesmo arquivo.

**A série histórica se alimenta sozinha.** Um job diário roda `--snapshot` às 8h
e commita `test/metricas/`. Antes isso dependia de alguém lembrar na auditoria
semanal, e a pasta ficou vazia desde a v1.1.0 — métrica sem série responde
"como estamos", nunca "melhoramos?".

### A ponte com o CI — o que fecha o laço

```bash
npx playwright test --reporter=junit --output-file=resultados.xml
python3 test/scripts/qa_ingest.py --junit resultados.xml --rodada 3 --criar
```

O `qa_ingest` casa a tag `@CT-XXX` do título do teste, grava `executado_por: ci`
e avisa o que ficou de fora. **É o único caminho de execução automatizada
oficial** — sem ele, alguém digita resultado à mão, e "a regressão é código
determinístico" vira slogan.

Um CT citado em vários testes recebe a **pior notícia**: se qualquer um falhou, o
caso falhou. `skipped` vira `nao_executado`, nunca `passou`.

### O que o `qa-lint` reprova

ID órfão · **ID duplicado entre features** (é global, nunca reciclado) · regra sem
caso · tag obrigatória faltando · `@premissa` sem `@nao-aprovado` · `@aprovado-por`
sem `@data` · `@automacao:feito` apontando para spec inexistente · `nao-automatizar`
sem motivo · mais de `max(1, 10%)` em `@camada:e2e` · feature sem `REGRAS.md` ou
`LACUNAS.md` · `@obsoleto` sem data ou ainda aprovado · **execução oficial com
`executado_por: agente`** · **requisito alterado sem revisão dos casos** (via hash).

E **avisa** (sem reprovar) quando um caso executado por `ci` ainda está
`@automacao:pendente` — o painel e o relatório leem a conversão da *tag*, a
execução vem do *XML*, e sem essa ponte os dois números divergem em silêncio.

E **lê a spec**, não só o nome do arquivo dela. O `.feature` sempre foi
policiado; o código que implementa o cenário não era, e é nele que a asserção
mora. Um cenário podia dizer *"o total deve ser 90,00"* e a spec dizer
`expect(total).toBeTruthy()` — verde para sempre, sem nenhum PR reprovar.

| Reprova | Por quê |
|---|---|
| nenhuma asserção forte no bloco | o caso não prova nada e sai verde para sempre |
| dois status HTTP aceitos (`[200, 201]`) | a regra define **um**; aceitar dois é afrouxar até passar |
| `.skip` num caso **aprovado** | some do relatório como se estivesse coberto |
| `.only` | o CI roda esse teste e ignora todos os outros |

| Avisa | Por quê |
|---|---|
| asserção fraca ao lado de fortes | é a forma da falha mais comum: status forte, **valor** frouxo |
| espera fixa (`waitForTimeout`) | curta demais no CI lento, longa demais sempre |
| timeout acima de 30s | inflar timeout esconde lentidão que é defeito |

Não pega tudo: se o `90,00` veio da regra ou da tela, só a pessoa sabe — para
isso existem `@observado:` e `@premissa` na matriz. Pega a classe **mecânica**,
que é a que um agente produz sob pressão de fazer passar. Caso `@nao-aprovado`
pode estar legitimamente desligado: é o cenário travado por lacuna aberta.

Com `--check-kit`, valida também o próprio kit: comando citado que não é skill,
caminho para skill inexistente, script inexistente e **link markdown quebrado**.

E há 90 testes do kit em `test/scripts/tests/`: cada um quebra uma regra de
propósito e confirma que o lint fica vermelho. Um lint que passa verde em base
inconsistente é pior que nenhum, porque cria confiança onde não deve haver.

---

## Duas regras que se esquece

> **O agente explora, autora e diagnostica. A regressão é código determinístico.**

Sessão conduzida por agente vai para `test/sessoes/`, **nunca** para `test/runs/`.

> **A banda de revisão humana é o teto do sistema.**

~30 cenários por feature é revisável (≈45 min). 200 por semana não é — vira carimbo.
Gere por feature, na ordem de risco.

---

## Desvios em relação a `sistema-qa-ia.md`

| Documento diz | Aqui está | Por quê |
|---|---|---|
| `qa-lint.ts`, `qa-report.ts` | `qa_lint.py`, `qa_report.py` | Kit roda sem Node; Node só para os MCPs |
| 8 skills | 9 — `qa-manual` separada | Execução humana tem portão próprio |
| Lacuna aberta: 30 dias | **5 dias** | Alinhado ao README do sistema |

### Ainda sem decisão

1. **Numeração dos portões** diverge entre os três documentos-fonte. Aqui está a
   ordem da seção "Os cinco portões", acima.
2. **Teto da regressão:** 20 min (`camadas-e-automacao`) × 15 min (mapa HTML). Aqui, 15.
3. **`qa_report.py`** ainda não calcula quarentena nem deriva de p95, que estão no
   parecer de `test/releases/TEMPLATE.md`. Conversão e cobertura de RN passaram a
   ser calculadas na v1.1.0.
