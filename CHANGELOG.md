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
