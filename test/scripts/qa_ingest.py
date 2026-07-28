#!/usr/bin/env python3
"""
qa-ingest — a ponte entre a suite automatizada e o historico oficial.

Le o JUnit XML que qualquer runner emite (Playwright, Cypress, Newman, pytest,
Jest, k6) e grava o resultado em test/runs/, casando a tag @CT-XXX que aparece
no titulo do teste.

POR QUE ISSO EXISTE
    Sem este script, alguem precisa digitar o resultado de cada caso na mao --
    ou pedir para um agente preencher, que e exatamente o que o qa_lint proibe.
    O kit prega "a regressao e codigo deterministico" e ate aqui nao tinha como
    o codigo deterministico reportar. Este e o caminho.

COMO O CASAMENTO FUNCIONA
    O titulo do teste (ou do describe, que o runner concatena no classname)
    precisa citar o CT:

        test("@CT-007 recusa cupom abaixo do minimo", ...)
        describe("@CT-007 @CT-008 cupons", ...)

    Um teste pode citar varios CT; todos recebem o mesmo resultado. Um CT pode
    aparecer em varios testes; nesse caso vale a pior noticia -- se qualquer
    teste do CT falhou, o CT falhou. Verde so quando tudo passou.

Uso:
    python3 test/scripts/qa_ingest.py --junit resultados.xml --rodada 3
    python3 test/scripts/qa_ingest.py --junit "reports/*.xml" --rodada 3 --criar
    python3 test/scripts/qa_ingest.py --junit r.xml --rodada 3 --dry-run

Saida: 0 se ingeriu, 1 se houve caso do XML sem CT correspondente no .feature
(erro de rastreabilidade: a spec cita um CT que nao existe).
"""

import argparse
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_run import parse_features, RUNS_DIR, ROOT  # noqa: E402

CT_RE = re.compile(r"@?(CT-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)")

# pior noticia primeiro: e a ordem de precedencia quando um CT aparece em mais
# de um teste. 'falhou' vence 'passou' -- nunca o contrario.
PRECEDENCIA = ["falhou", "bloqueado", "nao_executado", "passou"]


def cts_do_texto(texto):
    """Todos os @CT-XXX citados num titulo/classname, sem repetir."""
    vistos, out = set(), []
    for m in CT_RE.finditer(texto or ""):
        cid = m.group(1)
        if cid not in vistos:
            vistos.add(cid)
            out.append(cid)
    return out


def le_junit(paths):
    """[(cts, status, nome, tempo, mensagem)] de um ou mais JUnit XML.

    Tolerante ao dialeto: cada runner escreve um pouco diferente (testsuites
    aninhado, classname vazio, skipped como atributo). O que todos respeitam e
    o elemento <testcase> com filhos <failure>/<error>/<skipped>.
    """
    out = []
    for path in paths:
        try:
            raiz = ET.parse(path).getroot()
        except ET.ParseError as e:
            sys.exit(f"erro: {path} nao e um XML valido ({e})")
        for tc in raiz.iter("testcase"):
            nome = " ".join(x for x in (tc.get("classname"), tc.get("name")) if x)
            cts = cts_do_texto(nome)
            msg = ""
            if tc.find("failure") is not None or tc.find("error") is not None:
                st = "falhou"
                no = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
                msg = (no.get("message") or (no.text or "")).strip()[:300]
            elif tc.find("skipped") is not None:
                # skip nao e verde e nao e vermelho: e caso que ninguem rodou.
                # O kit proibe green-skip justamente para isto nao virar 'passou'.
                st = "nao_executado"
                msg = (tc.find("skipped").get("message") or "").strip()[:300]
            else:
                st = "passou"
            try:
                tempo = float(tc.get("time") or 0)
            except ValueError:
                tempo = 0.0
            out.append((cts, st, nome, tempo, msg))
    return out


def consolida(testes):
    """{CT: {status, tempo, obs, testes}} aplicando a pior-noticia-vence."""
    por_ct = OrderedDict()
    for cts, st, nome, tempo, msg in testes:
        for cid in cts:
            atual = por_ct.setdefault(cid, {"status": "passou", "tempo": 0.0,
                                            "obs": "", "testes": 0})
            atual["testes"] += 1
            atual["tempo"] += tempo
            if PRECEDENCIA.index(st) < PRECEDENCIA.index(atual["status"]):
                atual["status"] = st
                atual["obs"] = msg
            elif st == atual["status"] and msg and not atual["obs"]:
                atual["obs"] = msg
    return por_ct


def caminho_rodada(numero):
    return os.path.join(RUNS_DIR, f"rodada-{numero}.json")


def main():
    ap = argparse.ArgumentParser(
        description="Ingere JUnit XML na rodada oficial (executado_por: ci)")
    ap.add_argument("--junit", nargs="+", required=True,
                    help="arquivo(s) ou glob(s) do JUnit XML")
    ap.add_argument("--rodada", required=True, metavar="N")
    ap.add_argument("--criar", action="store_true",
                    help="cria a rodada se ela ainda nao existir")
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra o que faria, sem gravar")
    ap.add_argument("--build", help="identificacao do build (vai para o run)")
    args = ap.parse_args()

    paths = [p for pat in args.junit for p in sorted(glob.glob(pat))]
    if not paths:
        sys.exit(f"erro: nenhum arquivo casou com {' '.join(args.junit)}")

    casos = parse_features()
    if not casos:
        sys.exit("erro: nenhum caso em test/cases/ (cenarios precisam de @CT-XXX)")

    testes = le_junit(paths)
    if not testes:
        sys.exit(f"erro: nenhum <testcase> em {', '.join(paths)}")
    por_ct = consolida(testes)

    sem_ct = [n for cts, _s, n, _t, _m in testes if not cts]
    fantasmas = [c for c in por_ct if c not in casos]

    caminho = caminho_rodada(args.rodada)
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as fh:
            run = json.load(fh)
    elif args.criar:
        run = {"rodada": int(args.rodada), "data": "", "executor": "ci",
               "feature": "", "versao": args.build or "", "ambiente": "QA",
               "resultados": {}}
    else:
        sys.exit(f"erro: {os.path.relpath(caminho, ROOT)} nao existe "
                 f"(use --criar, ou qa_run.py --init {args.rodada})")

    resultados = run.setdefault("resultados", {})
    if args.build:
        run["build"] = args.build

    aplicados = 0
    for cid, info in por_ct.items():
        if cid not in casos:
            continue
        item = resultados.setdefault(cid, {})
        item["status"] = info["status"]
        item["titulo"] = casos[cid]["titulo"]
        item["modo"] = "auto"
        # o unico lugar do kit que escreve 'ci'. Execucao humana e 'qa', e vem
        # pelo qa_run.py --executar; agente nao escreve em test/runs/ nunca.
        item["executado_por"] = "ci"
        item["duracao_s"] = round(info["tempo"], 2)
        if info["status"] == "falhou" and info["obs"]:
            item["obs"] = info["obs"]
        elif info["status"] != "falhou":
            item.pop("obs", None)
        aplicados += 1

    nao_vistos = [c for c, i in casos.items()
                  if c not in por_ct and i["modo"] == "auto"]

    # CT que o CI acabou de rodar mas que a matriz ainda chama de pendente.
    # A conversao do painel e do relatorio le a TAG (@automacao:feito); a
    # execucao vem do XML. Sem este aviso os dois numeros divergem em silencio:
    # o CI roda 12 casos e o painel segue exibindo "conversao 0%", porque
    # ninguem marcou a tag depois do merge da spec. O lint tambem passa a
    # cobrar isso em toda rodada -- ver qa_lint.checa_runs().
    nao_declarados = [c for c in por_ct
                      if c in casos and not casos[c]["automacao"].startswith("feito")]
    # PORTAO 2 pela via do CI. O ingest GRAVA de qualquer forma -- ele registra
    # o que o runner de fato fez, e mascarar isso seria pior. Quem barra e o
    # qa_lint, que reprova o build. Mas avisar aqui poupa o ciclo inteiro ate o
    # PR: a suite esta rodando cenario que ninguem aprovou.
    nao_aprovados = [c for c in por_ct
                     if c in casos and not casos[c].get("aprovado")]

    print(f"qa-ingest: {len(paths)} arquivo(s), {len(testes)} teste(s), "
          f"{len(por_ct)} CT distinto(s)")
    print(f"  aplicados na rodada {args.rodada}: {aplicados}")
    cont = {}
    for cid, info in por_ct.items():
        if cid in casos:
            cont[info["status"]] = cont.get(info["status"], 0) + 1
    if cont:
        print("  " + " | ".join(f"{k}: {v}" for k, v in sorted(cont.items())))

    if sem_ct:
        print(f"\n  aviso: {len(sem_ct)} teste(s) sem @CT-XXX no titulo — "
              f"nao entram no historico:")
        for n in sem_ct[:10]:
            print(f"           {n[:90]}")
        if len(sem_ct) > 10:
            print(f"           ... e mais {len(sem_ct) - 10}")
    if nao_vistos:
        print(f"\n  aviso: {len(nao_vistos)} caso(s) @automacao:feito que o XML "
              f"nao trouxe: {', '.join(nao_vistos[:12])}")
        print("           ou a spec nao rodou, ou o titulo perdeu a tag @CT.")
    if nao_declarados:
        print(f"\n  aviso: {len(nao_declarados)} caso(s) que o CI rodou mas a matriz "
              f"nao declara automatizado: {', '.join(nao_declarados[:12])}")
        print("           marque @automacao:feito:<PR> no .feature e na MATRIZ.md.")
        print("           enquanto nao marcar, o painel e o relatorio contam esses")
        print("           casos como NAO automatizados — conversao sai menor que a real.")
    if nao_aprovados:
        print(f"\n  ERRO: {len(nao_aprovados)} caso(s) sem @aprovado-por: na rodada: "
              f"{', '.join(nao_aprovados[:12])}")
        print("        cenario que nao passou pelo portao 2 nao entra em execucao")
        print("        oficial — o resultado dele vira cobertura no painel e taxa")
        print("        de aprovacao no relatorio do PMO. O qa_lint reprova o build.")
        print("        Aprove o cenario, ou tire a spec da suite ate a aprovacao.")
    if fantasmas:
        print(f"\n  ERRO: {len(fantasmas)} CT citado(s) na spec que nao existe "
              f"em test/cases/: {', '.join(fantasmas)}")
        print("        rastreabilidade quebrada — corrija a spec ou o .feature.")

    if args.dry_run:
        print("\n>> dry-run: nada gravado")
        return

    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(run, fh, indent=2, ensure_ascii=False)
    print(f"\ngravado: {os.path.relpath(caminho, ROOT)}")

    pendentes = [c for c, i in resultados.items()
                 if i.get("status") == "falhou" and not i.get("bug")]
    if pendentes:
        print(f"ATENCAO: {len(pendentes)} caso(s) com falha sem bug cadastrado: "
              + ", ".join(pendentes))
        print("   abra com /qa-defeito e feche o laco com rise_bug.py "
              f"--rodada {args.rodada}")

    if fantasmas:
        sys.exit(1)


if __name__ == "__main__":
    main()
