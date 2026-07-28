#!/usr/bin/env python3
"""
qa-import-qase — traz o acervo do Qase para o modelo do kit.

Le o export do Qase (CSV da interface ou JSON da API) e gera, por suite, a
pasta de feature com .feature, MATRIZ.md, REGRAS.md, LACUNAS.md e MIGRACAO.md.

O QUE ESTE SCRIPT NAO FAZ -- e por que isso e proposital
    O Qase guarda titulo, passos e prioridade. Ele NAO guarda a regra de
    negocio que o caso prova, porque o modelo dele nao tem esse campo. Entao
    todo caso importado nasce com:

        @RN-PENDENTE   nao se sabe qual regra ele prova
        @nao-aprovado  ninguem revisou este caso DENTRO do novo modelo
        @camada:manual nenhuma decisao de camada foi tomada ainda

    Isso e a verdade sobre o acervo, nao um defeito da importacao. Um caso que
    voce nao consegue ligar a uma regra e um caso que ninguem sabe por que
    existe -- e descobrir isso e metade do valor de trocar de ferramenta.

    O MIGRACAO.md de cada feature e a lista de pendencia dessa reconciliacao.
    O qa_lint conta quantos @RN-PENDENTE sobraram; o qa_dashboard mostra a
    curva. Migracao terminada = zero @RN-PENDENTE.

Uso:
    python3 test/scripts/qa_import_qase.py --csv export-qase.csv
    python3 test/scripts/qa_import_qase.py --json casos.json --prefixo checkout
    python3 test/scripts/qa_import_qase.py --csv e.csv --dry-run
"""

import argparse
import csv
import datetime
import glob
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CASES = os.path.join(ROOT, "test", "cases")

# O Qase varia o cabecalho entre versoes e idiomas do export. Aceitamos os
# nomes conhecidos e caimos fora silenciosamente no que nao reconhecemos --
# perder uma coluna e melhor que abortar a migracao inteira.
COLUNAS = {
    "id": ["id", "case_id", "caseid", "key"],
    "titulo": ["title", "name", "titulo", "título"],
    "descricao": ["description", "descricao", "descrição"],
    "precondicao": ["preconditions", "precondition", "pre_conditions"],
    "poscondicao": ["postconditions", "postcondition"],
    "prioridade": ["priority", "prioridade"],
    "severidade": ["severity", "severidade"],
    "camada": ["layer", "camada"],
    "automacao": ["automation", "automation_status", "automacao"],
    "situacao": ["status", "state", "situacao"],
    "suite": ["suite", "suite_title", "folder", "section", "path"],
    "tags": ["tags", "labels"],
    "passos_acao": ["steps_actions", "steps", "step_action", "steps_action"],
    "passos_esperado": ["steps_result", "steps_expected", "expected_result",
                        "step_expected", "expected"],
}

PRIORIDADE = {"high": "alta", "highest": "alta", "critical": "alta",
              "medium": "media", "normal": "media",
              "low": "baixa", "lowest": "baixa", "trivial": "baixa"}

# camada do Qase e um campo de organizacao, nao a decisao de roteamento que o
# kit exige. So aproveitamos quando o QA pede explicitamente com --manter-camada.
CAMADA = {"e2e": "e2e", "api": "api", "unit": "api", "integration": "api"}


def slug(texto, tamanho=40):
    t = unicodedata.normalize("NFKD", str(texto or ""))
    t = t.encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return (t[:tamanho].rstrip("-") or "sem-suite")


def acha_coluna(cabecalho, chave):
    normal = {re.sub(r"[^a-z0-9_]", "", c.lower().strip()): c for c in cabecalho}
    for cand in COLUNAS[chave]:
        if cand in normal:
            return normal[cand]
    return None


def le_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        amostra = fh.read(8192)
        fh.seek(0)
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
        except csv.Error:
            dialeto = csv.excel
        linhas = list(csv.DictReader(fh, dialect=dialeto))
    if not linhas:
        sys.exit(f"erro: {path} nao tem nenhuma linha de dado")
    cabecalho = list(linhas[0].keys())
    mapa = {k: acha_coluna(cabecalho, k) for k in COLUNAS}
    if not mapa["titulo"]:
        sys.exit(f"erro: nao achei a coluna de titulo em {path}.\n"
                 f"       colunas encontradas: {', '.join(cabecalho)}")
    return [{k: (linha.get(col) or "").strip() if col else ""
             for k, col in mapa.items()} for linha in linhas]


def le_json(path):
    with open(path, encoding="utf-8") as fh:
        dados = json.load(fh)
    # a API do Qase devolve {"result": {"entities": [...]}}; aceitamos tambem
    # a lista crua, que e o que sai de um export manual
    if isinstance(dados, dict):
        dados = (dados.get("result", {}) or {}).get("entities") or dados.get("cases") or []
    out = []
    for c in dados:
        passos = c.get("steps") or []
        out.append({
            "id": str(c.get("id") or ""),
            "titulo": (c.get("title") or "").strip(),
            "descricao": (c.get("description") or "").strip(),
            "precondicao": (c.get("preconditions") or "").strip(),
            "poscondicao": (c.get("postconditions") or "").strip(),
            "prioridade": str(c.get("priority") or ""),
            "severidade": str(c.get("severity") or ""),
            "camada": str(c.get("layer") or ""),
            "automacao": str(c.get("automation") or ""),
            "situacao": str(c.get("status") or ""),
            "suite": str(c.get("suite_title") or c.get("suite") or ""),
            "tags": ",".join(t.get("title", "") if isinstance(t, dict) else str(t)
                             for t in (c.get("tags") or [])),
            "passos_acao": "\n".join((p.get("action") or "") for p in passos),
            "passos_esperado": "\n".join(
                (p.get("expected_result") or p.get("expected") or "") for p in passos),
        })
    return out


def proximo_ct():
    """Maior CT-NNN ja usado no repositorio, +1.

    Alocacao global, nao por pasta: dois QAs importando suites diferentes na
    mesma semana nao podem gerar CT-001 os dois. ID nunca e reciclado.
    """
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
    return maior + 1


def linhas_de(texto):
    return [l.strip() for l in re.split(r"[\r\n]+", texto or "") if l.strip()]


def gherkin(caso):
    """Monta o corpo do cenario a partir dos passos do Qase.

    Marca com [MIGRAR] o que nao deu para derivar. Cenario obviamente
    incompleto e melhor que cenario plausivel e errado: o primeiro alguem
    conserta, o segundo alguem aprova sem ler.
    """
    linhas = []
    pre = linhas_de(caso["precondicao"])
    acoes = linhas_de(caso["passos_acao"])
    esperados = linhas_de(caso["passos_esperado"])

    for i, p in enumerate(pre):
        linhas.append(f"    {'Dado' if i == 0 else 'E'} que {p[0].lower() + p[1:]}")
    if not pre:
        linhas.append("    Dado que [MIGRAR: a pré-condição não veio do Qase]")

    for i, a in enumerate(acoes):
        linhas.append(f"    {'Quando' if i == 0 else 'E'} {a}")
    if not acoes:
        linhas.append("    Quando [MIGRAR: o Qase não trouxe passos]")

    if esperados:
        linhas.append(f"    Então {esperados[-1]}")
        for e in esperados[:-1]:
            linhas.append(f"    E {e}")
    else:
        linhas.append("    Então [MIGRAR: o resultado esperado não veio do Qase]")
    return linhas


def monta_feature(nome, casos_da_suite, manter_camada):
    L = ["# language: pt",
         f"@feature:{nome} @migrado:qase",
         f"Funcionalidade: {nome.replace('-', ' ').capitalize()}",
         "",
         "  # IMPORTADO DO QASE — matéria-prima, não cobertura.",
         "  # Todo cenário aqui está @nao-aprovado e @RN-PENDENTE até alguém",
         "  # dizer qual regra de negócio ele prova. Ver MIGRACAO.md.",
         ""]
    for c in casos_da_suite:
        camada = "manual"
        if manter_camada:
            camada = CAMADA.get(c["camada"].strip().lower(), "manual")
        prio = PRIORIDADE.get(c["prioridade"].strip().lower(), "media")
        tags = [f"@{c['ct']}", "@RN-PENDENTE", f"@camada:{camada}",
                "@suite:regressao", f"@prioridade:{prio}", "@ia-gerado",
                "@nao-aprovado", "@automacao:pendente"]
        if c["id"]:
            tags.append(f"@migrado:qase-{c['id']}")
        L.append("  " + " ".join(tags))
        titulo = c["titulo"] or "[MIGRAR: caso sem título no Qase]"
        L.append(f"  Cenário: {titulo}")
        L.extend(gherkin(c))
        L.append("")
    return "\n".join(L) + "\n"


def monta_matriz(nome, casos_da_suite):
    L = ["<!-- qa-lint: requisito=../../requisitos/RF-XX-<slug>.md hash=PENDENTE -->",
         "",
         f"# Matriz — {nome}",
         "",
         "⚠️ **Importada do Qase.** O cabeçalho `qa-lint` acima aponta para um",
         "requisito que ainda não existe: crie-o com `/qa-intake` e rode",
         "`qa_lint.py --fix-hash`. Enquanto o `hash` estiver `PENDENTE`, o lint",
         "avisa mas não reprova.",
         "",
         "| Regra | Origem | Técnica(s) | Cenários | Risco | Camada | Automação | Status |",
         "|---|---|---|---|---|---|---|---|"]
    for c in casos_da_suite:
        prio = PRIORIDADE.get(c["prioridade"].strip().lower(), "media")
        L.append(f"| RN-PENDENTE | qase-{c['id'] or '?'} | a declarar | "
                 f"{c['ct']} | {prio} | manual | pendente | migrado |")
    L.append("")
    return "\n".join(L)


def monta_migracao(nome, casos_da_suite, hoje):
    total = len(casos_da_suite)
    sem_passos = [c for c in casos_da_suite if not linhas_de(c["passos_acao"])]
    sem_esperado = [c for c in casos_da_suite if not linhas_de(c["passos_esperado"])]
    automatizados = [c for c in casos_da_suite
                     if "auto" in c["automacao"].lower()
                     and "to-be" not in c["automacao"].lower()]
    L = [f"# Migração do Qase — {nome}",
         "",
         f"Importado em {hoje}. **{total} casos.**",
         "",
         "Esta é a lista de pendência da migração. A feature está migrada quando",
         "não sobrar nenhum `@RN-PENDENTE` no `.feature` — e não quando os",
         "arquivos existirem.",
         "",
         "## O que falta, em ordem",
         "",
         "1. **Registrar o requisito.** Rode `/qa-intake` com a documentação da",
         "   feature. Ele cria `test/requisitos/RF-XX-*.md` e o `REGRAS.md` com as",
         "   `RN` numeradas.",
         "2. **Ligar cada caso a uma regra.** Troque `@RN-PENDENTE` pela `RN-XX`",
         "   correspondente. Caso que não liga a nenhuma regra é candidato a",
         "   exclusão — pergunte por que ele existe antes de mantê-lo.",
         "3. **Rotear a camada.** Rode `/qa-roteamento`. Tudo entrou como",
         "   `@camada:manual` porque o Qase não guarda essa decisão.",
         "4. **Aprovar.** Rode `/design-casos-teste` para revisar cenário a",
         "   cenário e trocar `@nao-aprovado` por `@aprovado-por:` com data.",
         "",
         "## Sinais levantados na importação",
         "",
         "| Sinal | Quantidade | O que significa |",
         "|---|---|---|",
         f"| Casos sem passos | {len(sem_passos)} | o cenário saiu com `[MIGRAR]`; "
         f"o texto precisa ser escrito |",
         f"| Casos sem resultado esperado | {len(sem_esperado)} | **o mais grave**: "
         f"caso sem \"Então\" nunca verificou nada |",
         f"| Marcados automatizados no Qase | {len(automatizados)} | entraram como "
         f"`@automacao:pendente`; a spec precisa existir neste repo e citar o `@CT` |",
         "",
         "## Rastreabilidade",
         "",
         "| CT | Qase | Título | Situação no Qase |",
         "|---|---|---|---|"]
    for c in casos_da_suite:
        t = (c["titulo"] or "—").replace("|", "\\|")[:70]
        L.append(f"| {c['ct']} | `{c['id'] or '?'}` | {t} | {c['situacao'] or '—'} |")
    L.append("")
    L.append("> O `@migrado:qase-<id>` fica no cenário para sempre. É o que permite,")
    L.append("> daqui a um ano, responder \"este caso veio do Qase ou nasceu aqui?\".")
    L.append("")
    return "\n".join(L)


REGRAS_SKEL = """# Regras de negócio — {nome}

⚠️ **Vazio de propósito.** O Qase não guarda regra de negócio, então não havia o
que importar. Rode `/qa-intake` com a documentação da feature para preencher.

Enquanto esta tabela estiver vazia, os cenários de `{nome}` provam algo que
ninguém declarou — que é exatamente o que a migração precisa resolver.

| Regra | Origem | Enunciado |
|---|---|---|
| | | |
"""

LACUNAS_SKEL = """# Lacunas — {nome}

Criado pela importação do Qase em {hoje}.

## Abertas

| # | Pergunta | Para quem | Desde | Impacto se não responder |
|---|---|---|---|---|
| L-01 | Qual documento de requisito originou os casos desta suíte? | PO | {hoje} | Sem ele nenhuma `RN` pode ser numerada, e todos os casos ficam `@RN-PENDENTE`. |

## Respondidas

_(nenhuma ainda)_
"""


def main():
    ap = argparse.ArgumentParser(description="Importa o acervo do Qase para o kit")
    origem = ap.add_mutually_exclusive_group(required=True)
    origem.add_argument("--csv", help="export CSV da interface do Qase")
    origem.add_argument("--json", help="JSON da API do Qase")
    ap.add_argument("--prefixo", help="força uma única feature com este nome, "
                                      "em vez de uma por suíte do Qase")
    ap.add_argument("--manter-camada", action="store_true",
                    help="usa o campo 'layer' do Qase em vez de @camada:manual")
    ap.add_argument("--incluir-obsoletos", action="store_true",
                    help="importa também os casos deprecated/obsoletos")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    casos = le_csv(args.csv) if args.csv else le_json(args.json)
    hoje = datetime.date.today().strftime("%Y-%m-%d")

    descartados = []
    if not args.incluir_obsoletos:
        mantidos = []
        for c in casos:
            if c["situacao"].strip().lower() in ("deprecated", "obsolete", "obsoleto"):
                descartados.append(c)
            else:
                mantidos.append(c)
        casos = mantidos

    if not casos:
        sys.exit("erro: nenhum caso a importar (todos obsoletos? use --incluir-obsoletos)")

    # agrupa por suite; o Qase exporta caminho com > ou tab
    grupos = OrderedDict()
    for c in casos:
        if args.prefixo:
            nome = slug(args.prefixo)
        else:
            bruto = re.split(r"[\t>|/]", c["suite"])[-1] if c["suite"] else ""
            nome = slug(bruto or "sem-suite")
        grupos.setdefault(nome, []).append(c)

    # numeracao global, alocada de uma vez para o lote inteiro
    n = proximo_ct()
    for nome, lista in grupos.items():
        for c in lista:
            c["ct"] = f"CT-{n:03d}"
            n += 1

    print(f"qa-import-qase: {len(casos)} caso(s) em {len(grupos)} feature(s)")
    if descartados:
        print(f"  {len(descartados)} obsoleto(s) ignorado(s) "
              f"(--incluir-obsoletos para trazer)")

    for nome, lista in grupos.items():
        destino = os.path.join(CASES, nome)
        print(f"\n  {nome}/  ({len(lista)} casos: "
              f"{lista[0]['ct']}..{lista[-1]['ct']})")
        arquivos = {
            f"{nome}.feature": monta_feature(nome, lista, args.manter_camada),
            "MATRIZ.md": monta_matriz(nome, lista),
            "MIGRACAO.md": monta_migracao(nome, lista, hoje),
            "REGRAS.md": REGRAS_SKEL.format(nome=nome),
            "LACUNAS.md": LACUNAS_SKEL.format(nome=nome, hoje=hoje),
            "EXPLORATORIO.md": f"# Exploratório — {nome}\n\n"
                               f"O Qase não guarda charter. Escreva os seus com "
                               f"`/qa-manual`.\n",
        }
        if args.dry_run:
            for a in arquivos:
                print(f"      criaria {a}")
            continue
        if os.path.exists(destino) and os.listdir(destino):
            print(f"      [pulado] {destino} ja existe e nao esta vazio")
            continue
        os.makedirs(destino, exist_ok=True)
        for a, conteudo in arquivos.items():
            with open(os.path.join(destino, a), "w", encoding="utf-8") as fh:
                fh.write(conteudo)
            print(f"      {a}")

    if args.dry_run:
        print("\n>> dry-run: nada gravado")
        return

    print(f"\nProximo passo: /qa-intake em cada feature, para criar o requisito e")
    print("numerar as RN. Depois troque os @RN-PENDENTE. Acompanhe com:")
    print("   python3 test/scripts/qa_lint.py")
    print("   python3 test/scripts/qa_dashboard.py")


if __name__ == "__main__":
    main()
