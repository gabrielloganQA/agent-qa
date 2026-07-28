#!/usr/bin/env python3
"""
qa-dashboard — o painel que o Qase dava e o git não dá sozinho.

Gera um HTML estático, autocontido (sem CDN, sem servidor, sem build) a partir
de test/cases, test/runs, test/metricas e bugs/. É o artefato que se publica no
CI e se manda para o PO e o PMO — gente que não vai abrir JSON no GitHub.

E grava o snapshot histórico: sem série temporal, "conversão 62%" não diz se
melhorou ou piorou. O qa-auditoria calcula tudo na hora e não guarda nada; aqui
cada execução com --snapshot deixa uma linha em test/metricas/.

Uso:
    python3 test/scripts/qa_dashboard.py
    python3 test/scripts/qa_dashboard.py --snapshot        # grava a métrica do dia
    python3 test/scripts/qa_dashboard.py --saida /tmp/x.html
    python3 test/scripts/qa_dashboard.py --dir piloto/cases     # outra raiz
"""

import argparse
import datetime
import glob
import html
import json
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_run  # noqa: E402
from qa_run import parse_features, load_runs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASES = os.path.join(ROOT, "test", "cases")
METRICAS = os.path.join(ROOT, "test", "metricas")

e = html.escape


def usa_raiz(caminho):
    """Aponta o painel para outra raiz de casos.

    O qa_lint ja tinha --dir e o painel nao: num repositorio recem-clonado ele
    mostrava tudo zerado, e quem fosse apresentar a ideia ao PO nao tinha o que
    mostrar. `parse_features` le de qa_run.CASES_DIR, entao os dois modulos
    precisam ser reapontados.
    """
    global CASES
    CASES = os.path.normpath(os.path.join(ROOT, caminho))
    qa_run.CASES_DIR = CASES
    return CASES


# --------------------------------------------------------------------------- #
# coleta
# --------------------------------------------------------------------------- #

def feature_de(caso):
    """Nome da pasta da feature: o primeiro nivel abaixo da raiz de casos.

    Antes era o indice 2 do caminho, o que assumia exatamente
    `test/cases/<feature>/`. Com --dir apontando para outra raiz -- ou com o
    .feature em subpasta -- o indice caia noutro lugar, a feature nao casava com
    o REGRAS.md, e a cobertura era reportada como 0% sem nenhum erro.
    """
    caminho = os.path.normpath(os.path.join(ROOT, caso["arquivo"]))
    rel = os.path.relpath(caminho, CASES).replace("\\", "/")
    return rel.split("/")[0] if rel and not rel.startswith("..") else "?"


def regras_por_feature():
    out = {}
    for p in sorted(glob.glob(os.path.join(CASES, "*", "REGRAS.md"))):
        nome = os.path.basename(os.path.dirname(p))
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        rns = set(re.findall(r"^\s*\|\s*\**(RN-\d+)\**\s*\|", txt, re.M))
        rns |= set(re.findall(r"^#+\s*\**(RN-\d+)", txt, re.M))
        out[nome] = rns
    return out


def lacunas_abertas(hoje):
    """[(feature, id, pergunta, dias)] das lacunas na seção Abertas."""
    out = []
    for p in sorted(glob.glob(os.path.join(CASES, "*", "LACUNAS.md"))):
        nome = os.path.basename(os.path.dirname(p))
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        # só a seção "Abertas" — o que já foi respondido não é dívida
        m = re.search(r"##\s*Abertas(.*?)(?=^##\s|\Z)", txt, re.S | re.M)
        bloco = m.group(1) if m else ""
        for linha in bloco.splitlines():
            mm = re.match(r"\s*\|\s*(L-\d+)\s*\|(.*)", linha)
            if not mm:
                continue
            cols = [c.strip() for c in mm.group(2).split("|")]
            pergunta = cols[0] if cols else ""
            data = next((re.search(r"\d{4}-\d{2}-\d{2}", c) for c in cols
                         if re.search(r"\d{4}-\d{2}-\d{2}", c)), None)
            dias = None
            if data:
                try:
                    d = datetime.date.fromisoformat(data.group(0))
                    dias = (hoje - d).days
                except ValueError:
                    pass
            out.append((nome, mm.group(1), pergunta, dias))
    return out


def bugs_abertos():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "bugs", "*.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                b = json.load(fh)
        except Exception:
            continue
        if b.get("status_bug", "aberto") != "aberto":
            continue
        v = str(b.get("severidade_nivel") or b.get("severidade") or "")
        m = re.search(r"\bS([1-4])\b", v, re.I)
        b["_sev"] = ("S" + m.group(1)) if m else "?"
        b["_arquivo"] = os.path.basename(p)
        out.append(b)
    return out


def coleta(hoje):
    casos, runs = parse_features(), load_runs()
    regras = regras_por_feature()
    feats = sorted({feature_de(i) for i in casos.values()} | set(regras))

    # último status conhecido de cada caso, em qualquer rodada
    ultimo, executados = {}, set()
    for run in runs:
        for cid, info in (run.get("resultados") or {}).items():
            st = info.get("status")
            if st in ("passou", "falhou", "bloqueado"):
                ultimo[cid] = (st, info.get("executado_por") or "?", run.get("rodada"))
                executados.add(cid)

    linhas = []
    for f in feats:
        meus = {c: i for c, i in casos.items() if feature_de(i) == f}
        rns_req = regras.get(f, set())
        rns_cob = {t for i in meus.values() for t in i["tecnicas"] if t.startswith("RN-")}
        elegiveis = [c for c, i in meus.items()
                     if not i.get("automacao", "").startswith("nao-automatizar")]
        feitos = [c for c in elegiveis if meus[c].get("automacao", "").startswith("feito")]
        pendentes_rn = [c for c, i in meus.items() if "RN-PENDENTE" in i["tecnicas"]]
        aprovados = [c for c, i in meus.items()
                     if any(t.startswith("aprovado-por:") for t in i["tecnicas"])]
        linhas.append({
            "feature": f,
            "casos": len(meus),
            "rn_total": len(rns_req),
            "rn_cobertas": len(rns_req & rns_cob),
            "rn_sem_caso": sorted(rns_req - rns_cob),
            "aprovados": len(aprovados),
            "conversao": (len(feitos) / len(elegiveis) * 100) if elegiveis else 0.0,
            "migracao_pendente": len(pendentes_rn),
            "nunca_executados": sorted(c for c in meus if c not in executados),
        })

    camadas = {}
    for i in casos.values():
        c = next((t.split(":", 1)[1] for t in i["tecnicas"]
                  if t.startswith("camada:")), "?")
        camadas[c] = camadas.get(c, 0) + 1

    return dict(casos=casos, runs=runs, linhas=linhas, camadas=camadas,
                ultimo=ultimo, executados=executados,
                lacunas=lacunas_abertas(hoje), bugs=bugs_abertos())


def resumo(d):
    """O bloco que vai para test/metricas/ — os números que viram série."""
    tot = sum(l["casos"] for l in d["linhas"])
    rn_t = sum(l["rn_total"] for l in d["linhas"])
    rn_c = sum(l["rn_cobertas"] for l in d["linhas"])
    eleg = [c for c, i in d["casos"].items()
            if not i.get("automacao", "").startswith("nao-automatizar")]
    feitos = [c for c in eleg if d["casos"][c].get("automacao", "").startswith("feito")]
    return {
        "casos": tot,
        "aprovados": sum(l["aprovados"] for l in d["linhas"]),
        "rn_declaradas": rn_t,
        "rn_cobertas": rn_c,
        "cobertura_pct": round(rn_c / rn_t * 100, 1) if rn_t else 0.0,
        "conversao_pct": round(len(feitos) / len(eleg) * 100, 1) if eleg else 0.0,
        "nunca_executados": sum(len(l["nunca_executados"]) for l in d["linhas"]),
        "migracao_pendente": sum(l["migracao_pendente"] for l in d["linhas"]),
        "lacunas_abertas": len(d["lacunas"]),
        "bugs_abertos": len(d["bugs"]),
        "bugs_s1": sum(1 for b in d["bugs"] if b["_sev"] == "S1"),
        "camadas": d["camadas"],
        "rodadas": len(d["runs"]),
    }


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #

CSS = """
:root{--bg:#fff;--fg:#16181d;--mut:#5f6672;--line:#e3e6ea;--card:#f7f8fa;
--ok:#0f7b4f;--warn:#9a6400;--bad:#b3261e;--accent:#2b5cd9}
@media(prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#e8eaed;--mut:#9aa2ae;
--line:#2a2e35;--card:#1c1f25;--ok:#4ec98a;--warn:#e0a93a;--bad:#f2776b;--accent:#7aa2f7}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem 4rem;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .25rem}
h2{font-size:1.05rem;margin:2.25rem 0 .6rem;padding-bottom:.3rem;
border-bottom:1px solid var(--line)}
.sub{color:var(--mut);font-size:.85rem;margin-bottom:1.5rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.7rem}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.85rem}
.tile .n{font-size:1.65rem;font-weight:600;letter-spacing:-.02em}
.tile .l{color:var(--mut);font-size:.78rem;margin-top:.15rem}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.87rem;min-width:520px}
th,td{text-align:left;padding:.45rem .6rem;border-bottom:1px solid var(--line);
vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:.78rem;text-transform:uppercase;
letter-spacing:.04em}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.bar{position:relative;height:6px;background:var(--line);border-radius:3px;
min-width:70px;margin-top:.3rem}
.bar>i{position:absolute;inset:0 auto 0 0;border-radius:3px;background:var(--accent)}
code{background:var(--card);padding:.1rem .3rem;border-radius:4px;font-size:.85em}
.empty{color:var(--mut);font-style:italic}
footer{margin-top:3rem;color:var(--mut);font-size:.8rem;border-top:1px solid var(--line);
padding-top:1rem}
"""


def barra(pct):
    return f'<div class="bar"><i style="width:{max(0, min(100, pct)):.0f}%"></i></div>'


def classe(valor, bom, ruim):
    if valor >= bom:
        return "ok"
    return "bad" if valor < ruim else "warn"


def render(d, r, historico, hoje):
    P = []
    P.append(f"<h1>Qualidade — visão do repositório</h1>")
    P.append(f'<div class="sub">Gerado em {hoje.strftime("%d/%m/%Y")} · '
             f'{r["rodadas"]} rodada(s) registrada(s) · '
             f'fonte: <code>test/cases</code>, <code>test/runs</code>, <code>bugs/</code></div>')

    # ---- tiles ----
    cob_c = classe(r["cobertura_pct"], 90, 70)
    conv_c = classe(r["conversao_pct"], 80, 50)
    P.append('<div class="tiles">')
    for n, l, c in [
        (r["casos"], "casos de teste", ""),
        (f'{r["aprovados"]}', "aprovados por pessoa",
         "ok" if r["aprovados"] == r["casos"] else "warn"),
        (f'{r["cobertura_pct"]:.0f}%', f'cobertura de RN ({r["rn_cobertas"]}/{r["rn_declaradas"]})', cob_c),
        (f'{r["conversao_pct"]:.0f}%', "conversão em automação", conv_c),
        (r["nunca_executados"], "nunca executados",
         "ok" if r["nunca_executados"] == 0 else "bad"),
        (r["lacunas_abertas"], "lacunas abertas",
         "ok" if r["lacunas_abertas"] == 0 else "warn"),
        (r["bugs_s1"], "defeitos S1 abertos", "ok" if r["bugs_s1"] == 0 else "bad"),
    ]:
        P.append(f'<div class="tile"><div class="n {c}">{e(str(n))}</div>'
                 f'<div class="l">{e(l)}</div></div>')
    P.append("</div>")

    # ---- migração ----
    if r["migracao_pendente"]:
        P.append("<h2>Migração do Qase — em andamento</h2>")
        P.append(f'<p><strong class="warn">{r["migracao_pendente"]} caso(s)</strong> '
                 f'ainda com <code>@RN-PENDENTE</code>: importados do Qase e sem '
                 f'regra de negócio vinculada. A migração termina quando este '
                 f'número chegar a zero — não quando os arquivos existirem.</p>')
        P.append('<div class="scroll"><table><tr><th>Feature</th>'
                 '<th class="num">Aguardando regra</th><th class="num">Total</th>'
                 '<th>Progresso</th></tr>')
        for l in d["linhas"]:
            if not l["migracao_pendente"]:
                continue
            feito = 100 * (1 - l["migracao_pendente"] / l["casos"]) if l["casos"] else 0
            P.append(f'<tr><td><code>{e(l["feature"])}</code></td>'
                     f'<td class="num">{l["migracao_pendente"]}</td>'
                     f'<td class="num">{l["casos"]}</td>'
                     f'<td>{barra(feito)}</td></tr>')
        P.append("</table></div>")

    # ---- por feature ----
    P.append("<h2>Por feature</h2>")
    P.append('<p class="sub">Nunca agregue entre features: a média é onde a '
             'feature crítica com 20% se esconde.</p>')
    P.append('<div class="scroll"><table><tr><th>Feature</th><th class="num">Casos</th>'
             '<th class="num">Aprovados</th><th>Cobertura de RN</th>'
             '<th>Conversão</th><th>RN sem caso</th></tr>')
    if not d["linhas"]:
        P.append('<tr><td colspan="6" class="empty">nenhuma feature em '
                 'test/cases/ ainda</td></tr>')
    for l in d["linhas"]:
        cob = (l["rn_cobertas"] / l["rn_total"] * 100) if l["rn_total"] else 0
        sem = ", ".join(l["rn_sem_caso"]) or "—"
        P.append(
            f'<tr><td><code>{e(l["feature"])}</code></td>'
            f'<td class="num">{l["casos"]}</td>'
            f'<td class="num">{l["aprovados"]}</td>'
            f'<td>{l["rn_cobertas"]}/{l["rn_total"]}{barra(cob)}</td>'
            f'<td>{l["conversao"]:.0f}%{barra(l["conversao"])}</td>'
            f'<td class="{"bad" if l["rn_sem_caso"] else ""}">{e(sem)}</td></tr>')
    P.append("</table></div>")

    # ---- camadas ----
    total_c = sum(d["camadas"].values()) or 1
    e2e_pct = d["camadas"].get("e2e", 0) / total_c * 100
    P.append("<h2>Distribuição por camada</h2>")
    P.append(f'<p class="sub">Alvo: api+banco+contrato ~90%, e2e ≤10%. '
             f'Hoje e2e está em <strong class="{"ok" if e2e_pct <= 10 else "bad"}">'
             f'{e2e_pct:.1f}%</strong> — migração silenciosa para o E2E é o padrão '
             f'de deriva mais comum.</p>')
    P.append('<div class="scroll"><table><tr><th>Camada</th><th class="num">Casos</th>'
             '<th>Fatia</th></tr>')
    for c, n in sorted(d["camadas"].items(), key=lambda x: -x[1]):
        P.append(f'<tr><td><code>{e(c)}</code></td><td class="num">{n}</td>'
                 f'<td>{n / total_c * 100:.0f}%{barra(n / total_c * 100)}</td></tr>')
    P.append("</table></div>")

    # ---- lacunas ----
    P.append("<h2>Lacunas abertas</h2>")
    if not d["lacunas"]:
        P.append('<p class="empty">Nenhuma lacuna aberta.</p>')
    else:
        P.append('<p class="sub">Lacuna aberta há mais de 5 dias significa que '
                 'ninguém está respondendo — e todo cenário <code>@premissa</code> '
                 'que depende dela continua fora da suíte oficial.</p>')
        P.append('<div class="scroll"><table><tr><th>Feature</th><th>Lacuna</th>'
                 '<th>Pergunta</th><th class="num">Dias</th></tr>')
        for f, lid, perg, dias in sorted(d["lacunas"],
                                         key=lambda x: -(x[3] or 0)):
            cls = "bad" if (dias or 0) > 5 else ""
            P.append(f'<tr><td><code>{e(f)}</code></td><td>{e(lid)}</td>'
                     f'<td>{e(perg[:90])}</td>'
                     f'<td class="num {cls}">{dias if dias is not None else "—"}</td></tr>')
        P.append("</table></div>")

    # ---- casos nunca executados ----
    nunca = [(l["feature"], c) for l in d["linhas"] for c in l["nunca_executados"]]
    P.append("<h2>Casos nunca executados</h2>")
    if not nunca:
        P.append('<p class="empty">Nenhum. Todo caso escrito já rodou ao menos uma vez.</p>')
    else:
        P.append(f'<p class="sub">Caso escrito e nunca rodado é documentação, '
                 f'não teste. {len(nunca)} no total.</p><p>'
                 + " ".join(f"<code>{e(c)}</code>" for _f, c in nunca[:60]) + "</p>")

    # ---- defeitos ----
    P.append("<h2>Defeitos em aberto</h2>")
    if not d["bugs"]:
        P.append('<p class="empty">Nenhum rascunho de defeito aberto em bugs/.</p>')
    else:
        P.append('<div class="scroll"><table><tr><th>Sev.</th><th>Caso</th>'
                 '<th>Resumo</th><th>Prioridade</th></tr>')
        for b in sorted(d["bugs"], key=lambda x: x["_sev"]):
            cls = "bad" if b["_sev"] in ("S1", "?") else ""
            P.append(f'<tr><td class="{cls}">{e(b["_sev"])}</td>'
                     f'<td><code>{e(str(b.get("caso_de_teste") or "—"))}</code></td>'
                     f'<td>{e(str(b.get("resumo") or b["_arquivo"])[:80])}</td>'
                     f'<td>{e(str(b.get("prioridade") or "—"))}</td></tr>')
        P.append("</table></div>")

    # ---- histórico ----
    if len(historico) > 1:
        P.append("<h2>Série histórica</h2>")
        P.append('<p class="sub">Métrica sem série não é métrica: sem isto não dá '
                 'para dizer se melhorou.</p>')
        P.append('<div class="scroll"><table><tr><th>Data</th><th class="num">Casos</th>'
                 '<th class="num">Cobertura</th><th class="num">Conversão</th>'
                 '<th class="num">Nunca exec.</th><th class="num">Migração</th>'
                 '<th class="num">S1</th></tr>')
        for snap in historico[-12:]:
            P.append(f'<tr><td>{e(snap.get("data", "?"))}</td>'
                     f'<td class="num">{snap.get("casos", "—")}</td>'
                     f'<td class="num">{snap.get("cobertura_pct", "—")}%</td>'
                     f'<td class="num">{snap.get("conversao_pct", "—")}%</td>'
                     f'<td class="num">{snap.get("nunca_executados", "—")}</td>'
                     f'<td class="num">{snap.get("migracao_pendente", "—")}</td>'
                     f'<td class="num">{snap.get("bugs_s1", "—")}</td></tr>')
        P.append("</table></div>")

    P.append('<footer>Gerado por <code>test/scripts/qa_dashboard.py</code>. '
             'Este painel é derivado — a fonte da verdade são os arquivos '
             'versionados. Um painel que só mostra o verde recria o pior defeito '
             'do TMS antigo: um catálogo em que ninguém confia.</footer>')

    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>QA — {hoje.strftime("%d/%m/%Y")}</title>'
            f"<style>{CSS}</style></head><body><div class=\"wrap\">"
            + "".join(P) + "</div></body></html>")


def main():
    ap = argparse.ArgumentParser(description="Painel HTML estático do estado de QA")
    ap.add_argument("--saida", help="caminho do HTML (padrão: test/dashboard.html)")
    ap.add_argument("--snapshot", action="store_true",
                    help="grava as métricas do dia em test/metricas/")
    ap.add_argument("--json", action="store_true",
                    help="imprime o resumo em JSON e sai (para o CI)")
    # mesma raiz que o qa_lint --dir: a pasta que CONTEM as features
    ap.add_argument("--dir", metavar="CAMINHO",
                    help="outra raiz de casos (ex.: piloto/cases)")
    args = ap.parse_args()

    if args.dir:
        raiz = usa_raiz(args.dir)
        if not os.path.isdir(raiz):
            sys.exit(f"erro: {args.dir} não existe")

    hoje = datetime.date.today()
    d = coleta(hoje)
    r = resumo(d)

    if args.json:
        print(json.dumps(dict(r, data=hoje.isoformat()), indent=2, ensure_ascii=False))
        return

    historico = []
    for p in sorted(glob.glob(os.path.join(METRICAS, "*.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                historico.append(json.load(fh))
        except Exception:
            pass

    if args.snapshot:
        os.makedirs(METRICAS, exist_ok=True)
        alvo = os.path.join(METRICAS, f"{hoje.isoformat()}.json")
        snap = dict(r, data=hoje.isoformat())
        with open(alvo, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, ensure_ascii=False)
        print(f"snapshot: {os.path.relpath(alvo, ROOT)}")
        historico = [h for h in historico if h.get("data") != hoje.isoformat()]
        historico.append(snap)
        historico.sort(key=lambda h: h.get("data", ""))

    saida = args.saida or os.path.join(ROOT, "test", "dashboard.html")
    with open(saida, "w", encoding="utf-8") as fh:
        fh.write(render(d, r, historico, hoje))

    print(f"painel: {os.path.relpath(saida, ROOT)}")
    print(f"  {r['casos']} casos | cobertura {r['cobertura_pct']}% | "
          f"conversão {r['conversao_pct']}% | {r['nunca_executados']} nunca executados")
    if r["migracao_pendente"]:
        print(f"  migração do Qase: {r['migracao_pendente']} caso(s) aguardando regra")
    if r["bugs_s1"]:
        print(f"  ATENCAO: {r['bugs_s1']} defeito(s) S1 em aberto")


if __name__ == "__main__":
    main()
