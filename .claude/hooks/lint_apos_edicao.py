#!/usr/bin/env python3
"""
PostToolUse — devolve o erro do qa-lint na hora, não no PR.

Sem isto, o agente escreve trinta cenários, o QA revisa trinta cenários, e só o
CI descobre que faltava @suite: em doze. Aqui a violação volta como contexto no
mesmo turno, enquanto ainda é barato corrigir.

Roda só quando a edição tocou test/cases/. Nunca bloqueia: lint é sinal, e o
agente decide o que fazer com ele.
"""

import json
import os
import re
import subprocess
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    caminho = str((payload.get("tool_input") or {}).get("file_path") or "")
    caminho = caminho.replace("\\", "/")
    raiz = (os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).replace("\\", "/")

    if "/test/cases/" not in caminho:
        sys.exit(0)

    resto = caminho.split("/test/cases/", 1)[1]
    feature = resto.split("/")[0] if "/" in resto else None
    if not feature:
        sys.exit(0)

    cmd = [sys.executable, os.path.join(raiz, "test", "scripts", "qa_lint.py"),
           "--feature", feature]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25, cwd=raiz)
    except Exception:
        sys.exit(0)

    saida = (r.stdout or "").strip()
    # linha de aviso e "  aviso  [feature] ...". Procurar so a palavra casava
    # tambem com o rodape "OK: nenhuma violacao, 0 aviso(s)", e o hook falava
    # em toda edicao de feature limpa -- ruido que treina a ignorar o sinal.
    tem_aviso = any(re.match(r"\s+aviso\s", l) for l in saida.splitlines())
    if r.returncode == 0 and not tem_aviso:
        sys.exit(0)     # verde e sem aviso: silêncio é a resposta certa

    rotulo = "REPROVOU" if r.returncode != 0 else "passou, com avisos"
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            f"qa-lint em '{feature}' {rotulo}. Corrija antes de seguir "
            f"— não apresente ao QA um cenário que o lint reprova.\n\n{saida}"
        ),
    }}))
    sys.exit(0)


if __name__ == "__main__":
    main()
