#!/usr/bin/env python3
"""
Controle de rodadas de teste.

A ideia: cada cenário do Gherkin tem uma tag @CT-XXX. Cada rodada de execução
vira um arquivo em test/runs/rodada-N.json dizendo o que cada caso deu.
Com isso da para responder "rodada 1 falhou X, rodada 2 passou tudo" sem
depender de ferramenta externa -- e o historico fica versionado no git.

Uso:
    python3 tools/qa_run.py --init 1                 cria a rodada 1 em branco
    python3 tools/qa_run.py --status                 matriz de todas as rodadas
    python3 tools/qa_run.py --status --rodada 2      detalhe de uma rodada
    python3 tools/qa_run.py --check                  valida IDs e duplicatas

Status possiveis de um caso:
    passou | falhou | bloqueado | nao_executado | nao_aplicavel
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASES_DIR = os.path.join(ROOT, "test", "cases")
RUNS_DIR = os.path.join(ROOT, "test", "runs")

STATUS = ["passou", "falhou", "bloqueado", "nao_executado", "nao_aplicavel"]
SIGLA = {"passou": "OK", "falhou": "X", "bloqueado": "B",
         "nao_executado": "-", "nao_aplicavel": "n/a"}


def parse_features():
    """Le os .feature e devolve {CT-XXX: {titulo, arquivo, tecnicas}}."""
    casos = OrderedDict()
    for path in sorted(glob.glob(os.path.join(CASES_DIR, "**", "*.feature"), recursive=True)):
        pendente = None
        for linha in open(path, encoding="utf-8"):
            s = linha.strip()
            if s.startswith("#"):
                continue
            ids = re.findall(r"@(CT-[\w-]+)", s)
            if ids:
                tecnicas = [t for t in re.findall(r"@([\w:-]+)", s)
                            if not t.startswith("CT-")]
                pendente = (ids[0], tecnicas)
                continue
            m = re.match(r"^(Cen[áa]rio|Esquema do Cen[áa]rio|Scenario"
                         r"|Scenario Outline)\s*:\s*(.+)$", s)
            if m and pendente:
                cid, tecnicas = pendente
                # @auto = o Claude executa | @manual = o QA executa
                # sem marcacao explicita, assume manual (mais conservador:
                # ninguem passa por automatico sem alguem ter decidido isso)
                modo = "auto" if "auto" in tecnicas else "manual"
                casos[cid] = {
                    "titulo": m.group(2).strip(),
                    "arquivo": os.path.relpath(path, ROOT).replace("\\", "/"),
                    "tecnicas": tecnicas,
                    "modo": modo,
                }
                pendente = None
    return casos


def load_runs():
    """Le test/runs/*.json ordenado por numero da rodada."""
    runs = []
    for path in glob.glob(os.path.join(RUNS_DIR, "*.json")):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        data["_arquivo"] = os.path.basename(path)
        runs.append(data)
    return sorted(runs, key=lambda r: int(r.get("rodada", 0)))


def cmd_init(numero, args):
    casos = parse_features()
    if not casos:
        sys.exit(f"erro: nenhum caso encontrado em {CASES_DIR} "
                 f"(cenarios precisam da tag @CT-XXX)")
    destino = os.path.join(RUNS_DIR, f"rodada-{numero}.json")
    if os.path.exists(destino) and not args.force:
        sys.exit(f"erro: {destino} ja existe (use --force para sobrescrever)")

    anterior = {}
    runs = load_runs()
    if runs:
        anterior = runs[-1].get("resultados", {})

    resultados = OrderedDict()
    for cid, info in casos.items():
        item = {"status": "nao_executado", "titulo": info["titulo"],
                "modo": info["modo"], "executado_por": None}
        # caso que passou na rodada anterior ja entra sinalizado, para o QA
        # decidir se re-testa (regressao) ou marca nao_aplicavel
        ant = anterior.get(cid, {}).get("status")
        if ant:
            item["rodada_anterior"] = ant
        resultados[cid] = item

    os.makedirs(RUNS_DIR, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump({
            "rodada": int(numero),
            "data": args.data or "",
            "executor": args.executor or "",
            "feature": args.feature or "",
            "versao": args.versao or "",
            "ambiente": args.ambiente or "",
            "resultados": resultados,
        }, fh, indent=2, ensure_ascii=False)
    print(f"criado: {os.path.relpath(destino, ROOT)}  ({len(casos)} casos)")
    print("preencha o campo 'status' de cada caso: " + " | ".join(STATUS))


TECLAS = {"p": "passou", "f": "falhou", "b": "bloqueado",
          "n": "nao_executado", "x": "nao_aplicavel"}


def _pergunta(texto, default=""):
    try:
        v = input(texto).strip()
    except EOFError:
        return default
    return v or default


def cmd_executar(numero):
    """Percorre os casos perguntando o resultado. E assim que o QA registra."""
    caminho = os.path.join(RUNS_DIR, f"rodada-{numero}.json")
    if not os.path.exists(caminho):
        sys.exit(f"erro: rodada {numero} nao existe (crie com --init {numero})")
    with open(caminho, encoding="utf-8") as fh:
        run = json.load(fh)
    casos = parse_features()
    resultados = run.setdefault("resultados", {})

    print(f"\nRodada {run.get('rodada')} | {run.get('feature') or '?'} | "
          f"{run.get('versao') or '?'} | executor: {run.get('executor') or '?'}")
    print("teclas:  [p]assou  [f]alhou  [b]loqueado  [n]ao executado  "
          "[x] nao aplicavel  [s]air e salvar")
    print("Enter mantem o status atual.\n")

    for cid, info in casos.items():
        atual = resultados.setdefault(cid, {"status": "nao_executado",
                                            "titulo": info["titulo"]})
        st_atual = atual.get("status", "nao_executado")
        print("-" * 74)
        print(f"{cid}  {info['titulo']}")
        tec = [t for t in info["tecnicas"]
               if not t.startswith(("prioridade", "app", "sprint", "feature"))]
        if tec:
            print(f"   tecnicas: {', '.join(tec)}")
        print(f"   arquivo:  {info['arquivo']}")
        print(f"   atual:    {st_atual}")

        while True:
            t = _pergunta("   resultado > ").lower()
            if t == "":
                break
            if t == "s":
                _salvar(caminho, run)
                print(f"\nsalvo em {os.path.relpath(caminho, ROOT)} (parcial)")
                return
            if t in TECLAS:
                atual["status"] = TECLAS[t]
                atual["titulo"] = info["titulo"]
                break
            print("   opcao invalida. use p / f / b / n / x / s")

        # falha e bloqueio exigem contexto -- senao o relatorio do PMO fica vazio
        if atual["status"] in ("falhou", "bloqueado"):
            atual["obs"] = _pergunta(
                f"   o que aconteceu? [{atual.get('obs','')}] ", atual.get("obs", ""))
            if atual["status"] == "falhou":
                ev = _pergunta(f"   evidencia (nome do arquivo) "
                               f"[{atual.get('evidencia','')}] ", atual.get("evidencia", ""))
                if ev:
                    atual["evidencia"] = (ev if "/" in ev
                                          else f"test/image/{_hoje()}/{ev}")
                bug = _pergunta(f"   bug no AP (numero, vazio se ainda nao cadastrou) "
                                f"[{atual.get('bug','')}] ", str(atual.get("bug", "")))
                if bug.isdigit():
                    atual["bug"] = int(bug)
                elif not bug:
                    atual.pop("bug", None)
        else:
            for k in ("obs", "evidencia", "bug"):
                atual.pop(k, None)

    _salvar(caminho, run)
    print("\n" + "=" * 74)
    _resumo(run, prefixo=f"rodada {run.get('rodada')}: ")
    pend = [c for c, i in resultados.items()
            if i.get("status") == "falhou" and not i.get("bug")]
    if pend:
        print(f"\nATENCAO: {len(pend)} caso(s) com falha sem bug cadastrado no AP: "
              + ", ".join(pend))
        print("   cadastre com: python3 tools/rise_bug.py --file bugs/<arquivo>.json")
    print(f"\nsalvo em {os.path.relpath(caminho, ROOT)}")


def _hoje():
    import datetime
    return datetime.date.today().strftime("%d-%m-%Y")


def _salvar(caminho, run):
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(run, fh, indent=2, ensure_ascii=False)


def cmd_check():
    casos = parse_features()
    n_auto = sum(1 for i in casos.values() if i["modo"] == "auto")
    print(f"{len(casos)} caso(s) em {os.path.relpath(CASES_DIR, ROOT)}  "
          f"({n_auto} auto / {len(casos) - n_auto} manual):")
    for cid, info in casos.items():
        tec = ", ".join(t for t in info["tecnicas"]
                        if t not in ("auto", "manual")
                        and not t.startswith(("prioridade", "app", "sprint", "feature")))
        print(f"  {cid:<10} [{info['modo']:<6}] {info['titulo'][:46]:<48} {tec}")

    problemas = []
    for run in load_runs():
        for cid in run.get("resultados", {}):
            if cid not in casos:
                problemas.append(f"{run['_arquivo']}: {cid} nao existe nos .feature")
        for cid, info in run.get("resultados", {}).items():
            st = info.get("status")
            if st not in STATUS:
                problemas.append(f"{run['_arquivo']}: {cid} com status invalido '{st}'")
    if problemas:
        print("\nPROBLEMAS:")
        for p in problemas:
            print("  " + p)
        sys.exit(1)
    print("\nok: nenhum problema encontrado")


def cmd_status(rodada=None):
    casos = parse_features()
    runs = load_runs()
    if not runs:
        sys.exit(f"nenhuma rodada em {os.path.relpath(RUNS_DIR, ROOT)} "
                 f"(crie com --init 1)")

    if rodada:
        run = next((r for r in runs if int(r.get("rodada", 0)) == int(rodada)), None)
        if not run:
            sys.exit(f"rodada {rodada} nao encontrada")
        print(f"Rodada {run['rodada']}  |  {run.get('data','')}  |  "
              f"executor: {run.get('executor','?')}  |  {run.get('versao','')}")
        print("-" * 78)
        for cid, info in run.get("resultados", {}).items():
            st = info.get("status", "nao_executado")
            linha = f"  {SIGLA.get(st,'?'):>3}  {cid:<10} {info.get('titulo','')[:44]:<46}"
            extra = []
            if info.get("bug"):
                extra.append(f"bug #{info['bug']}")
            if info.get("evidencia"):
                extra.append(info["evidencia"])
            print(linha + ("  " + " | ".join(extra) if extra else ""))
            if info.get("obs"):
                print(f"        obs: {info['obs']}")
        _resumo(run)
        return

    # matriz de todas as rodadas
    header = ("CASO       MODO    " + "".join(f"R{r['rodada']:<5}" for r in runs)
              + " ÚLTIMO      POR")
    print(header)
    print("-" * len(header))
    for cid, info in casos.items():
        linha = f"{cid:<11}{info['modo']:<8}"
        ultimo, por = "-", ""
        for run in runs:
            res = run.get("resultados", {}).get(cid, {})
            st = res.get("status", "nao_executado")
            linha += f"{SIGLA.get(st,'?'):<6}"
            if st in ("passou", "falhou", "bloqueado"):
                ultimo = st
                por = res.get("executado_por") or ""
        print(linha + f" {ultimo:<11} {por}")
    print()
    # so o que a maquina rodou nunca passou por olho humano -- o PMO precisa saber
    so_maquina = [cid for cid in casos
                  if all((run.get("resultados", {}).get(cid, {}) or {}).get("executado_por")
                         in (None, "claude")
                         for run in runs)
                  and any((run.get("resultados", {}).get(cid, {}) or {}).get("executado_por")
                          == "claude" for run in runs)]
    if so_maquina:
        print(f"nota: {len(so_maquina)} caso(s) executado(s) somente por automacao, "
              f"sem verificacao humana: " + ", ".join(so_maquina))
        print()
    for run in runs:
        _resumo(run, prefixo=f"rodada {run['rodada']}: ")


def _resumo(run, prefixo=""):
    cont = {s: 0 for s in STATUS}
    for info in run.get("resultados", {}).values():
        cont[info.get("status", "nao_executado")] = \
            cont.get(info.get("status", "nao_executado"), 0) + 1
    total = sum(cont.values())
    executados = total - cont["nao_executado"] - cont["nao_aplicavel"]
    taxa = (cont["passou"] / executados * 100) if executados else 0
    print(f"{prefixo}{total} casos | {cont['passou']} passou | {cont['falhou']} falhou "
          f"| {cont['bloqueado']} bloqueado | {cont['nao_executado']} nao executado "
          f"| aprovacao {taxa:.0f}%")


def main():
    ap = argparse.ArgumentParser(description="Controle de rodadas de teste")
    ap.add_argument("--init", metavar="N", help="cria a rodada N em branco")
    ap.add_argument("--executar", metavar="N",
                    help="modo interativo: percorre os casos perguntando o resultado")
    ap.add_argument("--status", action="store_true", help="matriz de rodadas")
    ap.add_argument("--check", action="store_true", help="valida IDs e status")
    ap.add_argument("--rodada", metavar="N", help="detalha uma rodada")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--data", help="data da rodada (AAAA-MM-DD)")
    ap.add_argument("--executor", help="quem executou")
    ap.add_argument("--feature", help="nome da feature testada")
    ap.add_argument("--versao", help="versao/sprint")
    ap.add_argument("--ambiente", help="ambiente de teste")
    args = ap.parse_args()

    if args.init:
        cmd_init(args.init, args)
    elif args.check:
        cmd_check()
    elif args.status or args.rodada:
        cmd_status(args.rodada)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
