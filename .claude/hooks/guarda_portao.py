#!/usr/bin/env python3
"""
PreToolUse — transforma os portões humanos de convenção em mecanismo.

Todo documento deste kit repete "o agente nunca escreve @aprovado-por". Ate
aqui, nada impedia. Este hook impede.

Ele roda SO nas ferramentas de escrita do agente. Quando voce, pessoa, abre o
.feature no seu editor e aprova o cenario, nada dispara -- e essa assimetria e
exatamente o portao: a aprovacao e um ato nominal de quem responde por ela.

O que bloqueia:
  1. introduzir @aprovado-por: num .feature
  2. remover @ia-gerado de um cenario
  3. escrever executado_por: agente|claude|ia em test/runs/

A quarta regra do conjunto -- @automacao:feito sem spec que cite o CT -- fica no
qa_lint (regra 'automacao-fantasma'), porque exige varrer o repositorio inteiro,
e o hook PostToolUse devolve o erro no mesmo turno. Aqui so mora o que da para
decidir olhando a propria edicao.

COBERTURA DE FERRAMENTAS
    Edit, Write, MultiEdit e NotebookEdit passam pelo `file_path` + conteudo.
    Bash passa pelo texto do comando: `sed -i`, `cat > arquivo`, `tee` e
    `python3 -c "...write..."` gravam exatamente as mesmas tags sem tocar nas
    ferramentas de edicao. Sem esta parte, o portao 2 continuava sendo honra --
    e o lint NAO pega o caso do @aprovado-por, porque ele so cobra a tag quando
    ela falta, nunca valida quem a escreveu.

Saida: JSON com permissionDecision. Silencio (exit 0 sem corpo) = liberado.
"""

import json
import os
import re
import sys

# @aprovado-por: COM valor. `grep "@aprovado-por:"` (sem valor) continua livre --
# e assim que se conta aprovacao sem poder forjar uma.
RE_APROVADO = re.compile(r"@aprovado-por:([\w.\-@]+)")
RE_EXECUTADO_AGENTE = re.compile(
    r"""executado_por["'\s:=]+["']?(agente|claude|ia|IA)\b""")
# remocao de @ia-gerado por linha de comando: sed/perl com s///, /d ou -i
RE_SED_IA_GERADO = re.compile(r"(sed|perl)\b[^\n]*ia-gerado")


def nega(motivo):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": motivo,
    }}))
    sys.exit(0)


def textos(tool_input):
    """(texto_novo, texto_antigo) de Write, Edit ou MultiEdit."""
    novo = [str(tool_input.get("content") or ""),
            str(tool_input.get("new_string") or "")]
    antigo = [str(tool_input.get("old_string") or "")]
    for ed in tool_input.get("edits") or []:
        if isinstance(ed, dict):
            novo.append(str(ed.get("new_string") or ""))
            antigo.append(str(ed.get("old_string") or ""))
    return "\n".join(novo), "\n".join(antigo)


MSG_APROVADO = (
    "PORTÃO 2 — bloqueado.\n\n"
    "Esta {onde} introduz @aprovado-por:{quem}.\n\n"
    "A aprovação de cenário é um ato nominal de quem assume a "
    "responsabilidade por ele. O agente nunca escreve essa tag — nem "
    "com o nome do QA, nem a pedido dele nesta conversa.\n\n"
    "O que fazer: apresente os cenários ao QA e peça que ELE troque "
    "@nao-aprovado por @aprovado-por:<usuario> @data:<AAAA-MM-DD> no "
    "editor dele. Editar pelo editor da pessoa não dispara este hook — "
    "a assimetria é o portão."
)

MSG_RUNS = (
    "Bloqueado: executado_por \"{valor}\" em execução oficial.\n\n"
    "test/runs/ é o histórico de execução OFICIAL e aceita exatamente "
    "dois valores: 'ci' (suíte determinística, gravada pelo "
    "qa_ingest.py) e 'qa' (pessoa executando à mão).\n\n"
    "Um agente decide em runtime como interagir com o sistema: duas "
    "execuções do mesmo cenário podem seguir caminhos diferentes, e o "
    "resultado deixa de ser comparável entre builds.\n\n"
    "O que fazer: grave a sessão em test/sessoes/AAAA-MM-DD-<tema>.md "
    "como evidência de exploração."
)

MSG_IA_GERADO = (
    "Bloqueado: esta {onde} remove @ia-gerado.\n\n"
    "A tag nunca é removida. Ela é o que permite, depois de um escape "
    "de defeito, perguntar se a origem tem correlação com o caso ter "
    "sido gerado por IA. Ver docs/GLOSSARIO.md."
)


def checa_bash(comando):
    """O mesmo portão, pelo texto do comando.

    Não tenta interpretar shell -- tenta reconhecer a tag. Um comando que
    CITA `@aprovado-por:<usuario>` só tem dois motivos para existir: gravar a
    tag, ou procurar por uma aprovação específica. O primeiro é o que este
    hook existe para impedir; o segundo se faz com `grep aprovado-por`, sem
    o valor, que continua liberado de propósito.
    """
    quem = RE_APROVADO.findall(comando)
    if quem:
        nega(MSG_APROVADO.format(
            onde="linha de comando", quem=", ".join(sorted(set(quem)))) +
            "\n\nSe você só queria CONTAR aprovações, use `grep aprovado-por` "
            "sem o valor, ou `python3 test/scripts/qa_lint.py`.")

    m = RE_EXECUTADO_AGENTE.search(comando)
    if m and "test/runs" in comando.replace("\\", "/"):
        nega(MSG_RUNS.format(valor=m.group(1)))

    if RE_SED_IA_GERADO.search(comando):
        nega(MSG_IA_GERADO.format(onde="linha de comando"))


def checa_edicao(caminho, novo, antigo, rel):
    # --- portao 2: aprovacao e ato nominal de pessoa ----------------------- #
    if caminho.endswith(".feature"):
        novas = set(RE_APROVADO.findall(novo))
        antigas = set(RE_APROVADO.findall(antigo))
        if novas - antigas:
            nega(MSG_APROVADO.format(
                onde=f"edição em {rel}",
                quem=", ".join(sorted(novas - antigas))))
        if "@ia-gerado" in antigo and "@ia-gerado" not in novo:
            nega(MSG_IA_GERADO.format(onde=f"edição em {rel}"))

    # --- execucao oficial nao e do agente ---------------------------------- #
    if "/test/runs/" in f"/{rel}" or rel.startswith("test/runs/"):
        m = RE_EXECUTADO_AGENTE.search(novo)
        if m:
            nega(MSG_RUNS.format(valor=m.group(1)) +
                 f"\n\nArquivo: {rel}")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                      # hook nunca derruba a sessao

    ti = payload.get("tool_input") or {}
    ferramenta = str(payload.get("tool_name") or "")

    if ferramenta == "Bash":
        comando = str(ti.get("command") or "")
        if comando.strip():
            checa_bash(comando)
        sys.exit(0)

    caminho = str(ti.get("file_path") or "").replace("\\", "/")
    if not caminho:
        sys.exit(0)
    novo, antigo = textos(ti)
    if not novo.strip():
        sys.exit(0)

    raiz = (os.environ.get("CLAUDE_PROJECT_DIR") or "").replace("\\", "/")
    rel = caminho[len(raiz):].lstrip("/") if raiz and caminho.startswith(raiz) else caminho

    checa_edicao(caminho, novo, antigo, rel)
    sys.exit(0)


if __name__ == "__main__":
    main()
