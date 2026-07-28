#!/usr/bin/env python3
"""
Cadastra bugs na coluna "BUGs" do kanban do AP (Atlante Project), seguindo o
modelo estrutural de QA. Ver docs/PADRAO-BUG-WMS.md.

REGRA DO PROCESSO: nada e cadastrado sem confirmacao do QA. O padrao e mostrar
o ticket montado e perguntar. Use --yes apenas quando o QA ja aprovou.

Usa os endpoints internos do AP (/tasks/save) porque o plugin REST API desta
instalacao e somente leitura. Ver docs/PADRAO-BUG-WMS.md.

Uso:
    python3 test/scripts/rise_bug.py --file bugs/imagem-produto.json
    python3 test/scripts/rise_bug.py --file bugs/*.json --yes
    python3 test/scripts/rise_bug.py --template > bugs/novo.json
    python3 test/scripts/rise_bug.py --delete 3496

    # fecha o laco: grava o numero do bug no caso da rodada
    python3 test/scripts/rise_bug.py --file bugs/ct-005.json --rodada 3

Requer no .env DA RAIZ: RISE_BASE_URL, RISE_USER, RISE_PASSWORD
"""

import argparse
import datetime
import glob
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- padrao do AP (ver docs/PADRAO-BUG-WMS.md) ---
DEFAULT_PROJECT = 9    # WMS
BUGS_COLUMN = 5        # coluna "BUGs" -- global, vale em qualquer projeto
DEFAULT_ASSIGNEE = 12  # Gabriel Logan (QA Lead)

# O AP so tem 4 prioridades. "Media" do modelo de QA nao existe la:
# a escala do AP e lida como trivial / normal / grave / impeditivo.
PRIORITY_IDS = {"baixa": 1, "alta": 2, "critica": 3, "bloqueada": 4}
PRIORITY_NAMES = {1: "Baixa", 2: "Alta", 3: "Critica", 4: "Bloqueada"}
PRIORITY_ALIASES = {
    "media": "alta",       # Media -> Alta (Critica/Bloqueada ocupam o topo)
    "médía": "alta", "média": "alta", "medium": "alta",
    "critical": "critica", "crítica": "critica",
    "blocker": "bloqueada", "bloqueador": "bloqueada",
    "low": "baixa", "high": "alta",
}

EVIDENCE_DIR = "test/image"

# Severidade no padrao Atlante (S1..S4) -- eixo diferente da prioridade do AP.
# Ver docs/GLOSSARIO.md secao 6.
SEV_ALIAS = {"critico": "S1", "crítico": "S1", "critica": "S1", "crítica": "S1",
             "alto": "S2", "alta": "S2", "medio": "S3", "médio": "S3",
             "media": "S3", "média": "S3", "baixo": "S4", "baixa": "S4",
             "bloqueada": "S1", "bloqueador": "S1"}


class RiseError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# modelo do bug
# --------------------------------------------------------------------------- #

TEMPLATE = {
    "escopo": "Checkout | /api/produtos",
    "resumo": "Imagem do produto não carrega na página de compra",
    "descricao": "Ao tentar comprar um produto, a imagem associada não é exibida, "
                 "o que prejudica a experiência do usuário.",
    "comportamento_atual": "A imagem do produto não é carregada ao comprar um produto.",
    "resultado_esperado": "A imagem do produto deve ser carregada e exibida corretamente.",
    "passos": [
        "Abra o navegador Google Chrome.",
        "Navegue até o site da aplicação (www.exemploapp.com).",
        "Faça login em sua conta.",
        "Escolha um produto e clique em Comprar.",
        "Observe a falta de carregamento da imagem.",
    ],
    "ambiente": {
        "aplicacao": "ExemploApp",
        "versao": "sprint 1",
        "navegador": "Google Chrome",
        "dispositivo": "Dell G15 / Windows 11",
    },
    "anexos": ["bug-comprador.png"],
    # o nivel S1..S4 e obrigatorio no inicio da string -- e o que alimenta a
    # tabela de defeitos do relatorio do PMO. Ver docs/GLOSSARIO.md secao 6.
    "severidade": "S3 — funcionalidade utilizável, mas com perda de informação ao usuário.",
    "prioridade": "Média",
    "caso_de_teste": "CT-005",
    "impacto": "Impede o usuário de visualizar a imagem do produto, o que pode gerar "
               "desistência de compra e perda de receita.",
    "project_id": DEFAULT_PROJECT,
    "assigned_to": DEFAULT_ASSIGNEE,
}

# rotulos exibidos para as chaves de "ambiente" (a chave fica sem acento no JSON)
AMBIENTE_LABELS = {
    "aplicacao": "Aplicação", "versao": "Versão", "navegador": "Navegador",
    "dispositivo": "Dispositivo", "so": "SO", "ambiente": "Ambiente",
    "url": "URL", "banco": "Banco de dados",
}

REQUIRED = ["escopo", "resumo", "descricao", "comportamento_atual",
            "resultado_esperado", "passos", "severidade", "prioridade", "impacto"]


def resolve_priority(value):
    """Normaliza a prioridade do modelo de QA para os 4 ids do AP."""
    key = str(value).strip().lower()
    key = PRIORITY_ALIASES.get(key, key)
    if key not in PRIORITY_IDS:
        raise RiseError(
            f"prioridade '{value}' invalida. Use: Baixa, Alta, Critica, Bloqueada "
            f"(Media e mapeada para Alta)")
    return PRIORITY_IDS[key]


def evidence_paths(anexos, when=None):
    """Monta os caminhos datados das evidencias: test/image/DD-MM-AAAA/arquivo."""
    day = (when or datetime.date.today()).strftime("%d-%m-%Y")
    out = []
    for a in anexos or []:
        out.append(a if "/" in a else f"{EVIDENCE_DIR}/{day}/{a}")
    return out


def build_title(bug):
    return f"Bug:[{bug['escopo']}] {bug['resumo']}"


def build_description(bug):
    """Renderiza o modelo estrutural em HTML (o AP aceita HTML na descricao)."""
    e = html.escape

    def section(title, body):
        return f"<h4>{e(title)}</h4>{body}"

    amb = bug.get("ambiente") or {}
    amb_items = "".join(
        f"<li><b>{e(AMBIENTE_LABELS.get(k, k.capitalize()))}:</b> {e(str(v))}</li>"
        for k, v in amb.items() if v)

    steps = "".join(f"<li>{e(str(p))}</li>" for p in bug.get("passos") or [])
    anexos = evidence_paths(bug.get("anexos"))
    anexos_html = ("".join(f"<li><code>{e(a)}</code></li>" for a in anexos)
                   if anexos else "<li><i>sem anexos</i></li>")

    prio_id = resolve_priority(bug["prioridade"])
    prio_txt = PRIORITY_NAMES[prio_id]
    if str(bug["prioridade"]).strip().lower() in ("media", "média", "medium"):
        prio_txt += " <i>(classificada como Média pelo QA; o AP não possui esse nível)</i>"

    parts = [
        section("Descrição do Problema", f"<p>{e(bug['descricao'])}</p>"),
        section("Comportamento Atual", f"<p>{e(bug['comportamento_atual'])}</p>"),
        section("Resultado Esperado", f"<p>{e(bug['resultado_esperado'])}</p>"),
        section("Passos para Reproduzir", f"<ol>{steps}</ol>"),
        section("Ambiente e Tecnologias", f"<ul>{amb_items}</ul>"),
        section("Anexos", f"<ul>{anexos_html}</ul>"),
        section("Severidade", f"<p>{e(bug['severidade'])}</p>"),
        section("Prioridade", f"<p>{prio_txt}</p>"),
        section("Impacto", f"<p>{e(bug['impacto'])}</p>"),
    ]
    return "".join(parts)


def render_preview(bug):
    """Versao legivel no terminal, para o QA conferir antes de cadastrar."""
    prio_id = resolve_priority(bug["prioridade"])
    L = []
    L.append("=" * 72)
    L.append(build_title(bug))
    L.append("=" * 72)
    L.append(f"projeto ....: {bug.get('project_id', DEFAULT_PROJECT)}")
    L.append(f"coluna .....: BUGs (status_id={BUGS_COLUMN})")
    pid = bug.get("project_id", DEFAULT_PROJECT)
    membros = {uid: nome for uid, nome, _c in project_members(pid)}
    assignee = str(bug.get("assigned_to", DEFAULT_ASSIGNEE))
    L.append(f"responsavel : {assignee}"
             + (f" = {membros[assignee]}" if assignee in membros
                else "  [ATENCAO: nao e membro deste projeto]" if membros else ""))
    colab = resolve_collaborators(bug, pid)
    colab_ids = [c for c in colab.split(",") if c]
    if colab_ids:
        nomes = ", ".join(membros.get(c, c) for c in colab_ids)
        L.append(f"colaborad. .: {len(colab_ids)} membro(s) -- {nomes}")
    else:
        L.append("colaborad. .: (nenhum -- lista indisponivel ou vazia)")
    orig = str(bug["prioridade"]).strip()
    mapped = PRIORITY_NAMES[prio_id]
    L.append(f"prioridade .: {mapped}" + (f"   [informada: {orig}]" if orig.lower() != mapped.lower() else ""))
    # O nivel S1..S4 decide o criterio de saida "S1 em aberto = 0", que
    # interrompe o ciclo. Quando ele veio de apelido ("alta" -> S2) em vez de
    # ter sido declarado, o script escolheu por alguem -- e severidade e
    # decisao do QA, nunca do script. Aparecer no preview e o minimo: o QA ve
    # o que vai ser gravado antes de confirmar.
    L.append(f"severidade .: {bug['severidade']}"
             + ("" if nivel_declarado(bug)
                else f"   -> {severidade_nivel(bug)} INFERIDO do texto "
                     f"(o nivel nao foi declarado; escreva 'S2 — ...' "
                     f"para decidir voce)"))
    L.append("-" * 72)
    L.append("Descrição do Problema")
    L.append(f"  {bug['descricao']}")
    L.append("Comportamento Atual")
    L.append(f"  {bug['comportamento_atual']}")
    L.append("Resultado Esperado")
    L.append(f"  {bug['resultado_esperado']}")
    L.append("Passos para Reproduzir")
    for i, p in enumerate(bug.get("passos") or [], 1):
        L.append(f"  {i}. {p}")
    amb = bug.get("ambiente") or {}
    if amb:
        L.append("Ambiente e Tecnologias")
        for k, v in amb.items():
            if v:
                L.append(f"  - {AMBIENTE_LABELS.get(k, k.capitalize())}: {v}")
    anexos = evidence_paths(bug.get("anexos"))
    L.append("Anexos")
    for a in anexos or ["(nenhum)"]:
        exists = "" if not a.startswith(EVIDENCE_DIR) else (
            "  [OK]" if os.path.exists(a) else "  [ARQUIVO NAO ENCONTRADO]")
        L.append(f"  - {a}{exists}")
    L.append("Impacto")
    L.append(f"  {bug['impacto']}")
    L.append("=" * 72)
    return "\n".join(L)


def nivel_declarado(bug):
    """O QA escreveu 'S1'..'S4' explicitamente, ou o nivel foi inferido?

    Existe porque a skill qa-defeito prometia que o script RECUSA severidade sem
    nivel, e ele na verdade mapeia "alta" -> S2 em silencio. Mapear e util na
    migracao; decidir calado nao e -- severidade e do QA, e S1 contra S2 e a
    diferenca entre interromper o ciclo e liberar a release.
    """
    v = str(bug.get("severidade_nivel") or bug.get("severidade") or "")
    return bool(re.search(r"\bS[1-4]\b", v, re.I))


def severidade_nivel(bug):
    """Extrai S1..S4 do campo severidade. None se nao for classificavel.

    Mesma leitura do qa_report.py -- e o numero que alimenta a tabela da secao 4
    do relatorio do PMO e o criterio de saida 'S1 em aberto = 0'.
    """
    v = str(bug.get("severidade_nivel") or bug.get("severidade") or "")
    m = re.search(r"\bS([1-4])\b", v, re.I)
    if m:
        return "S" + m.group(1)
    chave = v.strip().lower().split()[0].strip(":—-,.") if v.strip() else ""
    return SEV_ALIAS.get(chave)


def validate(bug):
    faltando = [f for f in REQUIRED if not bug.get(f)]
    if faltando:
        raise RiseError(f"campos obrigatorios ausentes: {', '.join(faltando)}")
    resolve_priority(bug["prioridade"])
    # severidade sem nivel faz a tabela da secao 4 do relatorio sair zerada e o
    # parecer subestimar a gravidade. Recusar aqui e proposital.
    if not severidade_nivel(bug):
        raise RiseError(
            f"severidade '{bug['severidade']}' nao declara nivel S1..S4. "
            f"Escreva 'S2 — <descricao>'. Sem isso o relatorio do PMO conta "
            f"este defeito como sem gravidade.")


# --------------------------------------------------------------------------- #
# cliente do AP
# --------------------------------------------------------------------------- #

class Rise:
    def __init__(self, base, user, password):
        self.base = base.rstrip("/")
        self.user = user
        self.password = password
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar()))
        self._logged = False

    def _post(self, path, data):
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(
            self.base + path, data=body,
            headers={"X-Requested-With": "XMLHttpRequest",
                     "Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "ap-qa-bot/1.0"})
        with self.opener.open(req, timeout=45) as r:
            return r.read().decode("utf-8", "replace")

    def login(self):
        self.opener.open(self.base + "/signin", timeout=45).read()
        body = urllib.parse.urlencode(
            {"email": self.user, "password": self.password, "redirect": ""}).encode()
        req = urllib.request.Request(
            self.base + "/signin/authenticate", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "ap-qa-bot/1.0"})
        with self.opener.open(req, timeout=45) as r:
            final = r.geturl()
        if final.rstrip("/").endswith("/signin"):
            raise RiseError("credenciais invalidas (RISE_USER / RISE_PASSWORD)")
        self._logged = True
        return self

    def create_bug(self, bug):
        validate(bug)
        if not self._logged:
            self.login()
        raw = self._post("/tasks/save", {
            "id": "", "add_type": "", "client_id": "", "ticket_id": "",
            "project_id": bug.get("project_id", DEFAULT_PROJECT),
            "title": build_title(bug),
            "description": build_description(bug),
            "context": "project",
            "points": bug.get("points", 1),
            "milestone_id": "",
            "assigned_to": bug.get("assigned_to", DEFAULT_ASSIGNEE),
            "collaborators": resolve_collaborators(
                bug, bug.get("project_id", DEFAULT_PROJECT)),
            "status_id": BUGS_COLUMN,
            "priority_id": resolve_priority(bug["prioridade"]),
            "labels": "", "start_date": "", "start_time": "",
            "deadline": bug.get("deadline", ""), "end_time": "",
        })
        # atencao: o AP responde HTTP 200 mesmo no erro -- validar o corpo
        try:
            res = json.loads(raw)
        except ValueError:
            raise RiseError(f"resposta inesperada (sessao expirada?): {raw[:200]}")
        if not res.get("success"):
            raise RiseError(f"cadastro falhou: {res.get('message') or raw[:300]}")
        m = re.search(r'data-id=\\?"(\d+)\\?"', json.dumps(res.get("data", "")))
        return int(m.group(1)) if m else None

    def delete(self, task_id):
        if not self._logged:
            self.login()
        res = json.loads(self._post("/tasks/delete", {"id": task_id}))
        if not res.get("success"):
            raise RiseError(f"delete falhou: {res.get('message')}")
        return True


# --------------------------------------------------------------------------- #

def confirm(prompt="Cadastrar este bug no AP? [s/N] "):
    try:
        return input(prompt).strip().lower() in ("s", "sim", "y", "yes")
    except EOFError:
        return False


_projects_cache = None


def list_projects():
    """Lista os projetos do AP via REST API (leitura). {id: titulo}.

    Usa RISE_AUTH_TOKEN. Se nao houver token ou a chamada falhar, devolve {} --
    o cadastro continua funcionando, so perde a validacao e o nome do projeto.
    """
    global _projects_cache
    if _projects_cache is not None:
        return _projects_cache
    _projects_cache = {}
    base, token = os.environ.get("RISE_BASE_URL"), os.environ.get("RISE_AUTH_TOKEN")
    if not (base and token):
        return _projects_cache
    try:
        req = urllib.request.Request(base.rstrip("/") + "/api/projects",
                                     headers={"authtoken": token})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        # atencao: o AP responde HTTP 200 mesmo no erro -- checar o formato
        if isinstance(data, list):
            _projects_cache = {str(p["id"]): p.get("title", "") for p in data}
    except Exception:
        pass
    return _projects_cache


_members_cache = None


def _api_get(path):
    """GET na REST API (leitura) usando authtoken. None se indisponivel."""
    base, token = os.environ.get("RISE_BASE_URL"), os.environ.get("RISE_AUTH_TOKEN")
    if not (base and token):
        return None
    try:
        req = urllib.request.Request(base.rstrip("/") + path, headers={"authtoken": token})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def project_members(project_id):
    """Membros de um projeto: [(user_id, nome, cargo)]. Vazio se indisponivel."""
    global _members_cache
    if _members_cache is None:
        data = _api_get("/api/project_members")
        # atencao: o AP responde HTTP 200 mesmo no erro -- checar o formato
        _members_cache = data if isinstance(data, list) else []
    out = []
    for m in _members_cache:
        if str(m.get("project_id")) == str(project_id):
            out.append((str(m.get("user_id")),
                        (m.get("member_name") or "").strip(),
                        m.get("job_title") or ""))
    return out


def resolve_collaborators(bug, project_id):
    """'all' (padrao) => todos os membros do projeto, menos o responsavel."""
    value = bug.get("collaborators", "all")
    assignee = str(bug.get("assigned_to", DEFAULT_ASSIGNEE))
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    if str(value).strip().lower() not in ("all", "todos"):
        return str(value)
    ids = [uid for uid, _n, _c in project_members(project_id) if uid != assignee]
    return ",".join(ids)


def anota_na_rodada(bug, task_id, numero_rodada):
    """Grava o numero do bug no caso correspondente da rodada.

    E o elo que sempre se perde quando o passo e manual: o defeito existe no AP,
    o caso esta 'falhou' na rodada, e nada liga os dois -- entao o relatorio nao
    consegue dizer QUAL defeito reprovou QUAL caso.
    """
    ct = bug.get("caso_de_teste")
    if not (ct and task_id and numero_rodada):
        return None
    direto = os.path.join(ROOT, "test", "runs", f"rodada-{numero_rodada}.json")
    achados = ([direto] if os.path.exists(direto) else sorted(glob.glob(
        os.path.join(ROOT, "test", "runs", "manual", f"*rodada-{numero_rodada}.json"))))
    if not achados:
        print(f"   [aviso] rodada {numero_rodada} nao encontrada em test/runs/")
        return None
    caminho = achados[0]
    with open(caminho, encoding="utf-8") as fh:
        run = json.load(fh)
    caso = (run.get("resultados") or {}).get(ct)
    if caso is None:
        print(f"   [aviso] {ct} nao esta na rodada {numero_rodada}")
        return None
    caso["bug"] = int(task_id)
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(run, fh, indent=2, ensure_ascii=False)
    print(f"   {ct} da rodada {numero_rodada} agora aponta para o bug #{task_id}")
    return caminho


def ask_project(default_id):
    """Pergunta em qual projeto o bug sera aberto. Enter aceita o default."""
    projects = list_projects()
    default_id = str(default_id)
    label = projects.get(default_id, "")
    hint = f"{default_id}" + (f" = {label}" if label else "")
    while True:
        try:
            raw = input(f"Projeto para abrir o bug [{hint}] (? lista): ").strip()
        except EOFError:
            return int(default_id)
        if not raw:
            return int(default_id)
        if raw == "?":
            if not projects:
                print("  (lista indisponivel -- defina RISE_AUTH_TOKEN no .env)")
            for pid, title in sorted(projects.items(), key=lambda x: int(x[0])):
                print(f"  {pid:>3}  {title}")
            continue
        if not raw.isdigit():
            print("  informe o id numerico do projeto (ou ? para listar)")
            continue
        if projects and raw not in projects:
            print(f"  projeto {raw} nao existe no AP. Use ? para listar.")
            continue
        if projects:
            print(f"  -> {raw} = {projects[raw]}")
        return int(raw)


def load_env(path=".env"):
    """Le o .env da RAIZ do repositorio (onde o README manda cria-lo).

    Antes procurava ao lado do script, em test/scripts/.env -- que ninguem cria.
    O resultado era 'faltando no .env: RISE_USER, RISE_PASSWORD' com o arquivo
    preenchido na raiz. Mantem o cwd como segundo lugar, para quem roda de fora.
    """
    candidatos = [os.path.join(ROOT, path), os.path.join(os.getcwd(), path)]
    for full in candidatos:
        if not os.path.exists(full):
            continue
        for line in open(full, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        return full
    return None


def main():
    load_env()
    ap = argparse.ArgumentParser(description="Cadastra bugs no AP seguindo o modelo de QA")
    ap.add_argument("--file", nargs="+", help="arquivo(s) JSON com a definicao do bug")
    ap.add_argument("--template", action="store_true", help="imprime um JSON modelo e sai")
    ap.add_argument("--yes", action="store_true",
                    help="pula a confirmacao (use so quando o QA ja aprovou)")
    ap.add_argument("--dry-run", action="store_true", help="so mostra, nunca cadastra")
    ap.add_argument("--delete", type=int, metavar="ID", help="remove uma task pelo id")
    ap.add_argument("--rodada", metavar="N",
                    help="apos cadastrar, grava o numero do bug no campo 'bug' do "
                         "caso_de_teste dentro de test/runs/rodada-N.json")
    args = ap.parse_args()

    if args.template:
        print(json.dumps(TEMPLATE, indent=2, ensure_ascii=False))
        return

    base = os.environ.get("RISE_BASE_URL")
    user = os.environ.get("RISE_USER")
    pwd = os.environ.get("RISE_PASSWORD")
    if args.delete or args.file:
        faltando = [k for k, v in (("RISE_BASE_URL", base), ("RISE_USER", user),
                                   ("RISE_PASSWORD", pwd)) if not v]
        if faltando and not args.dry_run:
            sys.exit(f"erro: faltando no .env: {', '.join(faltando)}")

    try:
        if args.delete:
            Rise(base, user, pwd).delete(args.delete)
            print(f"task #{args.delete} removida")
            return

        if not args.file:
            ap.print_help()
            return

        paths = [p for pat in args.file for p in sorted(glob.glob(pat))] or args.file
        bugs = []
        for p in paths:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            for b in (data if isinstance(data, list) else [data]):
                b["_origem"] = p
                bugs.append(b)

        for b in bugs:
            validate(b)

        rise = None
        criados = []
        for b in bugs:
            print()
            print(render_preview(b))
            print(f"(origem: {b['_origem']})")
            if args.dry_run:
                print(">> dry-run: nada cadastrado")
                continue
            if not args.yes:
                b["project_id"] = ask_project(b.get("project_id", DEFAULT_PROJECT))
                if not confirm():
                    print(">> pulado pelo QA")
                    continue
            rise = rise or Rise(base, user, pwd).login()
            tid = rise.create_bug(b)
            criados.append(tid)
            print(f">> cadastrado: #{tid}  {base}/projects/view/"
                  f"{b.get('project_id', DEFAULT_PROJECT)}")
            if args.rodada:
                anota_na_rodada(b, tid, args.rodada)

        if criados:
            print(f"\n{len(criados)} bug(s) cadastrado(s): "
                  + ", ".join(f"#{i}" for i in criados))
    except RiseError as e:
        sys.exit(f"erro: {e}")
    except (json.JSONDecodeError, OSError) as e:
        sys.exit(f"erro lendo arquivo: {e}")


if __name__ == "__main__":
    main()
