---
name: qa-defeito
description: Monta o bug no modelo estrutural da Atlante a partir de um caso que falhou, confirma severidade e prioridade com o QA e cadastra na coluna BUGs do AP (Atlante Project).
---

# qa-defeito — registro de defeito

## 0. ⚠️ Defeito sem RN não abre

Todo defeito aponta a **regra de negócio violada**. Sem ela, não é defeito:

| Situação | O que fazer |
|---|---|
| A RN existe e foi violada | Abre o defeito, citando `RN-XX` e o `CT-XX` |
| A regra **não está documentada** | É **lacuna** → entra em `LACUNAS.md` para o PO responder. Não abre defeito. |
| É preferência, não regra | Vira **sugestão de melhoria**, não defeito |

E antes de abrir, confirme:

- **Reprodução confirmada.** Achado de sessão de agente precisa ser reproduzido antes —
  agente não é fonte de execução oficial.
- **Não é duplicata.** Duplicata morre aqui, não na fila do dev.
- **Se escapou para produção**, o defeito nasce com um **`CT` novo** na matriz, na camada
  certa. Escape duas vezes pela mesma regra é falha de desenho, não de execução.
- **Defeito S1 interrompe o ciclo.** Parecer de release com S1 aberto não existe.

## 1. Monte o rascunho

Preencha a partir do caso de teste, da execução e da conversa. Grave em
`bugs/ct-XXX-<slug>.json`:

```json
{
  "escopo": "Checkout | /api/pedidos",
  "resumo": "frase curta e específica do problema",
  "descricao": "...",
  "comportamento_atual": "o que o sistema faz hoje",
  "resultado_esperado": "o que deveria acontecer",
  "passos": ["numerados, reproduzíveis por outra pessoa"],
  "ambiente": { "aplicacao": "", "versao": "", "navegador": "", "url": "" },
  "anexos": ["ct-005.png"],
  "severidade": "S2 — ...",
  "prioridade": "Alta",
  "impacto": "consequência para o negócio",
  "caso_de_teste": "CT-005",
  "project_id": 9,
  "assigned_to": 12
}
```

Passos ruins são o motivo nº 1 de bug devolvido pelo dev. Escreva de forma que
alguém que nunca viu a feature consiga reproduzir.

## 2. ⚠️ Severidade e prioridade são do QA — nunca decida

⚠️ **Use AskUserQuestion, uma pergunta por chamada, com opções clicáveis.** São
escolhas fechadas — não faça o QA digitar.

**Pergunta 1 — Severidade** (tamanho do estrago técnico):

| Opção | Descrição a exibir |
|---|---|
| `S1 — Crítico` | Impede o uso, corrompe dado ou expõe informação. **Interrompe o ciclo**: parecer de release com S1 aberto não existe. |
| `S2 — Alto` | Funcionalidade importante quebrada, com contorno. Teto de 2 em aberto para liberar. |
| `S3 — Médio` | Funciona com defeito perceptível; contorno simples. |
| `S4 — Baixo` | Cosmético ou de baixa frequência. |

**Pergunta 2 — Prioridade** (urgência de correção, campo nativo do AP):

`Baixa` · `Alta` · `Critica` · `Bloqueada`

Na descrição de `Alta`, avise: *"o AP não tem 'Média'; se você classificaria como Média,
esta é a opção — a observação fica no corpo do ticket."*

**Pergunta 3 — Projeto no AP**, com a lista real:
`curl -s -H "authtoken: $RISE_AUTH_TOKEN" "$RISE_BASE_URL/api/projects"`

Um bug pode ser **S1 com prioridade Baixa** (quebra feio num fluxo que ninguém usa).
São eixos independentes — por isso são duas perguntas, nunca uma.

Depois das três, mostre o ticket montado e peça a confirmação final:

```
Título: Bug:[Checkout | /api/pedidos] resumo
Severidade: ? ← preciso que você defina
Prioridade: ? ← preciso que você defina
Projeto: 9 (WMS) — confirma?

[demais seções preenchidas]
```

**São coisas diferentes:**
- **Severidade** = tamanho do estrago técnico → escala **S1 (Crítico) · S2 (Alto) ·
  S3 (Médio) · S4 (Baixo)**, usada no relatório do PMO
- **Prioridade** = urgência de correção → campo nativo do AP

Um bug pode ser S1 com prioridade Baixa (quebra feio num fluxo que ninguém usa).

⚠️ **O AP só tem 4 prioridades: Baixa, Alta, Critica, Bloqueada. Não existe
"Média"** — se o QA disser Média, avise e registre como Alta, com a observação no
corpo do ticket.

⚠️ **Escreva a severidade começando pelo nível:** `"S2 — funcionalidade importante
quebrada, com contorno"`. Sem o nível, a tabela da seção 4 do relatório sai
zerada e o parecer subestima a gravidade.

O `rise_bug.py` **aceita** texto solto (`"alta"`) e infere o nível pelo apelido —
conveniência que veio da migração. Mas quando ele infere, **diz no preview**:
`severidade .: alta   -> S2 INFERIDO do texto`. Confira: `S1` contra `S2` é a
diferença entre interromper o ciclo e liberar a release, e essa é uma decisão
sua, não do script. Declare o nível e não haverá o que conferir.

## 3. Cadastre

```bash
python3 test/scripts/rise_bug.py --file bugs/ct-XXX-<slug>.json --rodada N
```

O script mostra o preview, pergunta o projeto (com lista real do AP) e pede
confirmação antes de gravar. Colaboradores são preenchidos com todos os membros
do projeto automaticamente.

`--rodada N` fecha o laço: grava o número retornado no campo `bug` do
`caso_de_teste` dentro de `test/runs/rodada-N.json`. **Use sempre** — sem ele o
defeito existe no AP, o caso está `falhou` na rodada, e nada liga os dois; o
relatório não consegue dizer qual defeito reprovou qual caso.

Se `contexto.json` tiver `cadastrar_bug_no_ap: false`, **não cadastre** — deixe o
rascunho em `bugs/` e avise.

## 4. Como o AP funciona (conhecimento apurado)

- Cadastro vai para a **coluna BUGs** = `status_id 5`, **global em todos os
  projetos** (verificado em 9, 22, 31, 13). Muda só o `project_id`.
- O plugin REST API desta instalação é **somente leitura** — `POST /api/tasks`
  retorna `Route not found`. A escrita usa os endpoints internos (`/tasks/save`),
  autenticando por sessão. Está tudo em `docs/PADRAO-BUG-WMS.md`.
- ⚠️ **Erro retorna HTTP 200.** Token inválido → `200 {"status":false}`. Nunca
  confie no status code; valide o corpo.
- Evidência: no JSON escreva só o nome do arquivo (`"anexos": ["ct-005.png"]`); o
  script completa `test/image/DD-MM-AAAA/` e avisa se o arquivo não existir.

**Próximo:** `/qa-relatorio` ao fechar a feature
