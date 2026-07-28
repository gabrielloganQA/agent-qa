#!/usr/bin/env python3
"""
qa-lint — consistência do sistema de QA.

Substitui as validações que um TMS fazia por construção. Roda em todo PR e falha
o build. Sem isso, em dois meses a matriz vira ficção.

Uso:
    python3 test/scripts/qa_lint.py             # todas as features
    python3 test/scripts/qa_lint.py --feature saucedemo
    python3 test/scripts/qa_lint.py --fix-hash  # regrava os hashes após revisão
    python3 test/scripts/qa_lint.py --check-kit # valida o kit, não os artefatos

Vocabulário: docs/GLOSSARIO.md é a fonte única de tags, status e IDs.
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
SKILLS = os.path.join(ROOT, ".claude", "skills")

CAMADAS = {"api", "banco", "contrato", "e2e", "performance", "seguranca", "manual"}
SUITES = {"smoke", "regressao", "nightly", "release"}
PRIORIDADES = {"alta", "media", "baixa"}

# toda camada que pode conter codigo de teste. Antes so api e e2e eram varridos,
# entao uma spec de performance ou de contrato que citava o CT era acusada de
# automacao fantasma.
DIRS_SPEC = ["api", "e2e", "performance", "banco", "contrato", "seguranca", "support"]

erros, avisos = [], []
_specs_cache = {}


def base_de(raiz_de_casos):
    """A pasta que contém as camadas — irmã da raiz de casos.

    No repositório é `test/`: test/cases ao lado de test/api e test/e2e. Uma
    raiz alternativa passada em --dir segue a mesma forma — `piloto/cases`
    implica `piloto/api`.
    """
    return os.path.normpath(os.path.dirname(raiz_de_casos))


def specs_do_repo(base=None):
    """[(caminho_relativo, conteudo)] das specs sob `base`, lido uma vez por base.

    Antes o glob rodava dentro do laco de cenarios: numa feature com 30 casos
    @automacao:feito, o disco era varrido 30 vezes.

    O caminho passou a ser guardado junto quando checa_specs() entrou: acusar
    afrouxamento sem dizer em que arquivo e linha e um aviso que ninguem age.

    E `base` deixou de ser `test/` cravado no mesmo momento: com o caminho fixo,
    uma raiz alternativa passada em --dir era validada contra as specs de test/,
    que nao sao as dela.
    """
    chave = os.path.normpath(base or os.path.join(ROOT, "test"))
    if chave in _specs_cache:
        return _specs_cache[chave]
    achados, vistos = [], set()
    for d in DIRS_SPEC:
        for padrao in ("*.spec.*", "*.test.*", "*.js", "*.ts", "*.py"):
            for s in glob.glob(os.path.join(chave, d, "**", padrao), recursive=True):
                rel = os.path.relpath(s, ROOT).replace("\\", "/")
                # *.spec.ts casa tanto em "*.spec.*" quanto em "*.ts"
                if rel in vistos:
                    continue
                try:
                    with open(s, encoding="utf-8", errors="replace") as fh:
                        achados.append((rel, fh.read()))
                    vistos.add(rel)
                except OSError:
                    pass
    _specs_cache[chave] = achados
    return achados


def erro(feature, regra, msg):
    erros.append(f"[{feature}] {regra}: {msg}")


def aviso(feature, regra, msg):
    avisos.append(f"[{feature}] {regra}: {msg}")


# --------------------------------------------------------------------------- #

def le_cenarios(path):
    """[(CT, titulo, tags, linha)] de um .feature."""
    out, pend = [], None
    with open(path, encoding="utf-8") as fh:
        linhas = fh.readlines()
    for n, linha in enumerate(linhas, 1):
        s = linha.strip()
        if s.startswith("#"):
            continue
        if s.startswith("@"):
            tags = re.findall(r"@([\w:.\-/#]+)", s)
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
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    meta = {}
    m = re.search(r"<!--\s*qa-lint:\s*(.*?)-->", txt, re.S)
    if m:
        meta = dict(re.findall(r"(\w+)=(\S+)", m.group(1)))
    cts = set(re.findall(r"\bCT-\d+\b", txt))
    # intervalos escritos como "CT-001..CT-006"
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
    if not os.path.exists(lacunas):
        erro(feature, "estrutura", "falta LACUNAS.md (crie mesmo que vazio, com data)")
    if not os.path.exists(matriz):
        erro(feature, "estrutura", "falta MATRIZ.md")
        return
    if not os.path.exists(regras):
        erro(feature, "estrutura",
             "falta REGRAS.md — as RN extraídas do requisito, que é a matéria-prima crua")

    cts_matriz, _, meta, txt_matriz = le_matriz(matriz)

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
        # caso vindo do Qase ainda nao ligado a uma regra. Aviso, nao erro: e a
        # divida conhecida da migracao, e ela precisa ser commitavel para poder
        # ser paga aos poucos. O qa_dashboard mostra a curva.
        if "RN-PENDENTE" in tset:
            aviso(feature, "migracao",
                  f"{cid} está @RN-PENDENTE — importado do Qase e ainda sem "
                  f"regra de negócio vinculada (ver MIGRACAO.md)")
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

        # cenário com premissa pendente não pode entrar na suíte oficial
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

        for t in tags:
            # nao-automatizar exige motivo escrito
            if t.startswith("automacao:nao-automatizar"):
                motivo = t.split(":", 2)[2] if t.count(":") >= 2 else ""
                if len(motivo) < 4:
                    erro(feature, "automacao",
                         f"{cid} com nao-automatizar sem motivo escrito")
            # automacao:feito:<PR> precisa apontar para spec que existe
            if t.startswith("automacao:feito"):
                base = base_de(os.path.dirname(dirpath))
                if not any(cid in txt for _rel, txt in specs_do_repo(base)):
                    erro(feature, "automacao-fantasma",
                         f"{cid} marcado @{t} mas nenhuma spec em "
                         f"{'/'.join(DIRS_SPEC)} referencia esse CT")
            if t.startswith("prioridade:"):
                v = t.split(":", 1)[1]
                if v not in PRIORIDADES:
                    erro(feature, "tags", f"{cid} com @prioridade:{v} inválida")
            if t.startswith("obsoleto"):
                if not re.fullmatch(r"obsoleto:\d{4}-\d{2}-\d{2}", t):
                    erro(feature, "obsoleto", f"{cid} com @{t} — use @obsoleto:AAAA-MM-DD")
                if any(x.startswith("aprovado-por:") for x in tags):
                    erro(feature, "obsoleto",
                         f"{cid} está @obsoleto mas mantém @aprovado-por — "
                         f"continuaria rodando na suíte oficial")

    # --- matriz × feature, nos dois sentidos ------------------------------- #
    ids = {c[0] for c in cenarios}
    for cid in sorted(ids - cts_matriz):
        erro(feature, "matriz", f"{cid} existe no .feature mas não está na MATRIZ.md")
    for cid in sorted(cts_matriz - ids):
        erro(feature, "matriz", f"{cid} está na MATRIZ.md mas não existe em nenhum .feature")

    # --- valor esperado tirado de observação tem de ser premissa ------------ #
    # O viés central deste fluxo: derivar o caso do que o sistema FAZ em vez do que o
    # requisito MANDA. Caso cujo valor esperado foi lido da tela documenta o defeito
    # como comportamento correto e fica verde para sempre. Declarar a origem na matriz
    # torna isso mecânico, em vez de um aviso que ninguém lê.
    observados = set(re.findall(r"@observado:(CT-\d+)", txt_matriz))
    por_id = {c[0]: set(c[2]) for c in cenarios}
    for cid in sorted(observados):
        if cid not in por_id:
            erro(feature, "origem",
                 f"@observado:{cid} declarado na MATRIZ.md mas o CT não existe")
        elif "premissa" not in por_id[cid]:
            erro(feature, "origem",
                 f"{cid} tem valor esperado declarado @observado na MATRIZ.md mas não "
                 f"leva @premissa — valor lido do sistema é premissa até o PO confirmar, "
                 f"nunca asserção")
    # premissa vinda de lacuna: o CT aparece numa linha da matriz que cita a L-XX
    com_lacuna = set()
    for linha in txt_matriz.splitlines():
        if re.search(r"\bL-\d+\b", linha):
            com_lacuna |= set(re.findall(r"\bCT-\d+\b", linha))
    for cid in sorted(ids):
        if "premissa" in por_id[cid] and cid not in observados | com_lacuna:
            aviso(feature, "origem",
                  f"{cid} é @premissa mas a MATRIZ.md não diz de onde veio o valor "
                  f"esperado — acrescente @observado:{cid} ou cite a L-XX na linha dele")

    # --- toda RN do requisito tem ao menos um CT ---------------------------- #
    req_rel = meta.get("requisito")
    if req_rel:
        req_path = os.path.normpath(os.path.join(dirpath, req_rel))
        if not os.path.exists(req_path):
            # placeholder deixado pela importacao do Qase: a feature existe, o
            # requisito ainda nao. Avisa para nao travar a migracao no dia 1.
            if "<" in req_rel or "RF-XX" in req_rel:
                aviso(feature, "requisito",
                      f"requisito ainda não criado ({req_rel}). "
                      f"Rode /qa-intake e ajuste o cabeçalho da MATRIZ.md")
            else:
                erro(feature, "requisito", f"arquivo não encontrado: {req_rel}")
        else:
            with open(regras if os.path.exists(regras) else req_path,
                      encoding="utf-8") as fh:
                txt_req = fh.read()
            # RN DEFINIDA: linha de tabela (| **RN-01** | ...) ou cabeçalho (## RN-01).
            # Menção em prosa não conta — senão o lint cobra CT de uma regra apenas
            # citada de passagem. A forma de tabela é a que o kit prescreve no REGRAS.md.
            rns_req = set(re.findall(r"^\s*\|\s*\**(RN-\d+)\**\s*\|", txt_req, re.M))
            rns_req |= set(re.findall(r"^#+\s*\**(RN-\d+)", txt_req, re.M))
            rns_cobertas = {t for c in cenarios for t in c[2] if t.startswith("RN-")}
            # escape legítimo: @sem-caso:<motivo> declarado na matriz
            sem_caso = set(re.findall(r"@sem-caso:(RN-\d+)", txt_matriz))
            for rn in sorted(rns_req - rns_cobertas - sem_caso):
                erro(feature, "cobertura",
                     f"{rn} não tem nenhum CT (use @sem-caso:{rn} na matriz, "
                     f"com motivo, se for intencional)")

            # --- obsolescência: requisito mudou, casos não foram revisados --- #
            with open(req_path, "rb") as fh:
                h_atual = hashlib.sha256(fh.read()).hexdigest()[:12]
            h_matriz = meta.get("hash")
            if not h_matriz:
                aviso(feature, "obsolescencia",
                      "MATRIZ.md sem hash do requisito — adicione o cabeçalho qa-lint")
            elif h_matriz == "PENDENTE":
                aviso(feature, "obsolescencia",
                      "MATRIZ.md com hash=PENDENTE (feature importada). "
                      "Rode --fix-hash depois de revisar os casos.")
            elif h_atual != h_matriz:
                erro(feature, "obsolescencia",
                     f"o requisito mudou (hash {h_matriz} → {h_atual}). "
                     f"Revise os casos das RN afetadas e rode --fix-hash para confirmar")

    # --- teto de e2e: max(1, 10%) ------------------------------------------ #
    n_e2e = sum(1 for c in cenarios if any(t == "camada:e2e" for t in c[2]))
    teto = max(1, round(len(cenarios) * 0.10))
    if n_e2e > teto:
        erro(feature, "teto-e2e",
             f"{n_e2e} cenários em @camada:e2e; o teto é {teto} "
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
        with open(req_path, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()[:12]
        novo = re.sub(r"(<!--\s*qa-lint:[^>]*?hash=)\S+", r"\g<1>" + h, txt)
        with open(matriz, "w", encoding="utf-8") as fh:
            fh.write(novo)
        print(f"hash atualizado: {os.path.basename(dirpath)} -> {h}")


def checa_runs(automacao_por_ct=None, nao_aprovados=None):
    """Execução oficial não pode ter sido feita por agente.

    Agente explora, autora e diagnostica; a regressão é código determinístico.
    Resultado de agente vive em test/sessoes/, nunca em test/runs/.

    Também reconcilia os dois lados da automação, que até aqui nunca se
    falavam: a **conversão** (painel e relatório) é lida da TAG
    `@automacao:feito`, e a **execução** vem do JUnit do runner. Um CT que o CI
    roda toda noite mas que a matriz ainda chama de `pendente` faz o painel
    exibir conversão menor que a real — e ninguém desconfia, porque os dois
    números vêm de fontes diferentes e nenhum está obviamente errado.
    """
    import json
    automacao_por_ct = automacao_por_ct or {}
    nao_aprovados = nao_aprovados or set()
    # status que significam "alguem executou"; nao_executado e nao_aplicavel nao
    EXECUTADO = {"passou", "falhou", "bloqueado"}
    rodados_por_ci = set()
    for p in sorted(glob.glob(os.path.join(ROOT, "test", "runs", "**", "*.json"),
                              recursive=True)):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
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
            if por == "ci":
                rodados_por_ci.add(cid)
            # PORTAO 2 no limite da execucao. O glossario e o PROCESSO.md
            # prometem que "@nao-aprovado fica fora da suite oficial" e
            # atribuem isso a "hook + lint" -- e o lint nao cobria este ponto.
            # Cenario @premissa @nao-aprovado marcado 'passou' passava limpo, o
            # painel contava como coberto e o relatorio do PMO anunciava
            # aprovacao sobre comportamento SUPOSTO.
            if cid in nao_aprovados and (info or {}).get("status") in EXECUTADO:
                erro("runs", "execucao-nao-aprovada",
                     f"{nome}: {cid} tem status '{info['status']}' mas o cenário "
                     f"não passou pelo portão 2 (sem @aprovado-por:). Resultado "
                     f"de cenário não aprovado vira cobertura no painel e taxa "
                     f"de aprovação no relatório do PMO — sobre comportamento "
                     f"que ninguém confirmou. Aprove o cenário ou remova-o da "
                     f"rodada")

    for cid in sorted(rodados_por_ci):
        auto = automacao_por_ct.get(cid)
        if auto is not None and not auto.startswith("feito"):
            aviso("runs", "conversao-desatualizada",
                  f"{cid} foi executado por 'ci' mas está @automacao:{auto} — "
                  f"o painel e o relatório contam esse caso como NÃO "
                  f"automatizado. Marque @automacao:feito:<PR>")


# --------------------------------------------------------------------------- #
# Invariante 5: "quando o sistema diverge da regra, PARE".
#
# Ate aqui os guarda-corpos paravam no Gherkin. O .feature era policiado por uma
# duzia de regras; a spec -- onde a assercao de fato mora -- so era lida pelo
# NOME do arquivo, para provar que @automacao:feito nao era fantasma. O cenario
# podia dizer "entao o total deve ser 90,00" e a spec dizer
# expect(total).toBeTruthy(): verde para sempre, e nenhum PR reprovava.
#
# Nao da para saber mecanicamente se um 90.00 veio da regra ou da tela -- isso
# segue humano, e e para isso que existe @observado:/@premissa na matriz. Da
# para pegar a classe MECANICA, que e a que um agente produz sob pressao de
# fazer passar. Os quatro tapa-buracos estao nomeados no CLAUDE.md e os quatro
# sao grepaveis: afrouxar a assercao, aceitar dois status, pular o teste,
# aumentar o timeout.

TETO_TIMEOUT_MS = 30000

RE_CT_SPEC = re.compile(r"\bCT-\d+\b")

# declaracao de teste: Playwright/Jest/Vitest/Mocha/Cypress e pytest/unittest
RE_DECL_TESTE = re.compile(
    r"^\s*(?:async\s+)?(?:export\s+)?(?:await\s+)?"
    r"(?:[xf]?(?:test|it|describe|context|suite)\s*[.(]"
    r"|(?:async\s+)?def\s+test\w*\s*\()")

RE_DESLIGADA = re.compile(
    r"\b(?:test|it|describe|context|suite)\s*\.\s*(skip|only|fixme|failing)\b"
    r"|^\s*x(?:it|describe|test)\s*\("
    r"|@pytest\.mark\.(skip|skipif|xfail)"
    r"|@unittest\.(skip)")

RE_ASSERCAO = re.compile(r"\bexpect\s*\(|^\s*assert\b|\.should\b|\bassert[A-Z]\w*\s*\(")

# assercao que passa com quase qualquer coisa. toBeOK() do Playwright aceita a
# faixa 200-299 inteira, entao pertence a esta lista e nao a das fortes.
RE_ASSERCAO_FRACA = re.compile(
    r"\.\s*(?:toBeTruthy|toBeFalsy|toBeDefined|toBeOK)\s*\("
    r"|\.\s*not\s*\.\s*(?:toBeNull|toBeUndefined)\s*\("
    r"|\.\s*toBeGreaterThanOrEqual\s*\(\s*0\s*\)"
    r"|^assert\s+[\w.\[\]()]+$")

# colecao literal com dois ou mais codigos HTTP, numa linha que fala de status
RE_STATUS_AMBIGUO = re.compile(r"[\[\(]\s*[1-5]\d\d\s*(?:,\s*[1-5]\d\d\s*)+[\]\)]")

RE_ESPERA_CEGA = re.compile(r"\b(?:waitForTimeout|time\.sleep)\s*\(|\bsleep\s*\(\s*\d")

RE_TIMEOUT = re.compile(
    r"\b(?:timeout|setDefaultTimeout|setDefaultNavigationTimeout|setTimeout)\b"
    r"\s*[:(=]\s*(\d+)")


def _blocos_de_teste(linhas):
    """[(numero_da_linha_inicial, [linhas])] — um bloco por declaração de teste.

    O bloco começa nos decoradores, não no `def`: em pytest quem desliga o teste
    é a linha DE CIMA (`@pytest.mark.skip`), e cortar no `def` deixava o skip
    fora do bloco que ele desliga.
    """
    marcos = []
    for n, linha in enumerate(linhas):
        if not RE_DECL_TESTE.match(linha):
            continue
        ini = n
        while ini > 0 and linhas[ini - 1].lstrip().startswith("@"):
            ini -= 1
        marcos.append(ini if not marcos or ini > marcos[-1] else n)
    if not marcos:
        return []
    limites = marcos + [len(linhas)]
    return [(marcos[i] + 1, linhas[marcos[i]:limites[i + 1]])
            for i in range(len(marcos))]


def _ct_do_bloco(corpo, linhas, inicio):
    """CT que o bloco afirma provar.

    Normalmente está no próprio título -- test('CT-014 ...'). Quando não está, o
    describe de cima é quem carrega, então olhamos para trás.
    """
    m = RE_CT_SPEC.search("\n".join(corpo))
    if m:
        return m.group(0)
    for linha in reversed(linhas[:inicio - 1]):
        m = RE_CT_SPEC.search(linha)
        if m:
            return m.group(0)
    return None


def checa_specs(automacao_por_ct=None, nao_aprovados=None, base=None):
    """A spec prova o cenário, ou só finge que prova?

    Só olha bloco de teste que cita um CT conhecido: arquivo de apoio, fixture e
    page object não afirmam provar caso nenhum. Um CT que ainda não foi aprovado
    pode estar legitimamente desligado -- é o cenário travado por lacuna aberta,
    que o kit manda marcar @nao-aprovado -- então skip nele não é violação.
    """
    automacao_por_ct = automacao_por_ct or {}
    nao_aprovados = nao_aprovados or set()
    if not automacao_por_ct:
        return                      # nenhum caso: nada que a spec possa provar

    for rel, txt in specs_do_repo(base):
        # atalho, nao semantica: quem de fato limita o escopo e a atribuicao de
        # CT logo abaixo. Sem isto o resultado e o mesmo, so que depois de
        # quebrar em blocos toda fixture e todo page object do repositorio.
        if not RE_CT_SPEC.search(txt):
            continue
        linhas = txt.splitlines()
        for inicio, corpo in _blocos_de_teste(linhas):
            cid = _ct_do_bloco(corpo, linhas, inicio)
            if cid not in automacao_por_ct:
                continue
            visto = set()

            for n, linha in enumerate(corpo, inicio):
                onde = f"{rel}:{n}"

                m = RE_DESLIGADA.search(linha)
                if m and "desligada" not in visto:
                    visto.add("desligada")
                    modo = next((g for g in m.groups() if g), "skip")
                    if modo == "only":
                        erro("specs", "spec-desligada",
                             f"{onde}: {cid} usa .only — o CI roda esse teste e "
                             f"ignora todos os outros, e a rodada sai verde com "
                             f"a suíte inteira sem executar")
                    elif cid not in nao_aprovados:
                        erro("specs", "spec-desligada",
                             f"{onde}: {cid} está desligado por .{modo} mas o "
                             f"caso está aprovado. Cenário que não pode rodar se "
                             f"marca @nao-aprovado no .feature, com a lacuna "
                             f"aberta em LACUNAS.md — desligar só na spec some "
                             f"do relatório como se estivesse coberto")

                if RE_STATUS_AMBIGUO.search(linha) and "status" in linha.lower() \
                        and "status" not in visto:
                    visto.add("status")
                    erro("specs", "spec-status-ambiguo",
                         f"{onde}: {cid} aceita mais de um status HTTP. A regra "
                         f"define um; aceitar dois é afrouxar a asserção até ela "
                         f"passar. Se o requisito realmente não decide, é "
                         f"@premissa + entrada em LACUNAS.md")

                if RE_ESPERA_CEGA.search(linha) and "espera" not in visto:
                    visto.add("espera")
                    aviso("specs", "spec-espera-cega",
                          f"{onde}: {cid} tem espera fixa. Ela é curta demais no "
                          f"CI lento e longa demais sempre — espere pela "
                          f"condição, não pelo relógio")

                m = RE_TIMEOUT.search(linha)
                if m and int(m.group(1)) > TETO_TIMEOUT_MS and "timeout" not in visto:
                    visto.add("timeout")
                    aviso("specs", "spec-timeout-alto",
                          f"{onde}: {cid} com timeout de {int(m.group(1)) // 1000}s "
                          f"(teto {TETO_TIMEOUT_MS // 1000}s). Aumentar timeout "
                          f"para o teste passar esconde lentidão que é defeito")

            # Duas severidades, porque os dois casos sao diferentes.
            #
            # TODAS fracas: o caso nao prova nada e sai verde para sempre. Erro,
            # sem margem.
            #
            # ALGUMAS fracas: pode ser legitimo -- toBeTruthy como guarda antes
            # de destrinchar o corpo. Mas e tambem a forma da falha mais comum
            # de verdade: o status vai forte (toBe(200)) e o VALOR, que e o que
            # a regra define, vai frouxo. O lint nao tem como saber qual das
            # assercoes prova a RN, entao aponta a linha e devolve a decisao a
            # quem aprova. Em spec bem escrita isso e silencioso: o exemplo do
            # kit tem zero.
            assercoes = [(n, l.strip()) for n, l in enumerate(corpo, inicio)
                         if RE_ASSERCAO.search(l)]
            fracas = [(n, a) for n, a in assercoes if RE_ASSERCAO_FRACA.search(a)]
            if assercoes and len(fracas) == len(assercoes):
                erro("specs", "spec-sem-assercao-forte",
                     f"{rel}:{inicio}: {cid} não tem nenhuma asserção forte — "
                     f"as {len(assercoes)} são do tipo que passa com quase "
                     f"qualquer valor ({assercoes[0][1][:48]}). O valor esperado "
                     f"vem da regra, calculado à mão; se ele não é conhecido, o "
                     f"cenário é @premissa, não asserção frouxa")
            elif fracas:
                n, a = fracas[0]
                aviso("specs", "spec-assercao-fraca",
                      f"{rel}:{n}: {cid} tem asserção que passa com quase "
                      f"qualquer valor ({a[:48]}). Se for guarda de passo "
                      f"intermediário, tudo bem; se for ela que prova a regra, "
                      f"o cenário está verde sem provar nada")


def docs_do_kit():
    """Todo .md do kit: skills, referências e docs/."""
    out = sorted(glob.glob(os.path.join(SKILLS, "**", "*.md"), recursive=True))
    out += sorted(glob.glob(os.path.join(ROOT, "docs", "*.md")))
    for nome in ("README.md", "CLAUDE.md", "CHANGELOG.md"):
        p = os.path.join(ROOT, nome)
        if os.path.exists(p):
            out.append(p)
    return out


def check_kit():
    """Valida o próprio kit: comandos citados, caminhos e links entre documentos.

    Skill é código, não documento que alguém edita direto na main. Nada verificava as
    junções entre elas — foi assim que quatro ponteiros para skills inexistentes
    sobreviveram, e que uma skill pôde prometer artefatos que nunca produzia.

    A checagem de link markdown foi acrescentada depois de quatro ponteiros para
    `docs/CAMADAS-E-AUTOMACAO.md` e `docs/TESTE-LIMPO.md`, que nunca existiram:
    validar só `/comando` e `.claude/skills/` deixava passar exatamente o tipo
    de erro que a regra existia para pegar.
    """
    nomes = {os.path.basename(d) for d in glob.glob(os.path.join(SKILLS, "*"))
             if os.path.isdir(d)}
    if not nomes:
        print("qa-lint: nenhuma skill em .claude/skills/")
        return
    scripts = {os.path.basename(p)
               for p in glob.glob(os.path.join(ROOT, "test", "scripts", "*.py"))}

    for path in docs_do_kit():
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        with open(path, encoding="utf-8") as fh:
            txt = fh.read()
        # exige hifen: todo nome de skill tem um (qa-intake, design-casos-teste).
        # Sem isso o padrao casava rota HTTP citada em documento -- `/signin`,
        # `/tasks/save` -- e acusava skill inexistente.
        # entre crases -- `/qa-intake`
        citados = set(re.findall(r"`/([a-z][\w]*-[\w-]+)`", txt))
        # e em titulo markdown -- "# /qa-testar — execução". Este caso escapava,
        # e foi assim que a qa-execucao passou a se anunciar, no proprio H1,
        # como um comando que nao existe. Quem lesse a skill digitaria /qa-testar
        # e nao aconteceria nada.
        citados |= set(re.findall(r"^#+\s*/([a-z][\w]*-[\w-]+)", txt, re.M))
        for citado in sorted(citados):
            if citado not in nomes:
                erro("kit", "comando-inexistente",
                     f"{rel} cita /{citado}, que não é uma skill em .claude/skills/")
        for ref in sorted(set(re.findall(r"\.claude/skills/([a-z][\w-]+)/", txt))):
            if ref not in nomes:
                erro("kit", "caminho-inexistente",
                     f"{rel} aponta para .claude/skills/{ref}/, que não existe")
        for ref in sorted(set(re.findall(r"test/scripts/(\w+\.py)", txt))):
            if ref not in scripts:
                erro("kit", "script-inexistente",
                     f"{rel} cita test/scripts/{ref}, que não existe")
        # links markdown relativos
        base = os.path.dirname(path)
        for alvo in sorted(set(re.findall(r"\]\(([^)\s#]+)\)", txt))):
            if alvo.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if "<" in alvo or ">" in alvo:      # placeholder de template
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base, alvo))):
                erro("kit", "link-quebrado", f"{rel} aponta para {alvo}, que não existe")


def cmd_proximo_ct():
    """Maior CT-NNN do repositório, +1. Alocação global, ID nunca reciclado."""
    maior = 0
    for p in glob.glob(os.path.join(CASES, "**", "*"), recursive=True):
        if not p.endswith((".feature", ".md")):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
        except OSError:
            continue
        for n in re.findall(r"\bCT-(\d+)\b", txt):
            maior = max(maior, int(n))
    print(f"CT-{maior + 1:03d}")


def main():
    ap = argparse.ArgumentParser(description="Consistência do sistema de QA")
    ap.add_argument("--feature", help="valida apenas uma feature")
    # a raiz é a pasta que CONTÉM as features, não a pasta de cima: o exemplo
    # features moram em <raiz>/cases/<feature>/, então a raiz a passar é
    # <raiz>/cases. Passar a pasta de cima acusa cases/ e requisitos/ de serem
    # features sem .feature — dois erros falsos no primeiro comando que se tenta.
    ap.add_argument("--dir", metavar="CAMINHO",
                    help="valida outra raiz de casos (ex.: piloto/cases)")
    ap.add_argument("--fix-hash", action="store_true",
                    help="regrava o hash do requisito após revisão dos casos")
    ap.add_argument("--check-kit", action="store_true",
                    help="valida o próprio kit: comandos, caminhos e links")
    ap.add_argument("--proximo-ct", action="store_true",
                    help="imprime o próximo @CT-XXX livre (alocação global)")
    args = ap.parse_args()

    if args.proximo_ct:
        cmd_proximo_ct()
        return

    if args.fix_hash:
        fix_hash()
        return

    if args.check_kit:
        check_kit()
        print("qa-lint --check-kit\n")
        for e in erros:
            print(f"  ERRO   {e}")
        print()
        if erros:
            print(f"FALHOU: {len(erros)} violação(ões)")
            sys.exit(1)
        print("OK: referências entre skills consistentes")
        return

    raiz = os.path.normpath(os.path.join(ROOT, args.dir)) if args.dir else CASES
    rel_raiz = os.path.relpath(raiz, ROOT).replace("\\", "/")
    dirs = [d for d in sorted(glob.glob(os.path.join(raiz, "*"))) if os.path.isdir(d)]
    if args.feature:
        dirs = [d for d in dirs if os.path.basename(d) == args.feature]
        if not dirs:
            sys.exit(f"erro: feature '{args.feature}' não existe em {rel_raiz}/")
    if not dirs:
        # kit recem-clonado: nao ha o que verificar, e isso nao e erro
        print(f"qa-lint: nenhuma feature em {rel_raiz}/ ainda.\n"
              "         Comece com /qa-intake para extrair as regras da sua feature,\n"
              "         ou com qa_import_qase.py se você está migrando do Qase.")
        return

    total, onde, automacao_por_ct, nao_aprovados = 0, {}, {}, set()
    for d in dirs:
        c = checa_feature(d) or []
        total += len(c)
        for cid, _titulo, tags, _arq, _ln in c:
            automacao_por_ct[cid] = next(
                (t.split(":", 1)[1] for t in tags if t.startswith("automacao:")),
                "pendente")
            if not any(t.startswith("aprovado-por:") for t in tags):
                nao_aprovados.add(cid)
        # unicidade GLOBAL do ID. A checagem por pasta nao pega o caso real:
        # dois QAs em branches diferentes gerando CT-001 na mesma semana. O
        # glossario promete "ID nunca e reciclado" -- aqui isso vira mecanismo.
        for cid, _titulo, _tags, arq, ln in c:
            local = f"{os.path.basename(d)}/{arq}:{ln}"
            if cid in onde:
                erro("global", "id-duplicado",
                     f"{cid} existe em {onde[cid]} e em {local} — "
                     f"ID é global; use --proximo-ct para alocar o próximo livre")
            else:
                onde[cid] = local
    checa_runs(automacao_por_ct, nao_aprovados)
    checa_specs(automacao_por_ct, nao_aprovados, base_de(raiz))

    migrados = sum(1 for a in avisos if "migracao" in a)
    print(f"qa-lint: {len(dirs)} feature(s), {total} cenário(s)"
          + (f", {migrados} aguardando regra (migração)" if migrados else "") + "\n")
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
