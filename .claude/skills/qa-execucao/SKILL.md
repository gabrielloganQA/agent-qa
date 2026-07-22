---
name: qa-execucao
description: Abre a rodada e executa os testes — roda os casos @auto via navegador ou API, pergunta ao QA o resultado dos @manual, captura evidências e grava tudo. Também conduz sessão exploratória guiada.
---

# /qa-testar — execução

## 1. Abra a rodada

```bash
python3 test/scripts/qa_run.py --init N --data AAAA-MM-DD --executor "Nome" \
  --feature "..." --versao "..." --ambiente "..."
```

Se já existir rodada aberta, continue nela.

## 2. Execute os `@auto`

**Ferramentas:**

| MCP | Usa para |
|---|---|
| `playwright` | web — navegar, clicar, ler a tela, screenshot, **`browser_network_requests`** e **`browser_console_messages`** |
| `mobile` | app — tocar, digitar, gravar vídeo, **`mobile_list_crashes`** |

`browser_network_requests` é caixa-cinza de graça: a tela diz "sucesso" mas a
requisição voltou 500? Teste de UI puro não pega isso.

**Cuidado com contaminação de setup.** Se você montar estado escrevendo direto em
`localStorage`/`sessionStorage` em vez de clicar, a interface pode não
re-renderizar e você registra falha que não existe. Diante de falha inesperada,
**refaça pela interface antes de reportar**.

## 3. Pergunte os `@manual`

Liste os casos e pergunte como foi. **Aceite resposta em lote** — *"1, 2 e 4
passaram, 3 e 5 falharam, 7 bloqueado"* — e confirme o entendimento antes de gravar.

Para cada falha pergunte: o que aconteceu, tem evidência, já existe bug.
Para cada bloqueio: por que não deu para testar.

Se ninguém executou, é `nao_executado` — **nunca** `passou` presumido.

## 4. Grave

`test/runs/rodada-N.json`:

```json
"CT-005": {
  "status": "falhou",
  "titulo": "...",
  "modo": "auto",
  "executado_por": "claude",
  "bug": 3502,
  "evidencia": "test/image/21-07-2026/ct-005.png",
  "obs": "observado X, esperado Y"
}
```

Status: `passou` `falhou` `bloqueado` `nao_executado` `nao_aplicavel`
`executado_por`: `claude` ou `qa`

Evidência de toda falha em `test/image/DD-MM-AAAA/`.

> `falhou` ≠ `bloqueado`. Bloqueado não é culpa do produto — é impedimento.
> Misturar os dois faz o relatório mentir sobre a qualidade da entrega.

## 5. Modo exploratório

Quando o QA quiser explorar: **ele dirige, você é as mãos e o caderno.**

1. **Não navegue por conta própria.** Sugira o próximo passo, mas pergunte antes.
2. **Relate o que observou, não o que concluiu.** "A tela mostrou X e a requisição
   voltou Y" — o julgamento é dele.
3. **Capture evidência** a cada passo relevante.
4. **Registre a sessão** em `test/exploratorio/DD-MM-AAAA-<tema>.md`.
5. **No fim, proponha a colheita.** Toda descoberta vira: bug, caso `@CT-XXX` novo
   (regressão permanente), ou nada.

O passo 5 é o que faz o exploratório valer. Sem ele o achado morre na memória de
quem testou.

## 6. Feche

```bash
python3 test/scripts/qa_run.py --status
```

Avise se houver caso `falhou` sem bug cadastrado.

**Próximo:** `/qa-bug` para as falhas · `/qa-relatorio` ao fechar a feature
