#!/usr/bin/env python3
"""
qa-lint — consistência do sistema de QA.

Substitui as validações que um TMS fazia por construção. Roda em todo PR e falha
o build. Sem isso, em dois meses a matriz vira ficção.

Uso:
    python3 test/scripts/qa_lint.py            # todas as features
    python3 test/scripts/qa_lint.py --feature saucedemo
    python3 test/scripts/qa_lint.py --fix-hash # regrava os hashes de requisito após revisão

Saída: 0 se tudo certo, 1 se houver violação.
"""

import argparse
import glob
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASES = os.path.join(ROOT, "test", "cases")

CAMADAS = {"api", "banco", "contrato", "e2e", "performance", "seguranca", "manual"}
SUITES = {"smoke", "regressao", "nightly", "release"}

erros, avisos = [], []


def erro(feature, regra, msg):
    erros.append(f"[{feature}] {regra}: {msg}")


def aviso(feature, regra, msg):
    avisos.append(f"[{feature}] {regra}: {msg}")


# --------------------------------------------------------------------------- #

def le_cenarios(path):
    """[(CT, titulo, tags, linha)] de um .feature."""
    out, pend = [], None
    for n, linha in enumerate(open(path, encoding="utf-8"), 1):
        s = linha.strip()
        if s.startswith("#"):
            continue
        if s.startswith("@"):
            tags = re.findall(r"@([\w:.\-]+)", s)
            ids = [t for t in tags if re.fullmatch(r"CT-[\w-]+", t)]
            if ids:
                pend = (ids[0], tags, n)
            continue
        m = re.match(r"^(Cen[áa]rio|Esquema do Cen[áa]rio|Scenario"
                     r"|Scenario Outline)\s*:\s*(.+)$", s)
        if m and pend:
            cid, tags, ln = pend
            out.append((cid, m.group(2).strip(), tags, ln))
            pend = None
    return out


def le_matriz(path):
    """CTs citados na matriz + metadados do cabeçalho qa-lint."""
    txt = open(path, encoding="utf-8").read()
    meta = {}
    m = re.search(r"<!--\s*qa-lint:\s*(.*?)-->", txt, re.S)
    if m:
        meta = dict(re.findall(r"(\w+)=(\S+)", m.group(1)))
    cts = set(re.findall(r"\bCT-\d+\b", txt))
    # intervalos "CT-001..CT-006"
    for a, b in re.findall(r"CT-(\d+)\.\.CT-(\d+)", txt):
        for i in range(int(a), int(b) + 1):
            cts.add(f"CT-{i:03d}")
    rns = set(re.findall(r"\bRN-\d+\b", txt))
    return cts, rns, meta, txt


def checa_feature(dirpath):
    feature = os.path.basename(dirpath)
    features = glob.glob(os.path.join(dirpath, "*.feature"))
    matriz = os.path.join(dirpath, "MATRIZ.md")
    lacunas = os.path.join(dirpath, "LACUNAS.md")
    regras = os.path.join(dirpath, "REGRAS.md")

    if not features:
        erro(feature, "estrutura", "pasta sem nenhum .feature")
        return
    # regra: nenhum .feature sem LACUNAS.md correspondente (mesmo vazio e datado)
    if not os.path.exists(lacunas):
        erro(feature, "estrutura", "falta LACUNAS.md (crie mesmo que vazio, com data)")
    if not os.path.exists(matriz):
        erro(feature, "estrutura", "falta MATRIZ.md")
        return
    if not os.path.exists(regras):
        erro(feature, "estrutura",
             "falta REGRAS.md — as RN extraídas do requisito, que é a matéria-prima crua")

    cts_matriz, rns_matriz, meta, txt_matriz = le_matriz(matriz)

    cenarios, vistos = [], {}
    for f in features:
        for cid, titulo, tags, ln in le_cenarios(f):
            cenarios.append((cid, titulo, tags, os.path.basename(f), ln))
            if cid in vistos:
                erro(feature, "id-duplicado",
                     f"{cid} aparece em {vistos[cid]} e em {os.path.basename(f)}:{ln}")
            vistos[cid] = f"{os.path.basename(f)}:{ln}"

    if not cenarios:
        erro(feature, "tags", "nenhum cenário com tag @CT-XXX")
        return

    # --- tags obrigatórias ------------------------------------------------- #
    for cid, titulo, tags, arq, ln in cenarios:
        tset = set(tags)
        if not any(t.startswith("RN-") for t in tags):
            erro(feature, "tags", f"{cid} ({arq}:{ln}) sem @RN-XX")
        camadas = [t.split(":", 1)[1] for t in tags if t.startswith("camada:")]
        if not camadas:
            erro(feature, "tags", f"{cid} sem @camada:")
        elif camadas[0] not in CAMADAS:
            erro(feature, "tags", f"{cid} com @camada:{camadas[0]} inválida")
        suites = [t.split(":", 1)[1] for t in tags if t.startswith("suite:")]
        if not suites:
            erro(feature, "tags", f"{cid} sem @suite:")
        elif suites[0] not in SUITES:
            erro(feature, "tags", f"{cid} com @suite:{suites[0]} inválida")

        # cenário não aprovado ou com premissa pendente não pode estar na suíte oficial
        if "premissa" in tset and "nao-aprovado" not in tset:
            erro(feature, "portao",
                 f"{cid} tem @premissa pendente mas não está marcado @nao-aprovado — "
                 f"entraria na suíte oficial")
        aprovado = [t for t in tags if t.startswith("aprovado-por:")]
        if not aprovado and "nao-aprovado" not in tset:
            aviso(feature, "portao",
                  f"{cid} sem @aprovado-por: — não roda na suíte oficial")
        if aprovado and not any(t.startswith("data:") for t in tags):
            erro(feature, "portao",
                 f"{cid} tem @aprovado-por sem @data: — aprovação é ato nominal COM data")

        # automacao:nao-automatizar exige motivo escrito
        for t in tags:
            if t.startswith("automacao:nao-automatizar"):
                motivo = t.split(":", 2)[2] if t.count(":") >= 2 else ""
                if len(motivo) < 4:
                    erro(feature, "automacao",
                         f"{cid} com nao-automatizar sem motivo escrito")
            # automacao:feito:<PR> precisa apontar para spec que existe
            if t.startswith("automacao:feito"):
                specs = glob.glob(os.path.join(ROOT, "test", "api", "**", "*.spec.*"),
                                  recursive=True)
                specs += glob.glob(os.path.join(ROOT, "test", "e2e", "**", "*.spec.*"),
                                   recursive=True)
                achou = any(cid in open(s, encoding="utf-8", errors="replace").read()
                            for s in specs)
                if not achou:
                    erro(feature, "automacao-fantasma",
                         f"{cid} marcado @{t} mas nenhuma spec em test/api ou test/e2e "
                         f"referencia esse CT")
            # prioridade com valor valido
            if t.startswith("prioridade:"):
                v = t.split(":", 1)[1]
                if v not in {"alta", "media", "baixa"}:
                    erro(feature, "tags", f"{cid} com @prioridade:{v} inválida")
            # obsoleto exige data e sai da suite oficial
            if t.startswith("obsoleto"):
                if not re.fullmatch(r"obsoleto:\d{4}-\d{2}-\d{2}", t):
                    erro(feature, "obsoleto",
                         f"{cid} com @{t} — use @obsoleto:AAAA-MM-DD")
                if any(x.startswith("aprovado-por:") for x in tags):
                    erro(feature, "obsoleto",
                         f"{cid} está @obsoleto mas mantém @aprovado-por — "
                         f"continuaria rodando na suíte oficial")

    # --- matriz × feature (dois sentidos) ---------------------------------- #
    ids = {c[0] for c in cenarios}
    for cid in sorted(ids - cts_matriz):
        erro(feature, "matriz", f"{cid} existe no .feature mas não está na MATRIZ.md")
    for cid in sorted(cts_matriz - ids):
        erro(feature, "matriz", f"{cid} está na MATRIZ.md mas não existe em nenhum .feature")

    # --- toda RN do requisito tem ao menos um CT --------------------------- #
    req_rel = meta.get("requisito")
    if req_rel:
        req_path = os.path.normpath(os.path.join(dirpath, req_rel))
        if not os.path.exists(req_path):
            erro(feature, "requisito", f"arquivo não encontrado: {req_rel}")
        else:
            txt_req = open(regras, encoding="utf-8").read() \
                if os.path.exists(regras) else open(req_path, encoding="utf-8").read()
            # RN-XX no inicio da linha, com ou sem cabecalho markdown
            rns_req = set(re.findall(r"^#*\s*\**(RN-\d+)", txt_req, re.M))
            rns_cobertas = {t[3:] if False else t for c in cenarios for t in c[2]
                            if t.startswith("RN-")}
            # escape legítimo: @sem-caso:<motivo> declarado na matriz
            sem_caso = set(re.findall(r"@sem-caso:(RN-\d+)", txt_matriz))
            for rn in sorted(rns_req - rns_cobertas - sem_caso):
                erro(feature, "cobertura",
                     f"{rn} não tem nenhum CT (use @sem-caso:{rn} na matriz, "
                     f"com motivo, se for intencional)")

            # --- obsolescência: requisito mudou, casos não foram revisados --- #
            h_atual = hashlib.sha256(open(req_path, "rb").read()).hexdigest()[:12]
            h_matriz = meta.get("hash")
            if not h_matriz:
                aviso(feature, "obsolescencia",
                      "MATRIZ.md sem hash do requisito — adicione o cabeçalho qa-lint")
            elif h_atual != h_matriz:
                erro(feature, "obsolescencia",
                     f"o requisito mudou (hash {h_matriz} → {h_atual}). "
                     f"Revise os casos das RN afetadas e rode --fix-hash para confirmar")

    # --- teto de E2E: max(1, 10%) ------------------------------------------ #
    n_e2e = sum(1 for c in cenarios
                if any(t == "camada:e2e" for t in c[2]))
    teto = max(1, round(len(cenarios) * 0.10))
    if n_e2e > teto:
        erro(feature, "teto-e2e",
             f"{n_e2e} cenários em @camada:e2e; teto é {teto} "
             f"(max(1, 10%) de {len(cenarios)}). Reclassifique para camadas mais baratas")

    return cenarios


def fix_hash():
    for dirpath in sorted(glob.glob(os.path.join(CASES, "*"))):
        matriz = os.path.join(dirpath, "MATRIZ.md")
        if not os.path.isdir(dirpath) or not os.path.exists(matriz):
            continue
        _, _, meta, txt = le_matriz(matriz)
        req = meta.get("requisito")
        if not req:
            continue
        req_path = os.path.normpath(os.path.join(dirpath, req))
        if not os.path.exists(req_path):
            continue
        h = hashlib.sha256(open(req_path, "rb").read()).hexdigest()[:12]
        novo = re.sub(r"(<!--\s*qa-lint:[^>]*?hash=)\S+", r"\g<1>" + h, txt)
        open(matriz, "w", encoding="utf-8").write(novo)
        print(f"hash atualizado: {os.path.basename(dirpath)} -> {h}")


def checa_runs():
    """Execução oficial não pode ter sido feita por agente.

    Agente explora, autora e diagnostica; a regressão é código determinístico.
    Resultado de agente vive em test/sessoes/, nunca em test/runs/.
    """
    import json
    for p in glob.glob(os.path.join(ROOT, "test", "runs", "**", "*.json"),
                       recursive=True):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        nome = os.path.relpath(p, ROOT)
        for cid, info in (d.get("resultados") or {}).items():
            por = (info or {}).get("executado_por")
            if por in ("agente", "claude", "ia"):
                erro("runs", "execucao-por-agente",
                     f"{nome}: {cid} com executado_por='{por}'. "
                     f"Execução oficial é 'qa' ou 'ci'. Mova para test/sessoes/")
                break


def main():
    ap = argparse.ArgumentParser(description="Consistência do sistema de QA")
    ap.add_argument("--feature", help="valida apenas uma feature")
    ap.add_argument("--fix-hash", action="store_true",
                    help="regrava o hash do requisito após revisão dos casos")
    args = ap.parse_args()

    if args.fix_hash:
        fix_hash()
        return

    dirs = [d for d in sorted(glob.glob(os.path.join(CASES, "*"))) if os.path.isdir(d)]
    if args.feature:
        dirs = [d for d in dirs if os.path.basename(d) == args.feature]
        if not dirs:
            sys.exit(f"erro: feature '{args.feature}' não existe em test/cases/")
    if not dirs:
        # kit recem-clonado: nao ha o que verificar, e isso nao e erro
        print("qa-lint: nenhuma feature em test/cases/ ainda.\n"
              "         Comece com /qa-intake para extrair as regras da sua feature.")
        return

    total = 0
    for d in dirs:
        c = checa_feature(d)
        total += len(c or [])
    checa_runs()

    print(f"qa-lint: {len(dirs)} feature(s), {total} cenário(s)\n")
    for a in avisos:
        print(f"  aviso  {a}")
    for e in erros:
        print(f"  ERRO   {e}")
    print()
    if erros:
        print(f"FALHOU: {len(erros)} violação(ões), {len(avisos)} aviso(s)")
        sys.exit(1)
    print(f"OK: nenhuma violação, {len(avisos)} aviso(s)")


if __name__ == "__main__":
    main()
