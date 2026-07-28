#!/usr/bin/env python3
"""
Gera o Relatório de Testes no modelo padrão Atlante.

NÃO recria o documento: preenche o template em templates/, preservando logo,
cabeçalho, rodapé (CNPJ + ISO 9001), fontes e estilos da empresa.

O que o script calcula sozinho (a partir de test/cases, test/runs e bugs/):
  - período, número de ciclos, contagens de casos e percentuais
  - tabela de defeitos por severidade (S1..S4)
  - critérios de saída, avaliados contra as metas
  - proposta de recomendação GO / GO com ressalvas / NO-GO

O que fica como [PLACEHOLDER] para o QA preencher:
  - a decisão final GO/NO-GO e sua justificativa
  - riscos residuais, plano de rollback e monitoramento
  - itens fora de escopo e quem aceitou o risco
  - nomes de QA Leader e PMO na aprovação

Uso:
    python3 test/scripts/qa_report.py
    python3 test/scripts/qa_report.py --release "v1.2" --fase "Regressão" --build "#4471"
"""

import argparse
import datetime
import glob
import html as htmlmod
import json
import os
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_run import (parse_features, load_runs, consolida_rodada,  # noqa: E402
                    numeros_de_rodada, STATUS)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(ROOT, "templates", "Relatorio_de_Testes_Atlante.docx")
BUGS_DIR = os.path.join(ROOT, "bugs")

# Severidade no padrão Atlante. O AP usa prioridade (Baixa/Alta/Critica/
# Bloqueada); aqui é severidade S1..S4 -- são coisas diferentes, ver README.
SEV_ORDEM = ["S1", "S2", "S3", "S4"]
SEV_ROTULO = {"S1": "Crítico (S1)", "S2": "Alto (S2)",
              "S3": "Médio (S3)", "S4": "Baixo (S4)"}
SEV_ALIAS = {"critico": "S1", "crítico": "S1", "critica": "S1", "crítica": "S1",
             "alto": "S2", "alta": "S2", "medio": "S3", "médio": "S3",
             "media": "S3", "média": "S3", "baixo": "S4", "baixa": "S4",
             "bloqueada": "S1", "bloqueador": "S1"}

PLACEHOLDER = "[PREENCHER]"


# --------------------------------------------------------------------------- #
# manipulação do docx preservando o template
# --------------------------------------------------------------------------- #

def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def texto_do_paragrafo(p_xml):
    # atencao: precisa exigir espaco ou fechamento apos "w:t", senao o padrao
    # casa tambem com <w:tab/> e a extracao vaza para o run seguinte
    return htmlmod.unescape(
        "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p_xml, re.S)))


def reescreve_paragrafo(p_xml, novo_texto):
    """Troca o conteúdo do parágrafo mantendo estilo do parágrafo e do 1º run."""
    abertura = re.match(r"<w:p\b[^>]*>", p_xml).group(0)
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p_xml, re.S)
    ppr = ppr.group(0) if ppr else ""
    rpr = re.search(r"<w:r\b[^>]*>\s*(<w:rPr>.*?</w:rPr>)", p_xml, re.S)
    rpr = rpr.group(1) if rpr else ""
    partes = str(novo_texto).split("\n")
    runs = []
    for i, parte in enumerate(partes):
        if i:
            runs.append(f"<w:r>{rpr}<w:br/></w:r>")
        runs.append(f'<w:r>{rpr}<w:t xml:space="preserve">{esc(parte)}</w:t></w:r>')
    return f"{abertura}{ppr}{''.join(runs)}</w:p>"


def aplica(doc, regras):
    """Percorre os parágrafos em ordem, rastreando a seção corrente.

    O rastreio importa: o mesmo placeholder "[N]" aparece na tabela de
    resultados (seção 3) e na de defeitos (seção 4). Sem saber a seção, uma
    regra consome o placeholder da outra.
    """
    estado = {"secao": 0}
    saida, pos = [], 0
    for m in re.finditer(r"<w:p\b[^>]*>.*?</w:p>", doc, re.S):
        saida.append(doc[pos:m.start()])
        p = m.group(0)
        txt = texto_do_paragrafo(p)
        cab = re.match(r"\s*([1-8])\.\s+\w", txt)
        if cab:
            estado["secao"] = int(cab.group(1))
        novo = None
        for regra in regras:
            novo = regra(txt, estado["secao"])
            if novo is not None:
                break
        saida.append(reescreve_paragrafo(p, novo) if novo is not None else p)
        pos = m.end()
    saida.append(doc[pos:])
    return "".join(saida)


def define_linhas(doc, texto_marcador, n):
    """Deixa exatamente n cópias da linha-modelo que contém o marcador.

    O template traz 2 linhas de exemplo; se sobrarem, o relatório sai com
    linhas fantasma. Aqui todas as linhas com o marcador viram n cópias da
    primeira.
    """
    linhas = [m for m in re.finditer(r"<w:tr\b[^>]*>.*?</w:tr>", doc, re.S)
              if texto_marcador in texto_do_paragrafo(m.group(0))]
    if not linhas:
        return doc
    modelo = linhas[0].group(0)
    for m in reversed(linhas[1:]):
        doc = doc[:m.start()] + doc[m.end():]
    p = linhas[0]
    return doc[:p.start()] + (modelo * max(n, 0)) + doc[p.end():]


# --------------------------------------------------------------------------- #
# coleta dos dados
# --------------------------------------------------------------------------- #

def sev_de(bug):
    """Extrai S1..S4 do campo severidade do bug. None se não definido."""
    for campo in ("severidade_nivel", "severidade"):
        v = str(bug.get(campo) or "")
        m = re.search(r"\bS([1-4])\b", v, re.I)
        if m:
            return "S" + m.group(1)
        chave = v.strip().lower().split()[0].strip(":—-,.") if v.strip() else ""
        if chave in SEV_ALIAS:
            return SEV_ALIAS[chave]
    return None


def carrega_bugs():
    bugs = []
    for p in sorted(glob.glob(os.path.join(BUGS_DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                b = json.load(fh)
        except Exception:
            continue
        b["_arquivo"] = os.path.basename(p)
        b["_sev"] = sev_de(b)
        bugs.append(b)
    return bugs


def contexto():
    p = os.path.join(ROOT, "test", "contexto.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def metricas(casos, runs):
    # a rodada e a UNIDADE, nao o arquivo: CI e QA escrevem em arquivos
    # separados com o mesmo numero, e o parecer precisa dos dois. Ver
    # qa_run.consolida_rodada -- ler runs[-1] anunciava "2/3 executados"
    # num ciclo em que os 3 casos tinham rodado.
    ultima = consolida_rodada(runs)
    res = ultima.get("resultados", {})
    planejado = len(casos)
    cont = {s: 0 for s in STATUS}
    for cid in casos:
        cont[res.get(cid, {}).get("status", "nao_executado")] += 1
    executado = cont["passou"] + cont["falhou"] + cont["bloqueado"]
    aprovado, reprovado, bloqueado = cont["passou"], cont["falhou"], cont["bloqueado"]
    taxa_exec = executado / planejado * 100 if planejado else 0
    taxa_aprov = aprovado / executado * 100 if executado else 0
    return dict(planejado=planejado, executado=executado, aprovado=aprovado,
                reprovado=reprovado, bloqueado=bloqueado,
                taxa_exec=taxa_exec, taxa_aprov=taxa_aprov,
                # ciclos = rodadas distintas. len(runs) contava DOIS para um
                # ciclo que teve rodada de CI e rodada manual.
                ciclos=len(numeros_de_rodada(runs)))


def rns_definidas():
    """{RN-XX} declaradas nos REGRAS.md de todas as features.

    Mesma leitura do qa_lint: so conta RN em linha de tabela ou cabecalho --
    mencao em prosa nao e declaracao de regra.
    """
    rns = set()
    for p in glob.glob(os.path.join(ROOT, "test", "cases", "*", "REGRAS.md")):
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        rns |= set(re.findall(r"^\s*\|\s*\**(RN-\d+)\**\s*\|", txt, re.M))
        rns |= set(re.findall(r"^#+\s*\**(RN-\d+)", txt, re.M))
    return rns


def criterios_saida(m, bugs, casos, res):
    """Avalia os criterios de saida do parecer.

    Cada linha mede uma coisa diferente. Antes, 'casos criticos executados' e
    'cobertura de requisitos' eram os dois a mesma taxa de execucao geral --
    numeros plausiveis medindo o que o nome nao diz, que e a pior especie de
    metrica: ninguem desconfia dela.
    """
    abertos = [b for b in bugs if b.get("status_bug", "aberto") == "aberto"]
    s1 = sum(1 for b in abertos if b["_sev"] == "S1")
    s2 = sum(1 for b in abertos if b["_sev"] == "S2")

    # criticos = risco alto declarado na tag, nao "todos os casos"
    criticos = [c for c, i in casos.items()
                if "prioridade:alta" in i.get("tecnicas", [])]
    crit_exec = sum(1 for c in criticos
                    if res.get(c, {}).get("status") in ("passou", "falhou", "bloqueado"))
    taxa_crit = crit_exec / len(criticos) * 100 if criticos else 0.0

    # cobertura = RN com ao menos um CT, sobre as RN declaradas nos REGRAS.md
    rns_req = rns_definidas()
    rns_cobertas = {t for i in casos.values() for t in i.get("tecnicas", [])
                    if t.startswith("RN-")}
    cob = len(rns_req & rns_cobertas) / len(rns_req) * 100 if rns_req else 0.0

    # conversao = automatizados sobre o total, excluindo nao-automatizar
    elegiveis = [c for c, i in casos.items()
                 if not i.get("automacao", "").startswith("nao-automatizar")]
    feitos = sum(1 for c in elegiveis
                 if casos[c].get("automacao", "").startswith("feito"))
    conv = feitos / len(elegiveis) * 100 if elegiveis else 0.0

    # falha sem defeito registrado. O relatorio contava defeito SO a partir de
    # bugs/*.json: uma rodada com caso reprovado e nenhum bug cadastrado saía
    # com "0 defeitos em aberto" no sumário executivo -- o primeiro número que o
    # PMO lê. Falha sem bug não é ausência de defeito, é defeito que ninguém
    # registrou. O qa_ingest e o qa_run já avisam no terminal; aqui vira critério.
    sem_bug = sorted(c for c, i in res.items()
                     if i.get("status") == "falhou" and not i.get("bug"))

    itens = [
        ("Casos críticos executados", "100%",
         f"{taxa_crit:.0f}% ({crit_exec}/{len(criticos)})" if criticos else "sem casos @prioridade:alta",
         (taxa_crit >= 100) if criticos else None),
        ("Taxa de aprovação geral", "≥ 95%", f"{m['taxa_aprov']:.0f}%", m["taxa_aprov"] >= 95),
        ("Defeitos S1 em aberto", "0", str(s1), s1 == 0),
        ("Defeitos S2 em aberto", "≤ 2", str(s2), s2 <= 2),
        ("Cobertura de requisitos", "≥ 90%",
         f"{cob:.0f}% ({len(rns_req & rns_cobertas)}/{len(rns_req)} RN)" if rns_req else "sem REGRAS.md",
         (cob >= 90) if rns_req else None),
        ("Regressão automatizada", "100%",
         f"{conv:.0f}% ({feitos}/{len(elegiveis)})", conv >= 100),
        # meta 0 e valor [N], no mesmo formato das linhas de S1/S2 -- a tabela
        # do modelo tem uma linha por criterio, e a ordem daqui casa com a
        # ordem dos rotulos de la. Ver TestCriteriosCasamComOModelo.
        ("Falhas sem defeito registrado", "0", str(len(sem_bug)), not sem_bug),
    ]
    return itens, s1, s2, sem_bug


def recomendacao(itens, s1):
    desconhecidos = [i for i in itens if i[3] is None]
    falhos = [i for i in itens if i[3] is False]
    if s1 > 0 or len(falhos) >= 3:
        base = "NO-GO"
    elif falhos:
        base = "GO com ressalvas"
    else:
        base = "GO"
    return base, falhos, desconhecidos


# --------------------------------------------------------------------------- #

def gerar(args):
    if not os.path.exists(TEMPLATE):
        sys.exit(f"erro: template não encontrado em {os.path.relpath(TEMPLATE, ROOT)}")

    casos, runs, bugs, ctx = parse_features(), load_runs(), carrega_bugs(), contexto()
    if not runs:
        sys.exit("erro: nenhuma rodada em test/runs/ (crie com qa_run.py --init 1)")
    if not casos:
        sys.exit("erro: nenhum caso em test/cases/ (cenários precisam da tag @CT-XXX)")

    m = metricas(casos, runs)
    if m["executado"] == 0:
        sys.exit("erro: nenhum caso foi executado ainda -- não há o que relatar.")

    ultima = consolida_rodada(runs)
    itens_crit, s1, s2, sem_bug = criterios_saida(m, bugs, casos,
                                                  ultima.get("resultados", {}))
    rec, falhos, _ = recomendacao(itens_crit, s1)

    projeto = args.projeto or ultima.get("feature") or ctx.get("aplicacao") or PLACEHOLDER
    release = args.release or ultima.get("versao") or PLACEHOLDER
    fase = args.fase or "Funcional"
    curto = re.sub(r"[^A-Za-z0-9]", "", (projeto.split("—")[0]))[:12] or "PROJ"
    hoje = datetime.date.today().strftime("%d/%m/%Y")

    def br(d):
        try:
            return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return d or PLACEHOLDER
    periodo = f"{br(runs[0].get('data'))} a {br(ultima.get('data'))}"

    abertos = [b for b in bugs if b.get("status_bug", "aberto") == "aberto"]
    por_sev = {s: sum(1 for b in abertos if b["_sev"] == s) for s in SEV_ORDEM}
    sem_sev = [b for b in bugs if not b["_sev"]]

    # ---- mapa de substituições -------------------------------------------- #
    trocas = {
        "[Projeto] — Release [vX.Y] — [Fase de teste]": f"{projeto} — Release {release} — {fase}",
        "Modelo padrão Atlante. Substitua os textos entre colchetes e remova esta nota antes de distribuir.": "",
        "QA-REL-[NomeCurto]-[vX.Y]": f"QA-REL-{curto}-{release}",
        "[Nome / Cargo]": args.responsavel or ultima.get("executor") or PLACEHOLDER,
        "[dd/mm/aaaa] a [dd/mm/aaaa]": periodo,
        "[vX.Y — build #____]": args.build or f"{release} — build {PLACEHOLDER}",
        "1.0 — [dd/mm/aaaa]": f"1.0 — {hoje}",
        "Recomendação:   [ ] GO      [ ] GO com ressalvas      [ ] NO-GO":
            "Recomendação:   "
            + ("[X]" if rec == "GO" else "[ ]") + " GO      "
            + ("[X]" if rec == "GO com ressalvas" else "[ ]") + " GO com ressalvas      "
            + ("[X]" if rec == "NO-GO" else "[ ]") + " NO-GO"
            + "     (proposta automática — confirmar)",
    }

    def regra_exata(txt, secao):
        t = txt.strip()
        return trocas.get(t)

    def regra_sumario(txt, secao):
        t = txt.strip()
        if t.startswith("•Resultado —"):
            # a ressalva das falhas sem bug vai NO MESMO parágrafo do número de
            # defeitos: separá-las deixaria "0 defeitos em aberto" sozinho na
            # linha que o PMO lê primeiro.
            extra = (f", mais {len(sem_bug)} falha(s) sem defeito registrado"
                     if sem_bug else "")
            return (f"•Resultado — {m['taxa_exec']:.0f}% dos casos executados, "
                    f"{m['taxa_aprov']:.0f}% de aprovação, {len(abertos)} defeitos em aberto "
                    f"({por_sev['S1']} críticos){extra}.")
        if t.startswith("•Critérios de saída —"):
            n_fail = len(falhos)
            estado = ("atendidos" if not n_fail else
                      f"atendidos com exceção ({n_fail} não atendido(s))")
            return f"•Critérios de saída — {estado}."
        if t.startswith("•Principal risco residual —"):
            return f"•Principal risco residual — {PLACEHOLDER}."
        if t.startswith("•Decisão solicitada —"):
            alvo = {"GO": "aprovar a release",
                    "GO com ressalvas": "aprovar com contingência",
                    "NO-GO": "adiar o deploy"}[rec]
            return f"•Decisão solicitada — {alvo}."
        if t.startswith("Justificativa:"):
            det = "; ".join(f"{c[0]}: {c[2]} (meta {c[1]})" for c in falhos) or \
                  "todos os critérios de saída foram atendidos"
            return (f"Justificativa: proposta de {rec} com base em {det}. "
                    f"{m['executado']}/{m['planejado']} casos executados em {m['ciclos']} "
                    f"ciclo(s). {PLACEHOLDER} — revisar e complementar o racional.")
        if t.startswith("•Taxa de execução —"):
            return (f"•Taxa de execução — {m['taxa_exec']:.0f}% — {m['executado']} "
                    f"executados sobre {m['planejado']} planejados.")
        if t.startswith("•Taxa de aprovação —"):
            return (f"•Taxa de aprovação — {m['taxa_aprov']:.0f}% — {m['aprovado']} "
                    f"aprovados sobre {m['executado']} executados.")
        if t.startswith("•Ciclos —"):
            return f"•Ciclos — {m['ciclos']} — rodadas de execução e reteste."
        return None

    def regra_ambiente(txt, secao):
        t = txt.strip()
        if t.startswith("•Ambiente —"):
            return f"•Ambiente — {ctx.get('ambiente') or PLACEHOLDER}."
        if t.startswith("•Versões —"):
            return f"•Versões — {release}."
        if t.startswith("•Massa de dados —"):
            return f"•Massa de dados — {PLACEHOLDER}."
        if t.startswith("•Ferramentas —"):
            fer = ["Gherkin (test/cases)", "qa_run.py", "Playwright MCP"]
            if ctx.get("contexto_tecnico", {}).get("contrato_api"):
                fer.append("Postman")
            return "•Ferramentas — " + "; ".join(fer) + "."
        if t.startswith("•Anexos —"):
            return ("•Anexos — test/cases/ (casos), test/runs/ (resultados por rodada), "
                    "test/image/ (evidências), bugs/ (defeitos).")
        return None

    doc = zipfile.ZipFile(TEMPLATE).read("word/document.xml").decode("utf-8")

    # ---- tabelas com linhas repetidas ------------------------------------- #
    doc = define_linhas(doc, "[PROJ-000]", max(len(abertos), 1))
    doc = define_linhas(doc, "[Módulo]", 1)
    doc = define_linhas(doc, "[Item]", 1)

    # ---- filas consumidas na ordem em que aparecem no documento ----------- #
    fila_res_n = [m["planejado"], m["executado"], m["aprovado"],
                  m["reprovado"], m["bloqueado"]]
    fila_res_pct = [f"{m['executado'] / m['planejado'] * 100:.0f}%",
                    f"{m['aprovado'] / m['planejado'] * 100:.0f}%",
                    f"{m['reprovado'] / m['planejado'] * 100:.0f}%",
                    f"{m['bloqueado'] / m['planejado'] * 100:.0f}%"]
    fila_sev_n = []
    for s in SEV_ORDEM:
        fila_sev_n += [str(por_sev[s]), "0"]          # em aberto, resolvidos
    fila_crit = list(itens_crit)
    fila_defeitos = list(abertos)
    est = {"def_idx": -1}

    def regra_sec3(txt, secao):
        if secao != 3:
            return None
        t = txt.strip()
        if t == "[N]" and fila_res_n:
            return str(fila_res_n.pop(0))
        if t == "[%]" and fila_res_pct:
            return fila_res_pct.pop(0)
        return None

    def regra_sec4(txt, secao):
        if secao != 4:
            return None
        t = txt.strip()
        if t == "[N]" and fila_sev_n:
            return fila_sev_n.pop(0)
        if t == "[↑ / ↓ / estável]":
            return "—"
        if t == "[PROJ-000]":
            est["def_idx"] += 1
            i = est["def_idx"]
            if i < len(fila_defeitos):
                b = fila_defeitos[i]
                return b.get("caso_de_teste") or b["_arquivo"].replace(".json", "")
            return "—"
        i = est["def_idx"]
        b = fila_defeitos[i] if 0 <= i < len(fila_defeitos) else None
        if t == "[Título]":
            return b.get("resumo", "—") if b else "—"
        if t == "[S1-S4]":
            return (b["_sev"] or PLACEHOLDER) if b else "—"
        if t == "[Impacto] / [Contorno]":
            if not b:
                return "—"
            imp = (b.get("impacto") or "").strip()
            imp = (imp[:170] + "…") if len(imp) > 170 else imp
            return f"{imp or '—'} / {PLACEHOLDER}"
        if t == "[vX.Y]":
            return PLACEHOLDER
        return None

    def regra_sec5(txt, secao):
        if secao != 5:
            return None
        t = txt.strip()
        if t in ("[%]", "[N]") and fila_crit:
            return fila_crit[0][2]
        if t == "[Atendido]" and fila_crit:
            c = fila_crit.pop(0)
            return ("Atendido" if c[3] else
                    "Não atendido" if c[3] is False else PLACEHOLDER)
        return None

    def regra_generica(txt, secao):
        t = txt.strip()
        if re.fullmatch(r"\[[^\]]+\]", t):
            return PLACEHOLDER
        return None

    doc = aplica(doc, [regra_exata, regra_sumario, regra_ambiente,
                       regra_sec3, regra_sec4, regra_sec5, regra_generica])

    # ---- escreve o docx preservando todas as outras partes ---------------- #
    saida = args.saida or os.path.join(
        ROOT, "test", f"Relatorio_de_Testes_{curto}_rodada-{ultima.get('rodada')}.docx")
    origem = zipfile.ZipFile(TEMPLATE)
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for item in origem.infolist():
            dados = origem.read(item.filename)
            if item.filename == "word/document.xml":
                dados = doc.encode("utf-8")
            z.writestr(item, dados)

    print(f"relatório gerado: {os.path.relpath(saida, ROOT)}")
    print(f"  recomendação proposta: {rec}")
    print(f"  {m['executado']}/{m['planejado']} executados | "
          f"{m['taxa_aprov']:.0f}% aprovação | {len(abertos)} defeito(s) em aberto")
    if falhos:
        print("  criterios NAO atendidos: " + "; ".join(c[0] for c in falhos))
    if sem_bug:
        print(f"  ATENCAO: {len(sem_bug)} caso(s) reprovado(s) sem bug cadastrado: "
              + ", ".join(sem_bug))
        print("           o relatorio conta defeito por bugs/*.json — sem cadastro,")
        print("           a falha nao aparece na tabela de defeitos do PMO.")
        print("           abra com /qa-defeito e feche com rise_bug.py --rodada N")
    if sem_sev:
        print(f"  ATENCAO: {len(sem_sev)} defeito(s) sem severidade S1..S4 definida: "
              + ", ".join(b["_arquivo"] for b in sem_sev))
    print(f"  revise os campos marcados como {PLACEHOLDER} antes de distribuir.")


def main():
    ap = argparse.ArgumentParser(description="Gera o Relatório de Testes no modelo Atlante")
    ap.add_argument("--projeto")
    ap.add_argument("--release")
    ap.add_argument("--fase", help="Funcional / Regressão / API / Performance")
    ap.add_argument("--build")
    ap.add_argument("--responsavel")
    ap.add_argument("--saida")
    gerar(ap.parse_args())


if __name__ == "__main__":
    main()
