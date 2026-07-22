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
| **Portões humanos** | 5, inegociáveis |
| **Verificação** | `qa-lint` em todo PR |

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

### Recebendo correção do kit

Você não perde seu trabalho: o `checkout` traz **só** as pastas da ferramenta.

```bash
git fetch kit --tags
git checkout kit/v1.2.0 -- .claude/skills test/scripts docs templates .mcp.json
echo "1.2.0" > VERSION
git commit -am "chore: atualiza kit de v1.0.0 para v1.2.0"
```

`test/cases/`, `test/runs/`, `test/sessoes/` e `test/releases/` — o que é seu — não são
tocados. Detalhe em [`docs/VERSIONAMENTO.md`](docs/VERSIONAMENTO.md).

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

Para web, na primeira execução: `npx playwright install chromium`

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

| # | Portão | Quem | O que trava |
|---|---|---|---|
| 1 | Resposta às lacunas | PO | Cenário com `@premissa` não vira cobertura |
| 2 | Aprovação do cenário | QA | `@nao-aprovado` não entra na execução oficial |
| 3 | Revisão do PR de teste | QA / SDET | Código sem revisão não vai para a suíte |
| 4 | Sessão exploratória | QA | Não automatizável por definição |
| 5 | Parecer de release | QA leader | Decisão de risco tem nome e data |

**A IA nunca decide:** o que é risco aceitável, o que significa uma ambiguidade de
requisito, se a release pode sair, se um defeito é aceitável em produção, e se um
cenário deixou de fazer sentido.

---

## Estrutura

```
test/
├── cases/<feature>/     .feature · REGRAS.md · LACUNAS.md · MATRIZ.md · EXPLORATORIO.md
├── requisitos/          origem versionada dos casos
├── api/ e2e/ performance/ support/     automação
├── sessoes/             exploratório e manual, uma folha por sessão
├── runs/                execução OFICIAL (ci) · runs/manual/ (qa)
├── releases/            parecer assinado por versão — TEMPLATE.md
├── image/DD-MM-AAAA/    evidências datadas
├── collection-postman/  collection + ambiente
└── scripts/             qa_lint · qa_run · qa_report · rise_bug

.claude/
├── skills/              os 9 agentes (+ references/ carregadas sob demanda)
└── prompts/             prompts recorrentes, versionados

bugs/                    rascunhos de defeito antes do cadastro no AP
docs/                    contratos do time e onboarding
templates/               modelo .docx do relatório (identidade Atlante)
```

---

## Documentação

| Documento | Leia quando |
|---|---|
| [`docs/COMO-FUNCIONA.md`](docs/COMO-FUNCIONA.md) | **primeiro** — o que o agente pergunta, quando e por quê |
| [`docs/SIMULACAO-RF-12.md`](docs/SIMULACAO-RF-12.md) | ver o ciclo inteiro num exemplo real |
| [`docs/CONVENCOES-AUTOMACAO.md`](docs/CONVENCOES-AUTOMACAO.md) | contrato do time para automação |
| [`docs/PADRAO-BUG-WMS.md`](docs/PADRAO-BUG-WMS.md) | como o cadastro no AP funciona |
| `.claude/skills/design-casos-teste/references/` | técnicas · gherkin · camadas · escrita · manuais · MCP |

---

## Comandos de manutenção

```bash
python3 test/scripts/qa_lint.py              # consistência — roda em todo PR
python3 test/scripts/qa_lint.py --fix-hash   # após revisar casos de requisito alterado
python3 test/scripts/qa_run.py --status      # matriz de rodadas
python3 test/scripts/qa_report.py            # relatório no modelo Atlante
python3 test/scripts/rise_bug.py --file bugs/x.json   # cadastra no AP
```

### O que o `qa-lint` reprova

ID órfão · regra sem caso · tag obrigatória faltando · `@premissa` sem `@nao-aprovado` ·
`@aprovado-por` sem `@data` · `@automacao:feito` apontando para spec inexistente ·
`nao-automatizar` sem motivo · mais de `max(1, 10%)` em `@camada:e2e` · feature sem
`REGRAS.md` ou `LACUNAS.md` · `@obsoleto` sem data ou ainda aprovado ·
**execução oficial com `executado_por: agente`** · **requisito alterado sem revisão dos
casos** (via hash).

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
| Lacuna aberta: 30 dias | **5 dias** | Alinhado ao README do sistema §10 |

### Ainda sem decisão

1. **Numeração dos portões** diverge entre os três documentos-fonte. Aqui está a ordem
   do `README` §6.
2. **Teto da regressão:** 20 min (`camadas-e-automacao`) × 15 min (mapa HTML). Aqui, 15.
3. **`qa_report.py`** calcula os critérios do template Atlante e **não** calcula
   conversão, quarentena nem deriva de p95 — que estão no parecer de
   `test/releases/TEMPLATE.md`.
