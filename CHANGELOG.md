# Changelog do kit

Versões do **sistema de QA** (skills, scripts, convenções) — não do produto sob teste
nem das execuções. Ver os três eixos de versão no README.

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) · [SemVer](https://semver.org/lang/pt-BR/)

Quando incrementar:

| | Quando |
|---|---|
| **MAIOR** | muda convenção que invalida artefato existente (tag obrigatória nova, formato de arquivo) — exige migração |
| **MENOR** | skill nova, regra de lint nova que passa a reprovar, referência nova |
| **CORREÇÃO** | ajuste de texto, correção de bug em script, sem mudança de contrato |

---

## [1.3.0] — 2026-07-28

Estende a verificação até o **código do teste**. Até aqui os guarda-corpos
paravam no Gherkin. **Nada invalida artefato existente**, mas o lint passa a
reprovar spec que antes passava — leia "Adicionado" antes de subir a versão.

### Adicionado

- **`qa_lint.py` lê o conteúdo das specs.** O `.feature` era policiado por uma
  dúzia de regras; a spec — onde a asserção de fato mora — só era lida pelo
  **nome do arquivo**, para provar que `@automacao:feito` não era fantasma. Um
  cenário podia dizer *"o total deve ser 90,00"* e a spec dizer
  `expect(total).toBeTruthy()`: verde para sempre, e nenhum PR reprovava. Era a
  invariante 5 do `CLAUDE.md` existindo como texto e não como mecanismo — a
  única sem plano B, porque as outras cinco têm hook ou lint.

  | Reprova | Regra |
  |---|---|
  | bloco sem nenhuma asserção forte | `spec-sem-assercao-forte` |
  | dois status HTTP aceitos (`[200, 201]`) | `spec-status-ambiguo` |
  | `.skip` num caso **aprovado**, ou `.only` | `spec-desligada` |

  | Avisa | Regra |
  |---|---|
  | asserção fraca ao lado de fortes | `spec-assercao-fraca` |
  | espera fixa (`waitForTimeout`, `time.sleep`) | `spec-espera-cega` |
  | timeout acima de 30s | `spec-timeout-alto` |

  Só olha bloco que cita um `CT` conhecido: fixture e page object não afirmam
  provar caso nenhum. Caso `@nao-aprovado` pode estar desligado — é o cenário
  travado por lacuna aberta, e desligá-lo ali é coerente.

  Duas severidades porque os casos são diferentes. **Todas** as asserções fracas
  é erro: o caso não prova nada. **Alguma** fraca é aviso — pode ser guarda de
  passo intermediário, mas é também a forma da falha mais comum de verdade, o
  status forte (`toBe(200)`) e o **valor** frouxo. O lint não sabe qual asserção
  prova a RN, então aponta a linha e devolve a decisão a quem aprova.

  Não pega tudo: se o `90,00` veio da regra ou da tela, só a pessoa sabe — é
  para isso que existem `@observado:` e `@premissa` na matriz. Pega a classe
  **mecânica**, que é a que um agente produz sob pressão de fazer passar.
- **O painel passou a ter onde morar.** Ele existia desde a v1.1.0 e só era
  entregue como artefato do CI — quem não é do time precisava navegar até o run
  e baixar um zip. Um job publica em **GitHub Pages** a cada push na `main`, com
  o aviso de exposição escrito no próprio workflow: publicar Pages de
  repositório privado exige plano pago, e restringir o site à organização só
  existe no Enterprise Cloud. Apagar o job desliga a publicação sem tocar no
  resto; o artefato continua.
- **A série histórica se alimenta sozinha.** `--snapshot` existia e nada o
  chamava: o CI rodava o painel sem ele, e `test/metricas/` seguia vazio desde a
  v1.1.0 — quatro documentos mandavam rodar à mão na auditoria semanal. Um job
  diário grava e commita a métrica. É o mesmo defeito de `qa_run.py --executar`
  na v1.0.0: recurso existente, documentado e nunca despachado.
- **`qa_dashboard.py --dir`**, como o `qa_lint` já tinha. Sem isso, repositório
  recém-clonado exibia tudo zerado e não havia como mostrar o painel a alguém
  antes de ter casos próprios. Com `--dir examples/cases` ele abre com 12 casos,
  100% de cobertura e a lacuna aberta que trava o CT-011.
- **`examples/api/checkout-cupom.spec.ts`** — o exemplo do kit ia do requisito
  até o roteamento e parava. Quem fosse escrever a primeira spec não tinha o que
  imitar, e agora havia uma regra policiando specs sem nenhum exemplar. Mostra a
  conta do valor esperado no comentário e o `CT-011` desligado **porque** está
  `@nao-aprovado`. `CT-001..CT-003` e `CT-006` viraram `@automacao:feito:PR-118`.

### Corrigido

- **O portão 2 vazava no limite da execução.** O `PROCESSO.md` promete que
  "`@nao-aprovado` fica fora da suíte oficial" e atribui isso a "hook + lint".
  Nenhum dos dois cobria este ponto: `qa_run.py --init` montava a rodada com
  `parse_features()` inteiro, e um cenário `@premissa @nao-aprovado` —
  comportamento **suposto**, esperando o PO — podia ser marcado `passou`. O lint
  passava limpo, o painel contava o caso como coberto e o relatório do PMO
  anunciava **"100% de aprovação"** sobre isso. Suposição virando cobertura é
  precisamente o que este kit existe para impedir, e era a invariante 4 sem
  mecanismo no ponto onde ela mais importa.

  Duas travas agora: `--init` exclui os não aprovados e diz quais excluiu (mesma
  forma do `--manual` com `@automacao:feito`); e `qa_lint` reprova com
  `execucao-nao-aprovada` quando uma rodada traz `passou`, `falhou` ou
  `bloqueado` para cenário sem `@aprovado-por:` — o que pega também rodada
  escrita à mão ou vinda do `qa_ingest`. `nao_executado` continua válido: é o
  estado **correto** de cenário travado por lacuna.

  Encontrado invocando `/qa-execucao` numa feature real.
- **`qa-execucao` se anunciava, no próprio H1, com o nome de um comando que não
  existe** (`qa-testar`, com barra na frente). Quem lesse a skill digitaria e
  não aconteceria nada. O `--check-kit` não pegava porque só validava comando
  entre crases; agora valida também em título markdown — e a primeira coisa que
  a regra nova pegou foi esta própria entrada do changelog, escrita com a forma
  de comando.
- **`qa-roteamento` declarava como entrada "cenários com `@aprovado-por:`"**,
  contradizendo o `design-casos-teste`, que roteia no passo 2 — antes do próprio
  portão, no passo 6. E o lint exige `@camada:` em **todo** cenário, então a
  camada tem de existir antes da aprovação. A skill agora diz o que de fato faz:
  revisa e confirma o roteamento.
- **`rise_bug.py` decidia a severidade em silêncio.** A skill `qa-defeito`
  prometia que o script **recusa** severidade sem nível `S1..S4`; ele na verdade
  mapeia `"alta"` → `S2` por apelido, sem dizer nada. Mapear é útil na migração,
  mas decidir calado não: `S1` contra `S2` é a diferença entre interromper o
  ciclo e liberar a release, e o `CLAUDE.md` lista severidade entre o que a IA
  **nunca decide sozinha**. O apelido continua funcionando e agora aparece no
  preview — `severidade .: alta -> S2 INFERIDO do texto`. A skill passou a
  descrever o comportamento real.
- **`qa_ingest.py` não acusava cenário não aprovado.** Ele grava de qualquer
  forma, e deve mesmo — registra o que o runner fez, e mascarar seria pior. Mas
  agora avisa na hora, em vez de deixar a descoberta para o lint no PR.
- **`open()` sem `with` em `qa_report.py`, `qa_dashboard.py` e
  `qa_import_qase.py`.** A v1.2.0 corrigiu os do `qa_lint.py` e parou ali. Os
  outros só apareceram quando `test/cases/` deixou de estar vazio — até então o
  trecho nunca era exercitado pela suíte.
- **O MCP do Playwright não abria nenhuma página.** `.mcp.json` não fixava o
  navegador, então o MCP procurava o **Chrome do sistema**
  (`/opt/google/chrome/chrome`) — que o `npx playwright install chromium` do
  README não cria. A primeira tentativa de testar UI falhava com
  `Chromium distribution 'chrome' is not found`, sem indicar que o problema era
  o canal e não a instalação. Agora `--browser chromium`, que casa com o comando
  documentado. Encontrado tentando abrir uma aplicação real.

### Removido

- **`examples/`.** O kit é template: cada QA clona e ele vira o projeto de QA de
  um produto. Feature de exemplo dentro dele é ruído no que a pessoa recebe, e o
  valor que ela entregava foi realocado — o modelo de spec passou a viver dentro
  da `qa-automacao`, e o caminho de entrada do README passou a apontar para o
  `PROCESSO.md`. O passo de fumaça do CI que rodava o lint sobre o exemplo saiu
  junto; a suíte cobre o mesmo com árvore temporária.

### Mudado

- **`feature_de()` do painel** derivava o nome da feature pelo índice 2 do
  caminho, o que assumia exatamente `test/cases/<feature>/`. Com `--dir` numa
  raiz de outra profundidade, a feature não casava com o `REGRAS.md` e a
  **cobertura era reportada como 0% sem nenhum erro**. Agora é o primeiro nível
  abaixo da raiz de casos, seja ela qual for.
- **A raiz das camadas deixou de ser `test/` cravado**: elas são irmãs da raiz de
  casos (`test/cases` → `test/api`; `examples/cases` → `examples/api`). Sem isso
  o exemplo não podia trazer spec nenhuma, porque mora fora de `test/`.
- `specs_do_repo()` devolve `(caminho, conteúdo)` e não relê `*.spec.ts` duas
  vezes — ele casava em dois padrões do glob.
- 55 → **90 testes**. Os novos foram checados por mutação: desligada cada peça
  da regra, uma a uma, 9 das 10 derrubam a suíte. A décima é atalho de
  desempenho e está anotada como tal no código.

---

## [1.2.0] — 2026-07-27

Fecha os buracos entre os três planos de verificação do kit — hook, lint e
relatório. Cada invariante era checada em **um** deles e atravessava pelos
outros. **Nada invalida artefato existente**; o modelo `.docx` ganha uma linha.

### Corrigido

- **O portão 2 tinha rota lateral por `Bash`.** O hook `PreToolUse` casava só
  `Edit|Write|MultiEdit|NotebookEdit`: `sed -i`, `cat >`, `tee` e `python3 -c`
  gravavam `@aprovado-por:` sem disparar nada — e o lint **não** pega este caso,
  porque ele cobra a tag quando ela *falta*, nunca valida quem a escreveu. O
  matcher agora inclui `Bash` e o hook inspeciona o texto do comando. Contar
  aprovação (`grep aprovado-por`, sem valor) segue liberado de propósito.
- **O relatório do PMO podia dizer "0 defeitos em aberto" com caso reprovado.**
  `qa_report.py` contava defeito só a partir de `bugs/*.json`; uma rodada com
  falha e nenhum bug cadastrado saía limpa no primeiro número que o PMO lê. Vira
  critério de saída (`Falhas sem defeito registrado`, meta 0) e ressalva no
  sumário executivo.
- **Conversão e execução não se falavam.** A conversão (painel e relatório) vem
  da tag `@automacao:feito`; a execução vem do JUnit. Um caso que o CI roda toda
  noite mas que a matriz ainda chama de `pendente` fazia o painel exibir
  conversão menor que a real. `qa_ingest.py` avisa na hora e `qa_lint.py` passa a
  avisar em todo PR.
- **O parecer enxergava metade do ciclo quando havia execução manual.** Uma
  rodada tem dois donos e dois arquivos — `runs/rodada-N.json` (CI) e
  `runs/manual/<data>-rodada-N.json` (QA) — e `qa_report.py` lia `runs[-1]`, um
  só. Num ciclo em que o CI rodou 1 caso e o QA rodou 2, o relatório anunciava
  **"2/3 executados"** com os 3 executados. Agora a **rodada é a unidade**:
  `qa_run.consolida_rodada()` funde os arquivos do mesmo número e, quando o
  mesmo CT tem resultado nos dois, **a pessoa vence** — o QA reexecuta
  justamente quando desconfia do verde da suíte, e é ela quem assina.
  `ciclos` também contava dois para um ciclo só.
- **`--executar` desfazia o filtro do `--init --manual`.** A criação da rodada
  excluía os `@automacao:feito` de propósito (o CI é dono deles) e a execução
  refazia `parse_features()`, reinserindo exatamente esses — o QA acabava
  clicando caso a caso em cenário que a suíte já tinha rodado.
- `qa_lint.py --dir` documentava `examples/` como exemplo; a raiz correta é
  `examples/cases` — quem seguia o `--help` recebia dois erros falsos.
- Docstring do `guarda_portao.py` prometia quatro bloqueios e implementava três.
  O quarto (`@automacao:feito` sem spec) sempre foi do lint; agora está escrito.
- Arquivos abertos sem `with` no `qa_lint.py` (`ResourceWarning` na suíte).

### Mudado

- **`templates/Relatorio_de_Testes_Atlante.docx` ganhou uma linha** na tabela de
  critérios de saída. Os rótulos moram no modelo e os valores no código, na mesma
  ordem — um critério novo só no código sumia da tabela sem erro nenhum. O teste
  `TestCriteriosCasamComOModelo` torna essa deriva mecânica.
- **`/qa-automacao` deixou de exigir três leituras de partida.** O essencial já
  estava na própria skill; abrir os três documentos custava ~21 mil tokens antes
  da primeira linha de spec. Agora são consulta pontual, com o gatilho escrito ao
  lado de cada um — o piso da sessão caiu ~79%.
- 34 → **55 testes**, cobrindo cada correção acima.

---

## [1.1.0] — 2026-07-25

Fecha o laço com o CI, abre o caminho de saída do Qase e transforma dois portões
de convenção em mecanismo. **Nada invalida artefato existente** — quem está na
1.0.0 atualiza e segue.

### Adicionado

- **`qa_ingest.py`** — lê o JUnit XML de qualquer runner (Playwright, Cypress,
  Newman, pytest, Jest) e grava em `test/runs/` com `executado_por: ci`, casando
  a tag `@CT-XXX` do título do teste. Era a peça que faltava: sem ela alguém
  digitava resultado à mão, ou pedia para um agente preencher — o que o lint
  proíbe. Um CT em vários testes recebe a pior notícia; `skipped` vira
  `nao_executado`, nunca `passou`.
- **`qa_import_qase.py`** — importa o acervo do Qase (CSV ou JSON da API) para
  `.feature` + `MATRIZ.md` + `MIGRACAO.md`. Tudo nasce `@nao-aprovado`,
  `@RN-PENDENTE` e `@camada:manual`, porque o Qase não guarda regra de negócio
  nem decisão de camada.
- **`qa_dashboard.py`** — painel HTML estático e autocontido (sem CDN, sem
  servidor) para o PO e o PMO, mais `--snapshot`, que grava a métrica do dia em
  `test/metricas/`. Métrica sem série temporal não diz se melhorou.
- **`CLAUDE.md`** — as seis invariantes, carregadas em toda conversa. Antes, elas
  só entravam no contexto quando alguém digitava um comando `/qa-*`.
- **`.claude/hooks/guarda_portao.py`** — PreToolUse que **bloqueia** o agente que
  tenta escrever `@aprovado-por:`, remover `@ia-gerado` ou gravar
  `executado_por: agente` em `test/runs/`. Portões 2 e 4 deixam de ser convenção.
- **`.claude/hooks/lint_apos_edicao.py`** — PostToolUse que roda o lint na feature
  tocada e devolve o erro no mesmo turno, não no PR.
- **`examples/`** — feature completa (RF-07, cupom no checkout), do requisito ao
  roteamento, passando no lint. Serve de onboarding, de âncora de estilo para o
  agente e de teste de fumaça do kit.
- **`test/scripts/tests/`** — 34 testes. Cada um quebra uma regra de propósito e
  confirma o vermelho do lint. Um kit que prega "teste do teste" precisa ter os
  seus.
- **`.github/workflows/qa.yml`** — o `VERSIONAMENTO.md` mandava rodar o lint no CI
  e não entregava o arquivo. Agora entrega, com o painel como artefato.
- **`docs/MIGRACAO-QASE.md`** — o passo a passo, o que vem junto, o que não vem e
  por quê.
- Três prompts em `.claude/prompts/`, cada um com a seção "o que costuma dar
  errado".

### Corrigido

- `qa_run.py --executar` existia, era documentado e **nunca era despachado** no
  `main()` — o modo interativo inteiro de registro manual estava morto.
- `qa-execucao` instruía gravar `executado_por: "claude"` em `test/runs/`, que o
  próprio lint reprova. O vocabulário correto (`ci` / `qa`) agora é o único.
- `rise_bug.py` procurava o `.env` em `test/scripts/`, não na raiz onde o README
  manda criá-lo: dava "faltando no .env" com o arquivo preenchido.
- `.env.example` não trazia `RISE_USER` nem `RISE_PASSWORD`, exigidos pelo script.
- Quatro links para `docs/CAMADAS-E-AUTOMACAO.md` e `docs/TESTE-LIMPO.md`, que
  nunca existiram. O `--check-kit` agora valida link markdown — era exatamente o
  tipo de erro que ele existia para pegar.
- `qa-execucao` gravava sessão em `test/exploratorio/`; todo o resto do kit usa
  `test/sessoes/`.
- `docs/PADRAO-BUG-WMS.md` documentava uma CLI que o `rise_bug.py` não tem.
- `qa_report.py` calculava "casos críticos executados" e "cobertura de
  requisitos" com **o mesmo número** (taxa de execução geral). Agora críticos são
  os `@prioridade:alta` e cobertura são as RN com caso. Conversão passou a ser
  calculada.
- `rise_bug.py` aceitava severidade sem nível `S1..S4`, o que zerava a tabela de
  defeitos do relatório do PMO.
- O glob de `@automacao:feito` varria só `test/api` e `test/e2e`: spec em
  `performance`, `banco` ou `contrato` era acusada de automação fantasma.

### Mudado

- **`CT` agora é único globalmente**, não por pasta. A checagem antiga não pegava
  a colisão real: dois QAs em branches diferentes gerando `CT-001` na mesma
  semana. Use `qa_lint.py --proximo-ct` para alocar.
- `qa_lint.py --dir <caminho>` valida outra raiz de casos (usado por `examples/`).
- `rise_bug.py --rodada N` grava o número do bug no caso da rodada, fechando o
  elo `RN → CT → run → bug` que sempre se perdia no passo manual.
- `hash=PENDENTE` e requisito com placeholder viram **aviso**, não erro: a dívida
  da migração precisa ser commitável para poder ser paga aos poucos.

---

## [1.0.0] — 2026-07-22

Primeira versão utilizável.

### Adicionado
- 9 skills: `qa-intake` · `design-casos-teste` · `qa-roteamento` · `qa-automacao` ·
  `qa-execucao` · `qa-manual` · `qa-defeito` · `qa-relatorio` · `qa-auditoria`
- 6 referências com divulgação progressiva: técnicas, gherkin, camadas, escrita de
  testes, testes manuais, testes com MCP
- `qa_lint.py` — 14 regras de consistência, incluindo detecção de requisito alterado
  por hash e bloqueio de execução oficial feita por agente
- `qa_run.py` · `qa_report.py` (modelo Atlante, preservando logo, CNPJ e ISO) ·
  `rise_bug.py` (cadastro na coluna BUGs do AP)
- `.mcp.json` com playwright e mobile
- `test/releases/TEMPLATE.md` — parecer assinado
- Documentação: `COMO-FUNCIONA.md`, `SIMULACAO-RF-12.md`, `CONVENCOES-AUTOMACAO.md`,
  `PADRAO-BUG-WMS.md`

### Decisões registradas
- Scripts em Python, não TypeScript — o kit roda sem Node
- 9 skills em vez de 8: `qa-manual` separada, porque execução humana tem portão próprio
- Lacuna aberta: prazo de 5 dias

### Pendente
- Numeração dos portões diverge entre os documentos-fonte
- Teto da regressão: 15 ou 20 min
- `qa_report.py` não calcula conversão, quarentena nem deriva de p95
