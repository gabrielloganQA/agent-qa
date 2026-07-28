#!/usr/bin/env python3
"""
Testes do kit. Um sistema que prega "quebre o comportamento e confirme o
vermelho" precisa fazer isso consigo mesmo.

    python3 -m unittest discover -s test/scripts/tests -v

Sem dependência: unittest da biblioteca padrão, como todo o resto do kit.

O foco não é cobertura de linha — é garantir que **o lint reprova o que promete
reprovar**. Um lint que passa verde em base inconsistente é pior que nenhum,
porque cria confiança onde não deve haver.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
ROOT = os.path.dirname(os.path.dirname(SCRIPTS))
sys.path.insert(0, SCRIPTS)

import qa_ingest          # noqa: E402
import qa_import_qase     # noqa: E402
import qa_lint            # noqa: E402
import qa_report          # noqa: E402
import qa_run             # noqa: E402
import rise_bug           # noqa: E402


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

FEATURE_OK = """# language: pt
Funcionalidade: Exemplo

  @CT-001 @RN-01 @bva @camada:api @suite:regressao @ia-gerado @aprovado-por:qa @data:2026-07-25
  Cenário: aceita o valor no limite
    Dado que o pedido soma "50,00"
    Então o cupom é aceito
"""

MATRIZ_OK = """<!-- qa-lint: requisito=../../requisitos/RF-01.md hash={hash} -->

| Regra | Origem | Técnica(s) | Cenários | Risco | Camada | Automação | Status |
|---|---|---|---|---|---|---|---|
| RN-01 | RF-01 | BVA | CT-001 | Alto | api | pendente | Aprovado |
"""

REGRAS_OK = """# Regras

| Regra | Origem | Enunciado |
|---|---|---|
| **RN-01** | RF-01 | Aceita a partir de R$50,00, inclusive. |
"""


def hash_de(caminho):
    import hashlib
    with open(caminho, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def monta_repo(tmp, feature=FEATURE_OK, regras=REGRAS_OK, matriz=None,
               nome="exemplo", requisito="conteudo do requisito\n"):
    """Cria uma arvore cases/ + requisitos/ valida dentro de tmp."""
    d = os.path.join(tmp, "cases", nome)
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(tmp, "requisitos"), exist_ok=True)
    rp = os.path.join(tmp, "requisitos", "RF-01.md")
    with open(rp, "w", encoding="utf-8") as fh:
        fh.write(requisito)
    h = hash_de(rp)
    with open(os.path.join(d, f"{nome}.feature"), "w", encoding="utf-8") as fh:
        fh.write(feature)
    with open(os.path.join(d, "MATRIZ.md"), "w", encoding="utf-8") as fh:
        fh.write(matriz if matriz is not None else MATRIZ_OK.format(hash=h))
    with open(os.path.join(d, "REGRAS.md"), "w", encoding="utf-8") as fh:
        fh.write(regras)
    with open(os.path.join(d, "LACUNAS.md"), "w", encoding="utf-8") as fh:
        fh.write("# Lacunas\n\n## Abertas\n\n_(nenhuma)_\n")
    return d


def roda_lint(*args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "qa_lint.py")] + list(args),
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode, r.stdout + r.stderr


# --------------------------------------------------------------------------- #

class TestLintReprovaOQuePromete(unittest.TestCase):
    """Cada teste quebra UMA regra e confirma o vermelho."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_base_valida_passa(self):
        monta_repo(self.tmp)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 0, f"base válida deveria passar:\n{saida}")

    def test_cenario_sem_camada_reprova(self):
        f = FEATURE_OK.replace("@camada:api ", "")
        monta_repo(self.tmp, feature=f)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("sem @camada:", saida)

    def test_camada_invalida_reprova(self):
        f = FEATURE_OK.replace("@camada:api", "@camada:frontend")
        monta_repo(self.tmp, feature=f)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("inválida", saida)

    def test_aprovado_sem_data_reprova(self):
        f = FEATURE_OK.replace(" @data:2026-07-25", "")
        monta_repo(self.tmp, feature=f)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("aprovação é ato nominal COM data", saida)

    def test_premissa_sem_nao_aprovado_reprova(self):
        """O portão 1: cenário suposto não pode entrar na suíte oficial."""
        f = FEATURE_OK.replace("@bva ", "@bva @premissa ")
        monta_repo(self.tmp, feature=f)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("entraria na suíte oficial", saida)

    def test_regra_sem_caso_reprova(self):
        regras = REGRAS_OK + "| **RN-02** | RF-01 | Regra que ninguém testou. |\n"
        monta_repo(self.tmp, regras=regras)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("RN-02 não tem nenhum CT", saida)

    def test_sem_caso_justificado_passa(self):
        """A válvula de escape existe e funciona — com motivo declarado."""
        regras = REGRAS_OK + "| **RN-02** | RF-01 | Regra fora de escopo. |\n"
        d = monta_repo(self.tmp, regras=regras)
        h = hash_de(os.path.join(self.tmp, "requisitos", "RF-01.md"))
        with open(os.path.join(d, "MATRIZ.md"), "w", encoding="utf-8") as fh:
            fh.write(MATRIZ_OK.format(hash=h)
                     + "\n@sem-caso:RN-02 — fora do escopo desta release.\n")
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 0, saida)

    def test_requisito_alterado_sem_revisao_reprova(self):
        """A falha que nenhum TMS pega: o requisito muda e os casos não."""
        monta_repo(self.tmp)
        with open(os.path.join(self.tmp, "requisitos", "RF-01.md"), "a",
                  encoding="utf-8") as fh:
            fh.write("\nregra nova que ninguém viu\n")
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("o requisito mudou", saida)

    def test_teto_de_e2e_reprova(self):
        f = FEATURE_OK
        for n in range(2, 5):
            f += FEATURE_OK.split("\n", 2)[2].replace(
                "CT-001", f"CT-00{n}").replace("@camada:api", "@camada:e2e")
        monta_repo(self.tmp, feature=f)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("teto", saida)

    def test_id_duplicado_entre_features_reprova(self):
        """A colisão real: dois QAs, duas features, o mesmo CT-001."""
        monta_repo(self.tmp, nome="feature-a")
        monta_repo(self.tmp, nome="feature-b")
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("ID é global", saida)

    def test_matriz_e_feature_divergentes_reprovam(self):
        f = FEATURE_OK.replace("CT-001", "CT-042")
        monta_repo(self.tmp, feature=f)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1)
        self.assertIn("não está na MATRIZ.md", saida)

    def test_migracao_pendente_avisa_mas_nao_reprova(self):
        """Dívida da migração precisa ser commitável para poder ser paga."""
        f = FEATURE_OK.replace("@RN-01", "@RN-PENDENTE")
        regras = "# Regras\n\n| Regra | Origem | Enunciado |\n|---|---|---|\n"
        monta_repo(self.tmp, feature=f, regras=regras)
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 0, saida)
        self.assertIn("@RN-PENDENTE", saida)


class TestExecucaoOficial(unittest.TestCase):
    """test/runs/ não aceita resultado de agente. Testado in-process."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._root = qa_lint.ROOT
        qa_lint.ROOT = self.tmp
        qa_lint.erros, qa_lint.avisos = [], []
        os.makedirs(os.path.join(self.tmp, "test", "runs"))

    def tearDown(self):
        qa_lint.ROOT = self._root
        qa_lint.erros, qa_lint.avisos = [], []
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _grava(self, por):
        p = os.path.join(self.tmp, "test", "runs", "rodada-1.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"rodada": 1, "resultados": {
                "CT-001": {"status": "passou", "executado_por": por}}}, fh)

    def test_agente_reprova(self):
        for por in ("agente", "claude", "ia"):
            with self.subTest(por=por):
                qa_lint.erros = []
                self._grava(por)
                qa_lint.checa_runs()
                self.assertTrue(qa_lint.erros, f"'{por}' deveria reprovar")

    def test_ci_e_qa_passam(self):
        for por in ("ci", "qa"):
            with self.subTest(por=por):
                qa_lint.erros = []
                self._grava(por)
                qa_lint.checa_runs()
                self.assertEqual(qa_lint.erros, [])


class TestIngestJUnit(unittest.TestCase):

    def test_extrai_varios_ct_do_titulo(self):
        self.assertEqual(
            qa_ingest.cts_do_texto("@CT-007 @CT-008 aplica cupom"),
            ["CT-007", "CT-008"])

    def test_titulo_sem_ct_nao_casa(self):
        self.assertEqual(qa_ingest.cts_do_texto("teste sem tag"), [])

    def test_le_os_tres_desfechos(self):
        xml = """<testsuites><testsuite name="s">
          <testcase classname="c" name="@CT-001 passa" time="1.5"/>
          <testcase classname="c" name="@CT-002 falha" time="0.2">
            <failure message="esperado 201, veio 500"/></testcase>
          <testcase classname="c" name="@CT-003 pulado">
            <skipped message="sem massa"/></testcase>
        </testsuite></testsuites>"""
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "r.xml")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(xml)
            d = qa_ingest.consolida(qa_ingest.le_junit([p]))
            self.assertEqual(d["CT-001"]["status"], "passou")
            self.assertEqual(d["CT-002"]["status"], "falhou")
            self.assertIn("500", d["CT-002"]["obs"])
            # skip nunca vira verde: e o green-skip que o kit proibe
            self.assertEqual(d["CT-003"]["status"], "nao_executado")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_pior_noticia_vence(self):
        """Um CT em dois testes: se um falhou, o CT falhou."""
        testes = [(["CT-001"], "passou", "a", 1.0, ""),
                  (["CT-001"], "falhou", "b", 2.0, "quebrou")]
        d = qa_ingest.consolida(testes)
        self.assertEqual(d["CT-001"]["status"], "falhou")
        self.assertEqual(d["CT-001"]["tempo"], 3.0)

    def test_ordem_inversa_da_o_mesmo_resultado(self):
        testes = [(["CT-001"], "falhou", "b", 2.0, "quebrou"),
                  (["CT-001"], "passou", "a", 1.0, "")]
        self.assertEqual(qa_ingest.consolida(testes)["CT-001"]["status"], "falhou")


class TestRiseBug(unittest.TestCase):

    def test_severidade_exige_nivel(self):
        bug = {"escopo": "x", "resumo": "y", "descricao": "z",
               "comportamento_atual": "a", "resultado_esperado": "b",
               "passos": ["1"], "prioridade": "Alta", "impacto": "i",
               "severidade": "bem grave mesmo"}
        with self.assertRaises(rise_bug.RiseError) as ctx:
            rise_bug.validate(bug)
        self.assertIn("S1..S4", str(ctx.exception))
        bug["severidade"] = "S2 — quebra com contorno"
        rise_bug.validate(bug)          # não levanta

    def test_media_vira_alta(self):
        """O AP não tem 'Média'. Mapear é decisão registrada, não silêncio."""
        self.assertEqual(rise_bug.resolve_priority("Média"),
                         rise_bug.PRIORITY_IDS["alta"])

    def test_prioridade_invalida_recusa(self):
        with self.assertRaises(rise_bug.RiseError):
            rise_bug.resolve_priority("Urgentíssima")

    def test_evidencia_ganha_caminho_datado(self):
        import datetime
        p = rise_bug.evidence_paths(["ct-005.png"], datetime.date(2026, 7, 21))
        self.assertEqual(p, ["test/image/21-07-2026/ct-005.png"])

    def test_titulo_nao_usa_travessao(self):
        """Em-dash no título derruba a conexão (armadilha 4.5 do padrão)."""
        t = rise_bug.build_title({"escopo": "Checkout", "resumo": "falha X"})
        self.assertNotIn("—", t)


class TestRelatorioDocx(unittest.TestCase):
    """O trecho mais frágil do kit: XML de .docx manipulado com regex."""

    def test_extracao_nao_vaza_no_tab(self):
        p = ('<w:p><w:r><w:t>Antes</w:t></w:r><w:r><w:tab/></w:r>'
             '<w:r><w:t>Depois</w:t></w:r></w:p>')
        self.assertEqual(qa_report.texto_do_paragrafo(p), "AntesDepois")

    def test_reescrita_preserva_estilo(self):
        p = ('<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
             '<w:r><w:rPr><w:b/></w:rPr><w:t>velho</w:t></w:r></w:p>')
        novo = qa_report.reescreve_paragrafo(p, "novo")
        self.assertIn('<w:jc w:val="center"/>', novo)
        self.assertIn("<w:b/>", novo)
        self.assertIn("novo", novo)
        self.assertNotIn("velho", novo)

    def test_escapa_caractere_xml(self):
        p = "<w:p><w:r><w:t>x</w:t></w:r></w:p>"
        self.assertIn("&amp;", qa_report.reescreve_paragrafo(p, "A & B"))

    def test_define_linhas_deixa_n_copias(self):
        doc = ("<w:tbl>"
               "<w:tr><w:p><w:r><w:t>[X]</w:t></w:r></w:p></w:tr>"
               "<w:tr><w:p><w:r><w:t>[X]</w:t></w:r></w:p></w:tr>"
               "</w:tbl>")
        self.assertEqual(qa_report.define_linhas(doc, "[X]", 3).count("<w:tr>"), 3)
        self.assertEqual(qa_report.define_linhas(doc, "[X]", 1).count("<w:tr>"), 1)


class TestImportQase(unittest.TestCase):

    def test_slug_normaliza_acento(self):
        self.assertEqual(qa_import_qase.slug("Checkout — Cupões & Ofertas"),
                         "checkout-cupoes-ofertas")

    def test_caso_sem_passos_sai_marcado(self):
        """Cenário obviamente incompleto > cenário plausível e errado."""
        linhas = qa_import_qase.gherkin(
            {"precondicao": "", "passos_acao": "", "passos_esperado": ""})
        # o marcador e "[MIGRAR: <motivo>]" -- procurar "[MIGRAR]" fechado nunca
        # casa, e o teste passaria a verificar nada
        self.assertEqual(len(linhas), 3)
        self.assertTrue(all("[MIGRAR:" in l for l in linhas), linhas)

    def test_passos_viram_gherkin(self):
        linhas = qa_import_qase.gherkin({
            "precondicao": "estou autenticada",
            "passos_acao": "aplico o cupom\nconfirmo o pedido",
            "passos_esperado": "o desconto aparece"})
        texto = "\n".join(linhas)
        self.assertIn("Dado que estou autenticada", texto)
        self.assertIn("Quando aplico o cupom", texto)
        self.assertIn("E confirmo o pedido", texto)
        self.assertIn("Então o desconto aparece", texto)
        self.assertNotIn("[MIGRAR]", texto)

    def test_importado_nasce_travado(self):
        caso = {"ct": "CT-001", "id": "42", "titulo": "t", "prioridade": "high",
                "camada": "e2e", "precondicao": "", "passos_acao": "",
                "passos_esperado": ""}
        f = qa_import_qase.monta_feature("x", [caso], manter_camada=False)
        self.assertIn("@nao-aprovado", f)
        self.assertIn("@RN-PENDENTE", f)
        self.assertIn("@migrado:qase-42", f)
        self.assertIn("@camada:manual", f)      # camada é decisão do roteamento
        self.assertNotIn("@aprovado-por", f)


class TestConversaoReconciliada(unittest.TestCase):
    """Conversão vem da TAG; execução vem do XML. Nada reconciliava os dois.

    O CI rodava 12 casos e o painel seguia exibindo 'conversão 0%', porque
    ninguém marcou @automacao:feito depois do merge da spec. Dois números de
    fontes diferentes, nenhum obviamente errado — a pior espécie de métrica.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._root = qa_lint.ROOT
        qa_lint.ROOT = self.tmp
        qa_lint.erros, qa_lint.avisos = [], []
        os.makedirs(os.path.join(self.tmp, "test", "runs"))
        with open(os.path.join(self.tmp, "test", "runs", "rodada-1.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"rodada": 1, "resultados": {
                "CT-001": {"status": "passou", "executado_por": "ci"}}}, fh)

    def tearDown(self):
        qa_lint.ROOT = self._root
        qa_lint.erros, qa_lint.avisos = [], []
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ci_rodou_caso_ainda_pendente_avisa(self):
        qa_lint.checa_runs({"CT-001": "pendente"})
        self.assertTrue(any("conversao-desatualizada" in a for a in qa_lint.avisos),
                        f"deveria avisar; avisos={qa_lint.avisos}")
        self.assertEqual(qa_lint.erros, [],
                         "é aviso, não erro: a spec pode ter acabado de entrar")

    def test_caso_declarado_feito_nao_avisa(self):
        qa_lint.checa_runs({"CT-001": "feito:PR-42"})
        self.assertEqual(qa_lint.avisos, [])

    def test_execucao_manual_nao_cobra_automacao(self):
        """`qa` é pessoa executando à mão — não diz nada sobre conversão."""
        with open(os.path.join(self.tmp, "test", "runs", "rodada-1.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"rodada": 1, "resultados": {
                "CT-001": {"status": "passou", "executado_por": "qa"}}}, fh)
        qa_lint.checa_runs({"CT-001": "pendente"})
        self.assertEqual(qa_lint.avisos, [])


class TestRelatorioNaoSubnotifica(unittest.TestCase):
    """Falha sem bug cadastrado não é ausência de defeito.

    O sumário executivo contava defeito só a partir de bugs/*.json: uma rodada
    com caso reprovado e nenhum bug saía com '0 defeitos em aberto' — o
    primeiro número que o PMO lê.
    """

    def _criterios(self, resultados, bugs=()):
        casos = {c: {"tecnicas": [], "automacao": "feito:PR-1"} for c in resultados}
        return qa_report.criterios_saida({"taxa_aprov": 100.0}, list(bugs),
                                         casos, resultados)

    def _linha(self, itens):
        return next(i for i in itens if i[0].startswith("Falhas sem defeito"))

    def test_falha_sem_bug_reprova_o_criterio(self):
        itens, _s1, _s2, sem_bug = self._criterios({"CT-001": {"status": "falhou"}})
        self.assertEqual(sem_bug, ["CT-001"])
        self.assertFalse(self._linha(itens)[3])

    def test_falha_com_bug_passa(self):
        itens, _s1, _s2, sem_bug = self._criterios(
            {"CT-001": {"status": "falhou", "bug": 4471}})
        self.assertEqual(sem_bug, [])
        self.assertTrue(self._linha(itens)[3])

    def test_rodada_sem_falha_passa(self):
        itens, _s1, _s2, sem_bug = self._criterios({"CT-001": {"status": "passou"}})
        self.assertEqual(sem_bug, [])
        self.assertTrue(self._linha(itens)[3])


class TestRodadaEUnidade(unittest.TestCase):
    """Uma rodada tem dois donos e dois arquivos; o parecer precisa dos dois.

    CI escreve em runs/rodada-N.json, QA em runs/manual/<data>-rodada-N.json.
    Separar a ESCRITA é o que impede o agente de tocar no histórico oficial —
    isso fica. Mas o relatório lia `runs[-1]`, ou seja, UM dos arquivos: num
    ciclo em que o CI rodou 1 caso e o QA rodou 2, ele anunciava '2/3
    executados' com os 3 executados, e o PMO nunca via a outra metade.
    """

    def _ci(self, **res):
        return {"rodada": 1, "data": "2026-07-27", "_arquivo": "rodada-1.json",
                "resultados": res}

    def _manual(self, **res):
        return {"rodada": 1, "data": "2026-07-28",
                "_arquivo": "manual/2026-07-28-rodada-1.json", "resultados": res}

    def test_funde_os_dois_arquivos(self):
        r = qa_run.consolida_rodada([
            self._ci(**{"CT-001": {"status": "passou", "executado_por": "ci"}}),
            self._manual(**{"CT-002": {"status": "passou", "executado_por": "qa"}})])
        self.assertEqual(sorted(r["resultados"]), ["CT-001", "CT-002"])

    def test_pessoa_vence_o_ci_no_mesmo_caso(self):
        """Decisão do time: o QA reexecuta justamente quando desconfia do verde."""
        r = qa_run.consolida_rodada([
            self._ci(**{"CT-001": {"status": "passou", "executado_por": "ci"}}),
            self._manual(**{"CT-001": {"status": "falhou", "executado_por": "qa"}})])
        self.assertEqual(r["resultados"]["CT-001"]["status"], "falhou")

    def test_ordem_dos_arquivos_nao_muda_o_resultado(self):
        ci = self._ci(**{"CT-001": {"status": "passou", "executado_por": "ci"}})
        man = self._manual(**{"CT-001": {"status": "falhou", "executado_por": "qa"}})
        for runs in ([ci, man], [man, ci]):
            with self.subTest(ordem=[r["_arquivo"] for r in runs]):
                self.assertEqual(
                    qa_run.consolida_rodada(runs)["resultados"]["CT-001"]["status"],
                    "falhou")

    def test_placeholder_nao_apaga_resultado_real(self):
        """A rodada nasce com tudo em nao_executado — não pode vencer o CI."""
        r = qa_run.consolida_rodada([
            self._ci(**{"CT-001": {"status": "passou", "executado_por": "ci"}}),
            self._manual(**{"CT-001": {"status": "nao_executado",
                                       "executado_por": None}})])
        self.assertEqual(r["resultados"]["CT-001"]["status"], "passou")

    def test_ciclos_conta_rodadas_nao_arquivos(self):
        self.assertEqual(qa_run.numeros_de_rodada([self._ci(), self._manual()]), [1])

    def test_relatorio_conta_o_ciclo_inteiro(self):
        casos = {c: {} for c in ("CT-001", "CT-002", "CT-003")}
        m = qa_report.metricas(casos, [
            self._ci(**{"CT-001": {"status": "passou", "executado_por": "ci"}}),
            self._manual(**{"CT-002": {"status": "passou", "executado_por": "qa"},
                            "CT-003": {"status": "passou", "executado_por": "qa"}})])
        self.assertEqual(m["executado"], 3, "os 3 casos rodaram — o parecer via 2")
        self.assertEqual(m["ciclos"], 1, "dois arquivos, um ciclo só")


class TestCriteriosCasamComOModelo(unittest.TestCase):
    """Os rótulos da tabela de critérios moram no .docx; os valores, no código.

    A tabela do modelo tem uma linha por critério, com o rótulo escrito nela.
    O `qa_report` só preenche as células `[%]`/`[N]`/`[Atendido]`, na ordem —
    então a ordem do código e a ordem do modelo são um contrato implícito.
    Quando um critério novo entrou no código e não no modelo, ele sumiu da
    tabela do PMO sem erro nenhum: aparecia na justificativa e em lugar
    nenhum mais. Este teste torna a deriva mecânica.
    """

    def _rotulos_do_modelo(self):
        import re
        import zipfile
        z = zipfile.ZipFile(os.path.join(ROOT, "templates",
                                         "Relatorio_de_Testes_Atlante.docx"))
        xml = z.read("word/document.xml").decode("utf-8")
        out = []
        for tr in re.findall(r"<w:tr[ >].*?</w:tr>", xml, re.S):
            if "[Atendido]" not in tr:
                continue
            celulas = [re.sub(r"<[^>]+>", "", c)
                       for c in re.findall(r"<w:tc[ >].*?</w:tc>", tr, re.S)]
            out.append(celulas[0])
        return out

    def test_ordem_e_quantidade_batem(self):
        itens, _s1, _s2, _sb = qa_report.criterios_saida(
            {"taxa_aprov": 100.0}, [],
            {"CT-001": {"tecnicas": [], "automacao": "feito:PR-1"}},
            {"CT-001": {"status": "passou"}})
        self.assertEqual([i[0] for i in itens], self._rotulos_do_modelo(),
                         "critério do código sem linha no modelo (ou fora de "
                         "ordem): ele não apareceria na tabela do PMO")


class TestPortaoContraBash(unittest.TestCase):
    """O portão 2 valia só para Edit/Write/MultiEdit.

    `sed -i`, `cat >` e `python3 -c` gravavam a mesma tag sem disparar nada — e
    o lint NÃO pega este caso, porque ele cobra @aprovado-por quando a tag
    falta, nunca valida quem a escreveu.
    """

    HOOK = os.path.join(ROOT, ".claude", "hooks", "guarda_portao.py")

    def _roda(self, payload):
        """Devolve o MOTIVO decodificado, ou '' se o hook liberou.

        Ler o stdout cru não serve: json.dumps escapa acento, então 'PORTÃO'
        chega como 'PORT\\u00c3O'. O harness consome o JSON parseado — o teste
        precisa olhar o mesmo que ele.
        """
        r = subprocess.run([sys.executable, self.HOOK], input=json.dumps(payload),
                           capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": ROOT})
        saida = r.stdout.strip()
        if not saida:
            return ""
        d = json.loads(saida)["hookSpecificOutput"]
        self.assertEqual(d["permissionDecision"], "deny")
        return d["permissionDecisionReason"]

    def _bash(self, comando):
        return self._roda({"tool_name": "Bash", "tool_input": {"command": comando}})

    def test_sed_gravando_aprovacao_e_bloqueado(self):
        self.assertIn("PORTÃO 2", self._bash(
            "sed -i 's/@nao-aprovado/@aprovado-por:ana @data:2026-07-27/' x.feature"))

    def test_heredoc_gravando_aprovacao_e_bloqueado(self):
        self.assertIn("PORTÃO 2", self._bash(
            "cat > x.feature <<EOF\n@CT-001 @aprovado-por:bruno\nEOF"))

    def test_escrita_de_agente_em_runs_e_bloqueada(self):
        for valor in ("agente", "claude", "ia"):
            with self.subTest(valor=valor):
                saida = self._bash(
                    'printf \'{"executado_por":"%s"}\' > test/runs/rodada-9.json'
                    % valor)
                self.assertIn("executado_por", saida)

    def test_sed_removendo_ia_gerado_e_bloqueado(self):
        self.assertIn("ia-gerado", self._bash("sed -i 's/@ia-gerado//g' x.feature"))

    def test_contar_aprovacoes_continua_liberado(self):
        """Contar aprovação é legítimo; forjar uma não é. A linha é o valor."""
        self.assertEqual(self._bash("grep -rc aprovado-por test/cases/"), "")

    def test_agente_em_sessoes_e_liberado(self):
        """test/sessoes/ é justamente onde resultado de agente deve morar."""
        self.assertEqual(self._bash(
            'echo \'{"executado_por":"agente"}\' > test/sessoes/2026-07-27-x.md'), "")

    def test_comando_comum_nao_dispara(self):
        self.assertEqual(self._bash("python3 test/scripts/qa_lint.py"), "")

    def test_hook_nunca_derruba_a_sessao(self):
        r = subprocess.run([sys.executable, self.HOOK], input="isto nao e json",
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


class TestSpecProvaOCenario(unittest.TestCase):
    """Invariante 5: o guarda-corpo não pode parar no Gherkin.

    O .feature dizia "o total deve ser 90,00" e a spec dizia
    expect(total).toBeTruthy(): verde para sempre, e nenhum PR reprovava, porque
    a spec só era lida pelo NOME do arquivo.
    """

    AUTO = {"CT-001": "feito:PR-9", "CT-005": "feito:PR-9"}
    TRAVADO = {"CT-005"}        # cenário sem aprovação, parado por lacuna aberta

    def roda(self, spec):
        qa_lint.erros[:] = []
        qa_lint.avisos[:] = []
        original = qa_lint.specs_do_repo
        qa_lint.specs_do_repo = lambda base=None: [("test/api/pedido.spec.ts", spec)]
        try:
            qa_lint.checa_specs(self.AUTO, self.TRAVADO)
            return list(qa_lint.erros), list(qa_lint.avisos)
        finally:
            qa_lint.specs_do_repo = original
            qa_lint.erros[:] = []
            qa_lint.avisos[:] = []

    def assertReprova(self, spec, regra):
        erros, _ = self.roda(spec)
        self.assertTrue(any(regra in e for e in erros),
                        f"esperava {regra}, veio: {erros}")

    def assertPassa(self, spec):
        erros, avisos = self.roda(spec)
        self.assertEqual(erros + avisos, [])

    def test_assercao_forte_passa(self):
        self.assertPassa("""
test('CT-001 desconto de 10%', async () => {
  const r = await api.post('/pedidos', { total: 100.00 });
  expect(r.status()).toBe(201);
  expect(r.json().total).toBe(90.00);
});
""")

    def test_so_assercao_fraca_reprova(self):
        self.assertReprova("""
test('CT-001 desconto de 10%', async () => {
  expect(r.json().total).toBeTruthy();
});
""", "spec-sem-assercao-forte")

    def test_status_forte_com_valor_frouxo_avisa(self):
        """A falha mais comum de verdade: o status vai forte e o valor, frouxo.

        Não é erro — pode ser guarda de passo intermediário, e o lint não sabe
        qual asserção prova a RN. Mas some do PR sem ninguém olhar se calar.
        """
        erros, avisos = self.roda("""
test('CT-001 desconto de 10%', async () => {
  expect(r.status()).toBe(200);
  expect(r.json().total).toBeTruthy();
});
""")
        self.assertEqual(erros, [])
        self.assertTrue(any("spec-assercao-fraca" in a for a in avisos), avisos)

    def test_so_assercoes_fortes_nao_avisa(self):
        """Em spec bem escrita o aviso é silencioso — senão vira ruído ignorado."""
        self.assertPassa("""
test('CT-001 desconto de 10%', async () => {
  expect(r.status()).toBe(200);
  expect(r.json().total).toBe(90.00);
});
""")

    def test_to_be_ok_e_fraca(self):
        """toBeOK() do Playwright aceita a faixa 200-299 inteira."""
        self.assertReprova("""
test('CT-001 desconto', async () => {
  expect(r).toBeOK();
});
""", "spec-sem-assercao-forte")

    def test_assert_nu_do_python_e_fraco(self):
        self.assertReprova("""
def test_desconto():
    # CT-001
    assert pedido.total
""", "spec-sem-assercao-forte")

    def test_assert_com_comparacao_passa(self):
        self.assertPassa("""
def test_desconto():
    # CT-001
    assert pedido.total == 90.00
""")

    def test_dois_status_http_reprova(self):
        self.assertReprova("""
test('CT-001 criação', async () => {
  expect([200, 201]).toContain(r.status());
  expect(r.json().total).toBe(90.00);
});
""", "spec-status-ambiguo")

    def test_skip_em_caso_aprovado_reprova(self):
        self.assertReprova("""
test.skip('CT-001 desconto', async () => {
  expect(total).toBe(90.00);
});
""", "spec-desligada")

    def test_skip_em_caso_travado_por_lacuna_passa(self):
        """O kit manda marcar @nao-aprovado; aí desligar a spec é coerente."""
        self.assertPassa("""
test.skip('CT-005 arredondamento', async () => {
  expect(total).toBe(90.00);
});
""")

    def test_only_reprova_ate_em_caso_nao_aprovado(self):
        """`.only` não desliga um teste — desliga todos os outros."""
        erros, _ = self.roda("""
test.only('CT-005 arredondamento', async () => {
  expect(total).toBe(90.00);
});
""")
        self.assertTrue(any("spec-desligada" in e and ".only" in e for e in erros), erros)

    def test_decorador_de_pytest_pertence_ao_bloco(self):
        """@pytest.mark.skip vem na linha DE CIMA do def — cortar no def o perdia."""
        self.assertReprova("""
import pytest

@pytest.mark.skip(reason="flaky")
def test_desconto():
    # CT-001
    assert pedido.total == 90.00
""", "spec-desligada")

    def test_espera_cega_avisa(self):
        _, avisos = self.roda("""
test('CT-001 desconto', async () => {
  await page.waitForTimeout(3000);
  expect(total).toBe(90.00);
});
""")
        self.assertTrue(any("spec-espera-cega" in a for a in avisos), avisos)

    def test_timeout_acima_do_teto_avisa(self):
        _, avisos = self.roda("""
test('CT-001 desconto', async () => {
  test.setTimeout(60000);
  expect(total).toBe(90.00);
});
""")
        self.assertTrue(any("spec-timeout-alto" in a for a in avisos), avisos)

    def test_timeout_dentro_do_teto_passa(self):
        self.assertPassa("""
test('CT-001 desconto', { timeout: 10000 }, async () => {
  expect(total).toBe(90.00);
});
""")

    def test_ct_herdado_do_describe(self):
        self.assertReprova("""
describe('CT-001 desconto', () => {
  test('aplica 10%', async () => {
    expect(total).toBeTruthy();
  });
});
""", "spec-sem-assercao-forte")

    def test_arquivo_de_apoio_e_ignorado(self):
        """Fixture e page object não afirmam provar caso nenhum."""
        self.assertPassa("""
export async function login(page) {
  await page.waitForTimeout(500);
  expect(page).toBeTruthy();
}
""")

    def test_ct_desconhecido_e_ignorado(self):
        self.assertPassa("""
test.skip('CT-999 caso de outro repositório', async () => {
  expect(x).toBeTruthy();
});
""")

    def test_sem_casos_nao_checa_nada(self):
        """Repositório recém-clonado: nenhum caso, nada que a spec possa provar."""
        qa_lint.erros[:] = []
        original = qa_lint.specs_do_repo
        qa_lint.specs_do_repo = lambda base=None: [
            ("test/api/x.spec.ts", "test.skip('CT-001', () => {})")]
        try:
            qa_lint.checa_specs({}, set())
            self.assertEqual(qa_lint.erros, [])
        finally:
            qa_lint.specs_do_repo = original
            qa_lint.erros[:] = []


class TestSpecsDoRepoAcham(unittest.TestCase):
    """A varredura devolve caminho e não repete arquivo."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root_original = qa_lint.ROOT
        qa_lint.ROOT = self.tmp
        qa_lint._specs_cache.clear()

    def tearDown(self):
        qa_lint.ROOT = self.root_original
        qa_lint._specs_cache.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nao_duplica_spec_ts(self):
        """`*.spec.ts` casa em dois padrões do glob — a leitura era dupla."""
        d = os.path.join(self.tmp, "test", "api")
        os.makedirs(d)
        with open(os.path.join(d, "pedido.spec.ts"), "w", encoding="utf-8") as fh:
            fh.write("// CT-001\n")
        achados = qa_lint.specs_do_repo()
        self.assertEqual([r for r, _ in achados], ["test/api/pedido.spec.ts"])

    def test_base_e_irma_da_raiz_de_casos(self):
        """`piloto/cases` implica `piloto/api` — a camada é irmã da raiz.

        Sem isso, `--dir` validava a raiz alternativa contra as specs de
        `test/`, que não são as dela.
        """
        d = os.path.join(self.tmp, "piloto", "api")
        os.makedirs(d)
        with open(os.path.join(d, "cupom.spec.ts"), "w", encoding="utf-8") as fh:
            fh.write("// CT-002\n")
        base = qa_lint.base_de(os.path.join(self.tmp, "piloto", "cases"))
        achados = qa_lint.specs_do_repo(base)
        self.assertEqual([r for r, _ in achados], ["piloto/api/cupom.spec.ts"])


class TestSpecsEstaoLigadasNoMain(unittest.TestCase):
    """A regra existe e é despachada.

    `qa_run.py --executar` já foi assim: existia, era documentado e nunca era
    chamado no main(). Regra que ninguém invoca é comentário.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def escreve_spec(self, corpo):
        d = os.path.join(self.tmp, "api")       # irmã de cases/, como test/api
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "cupom.spec.ts"), "w", encoding="utf-8") as fh:
            fh.write(corpo)

    def test_lint_reprova_spec_frouxa_de_ponta_a_ponta(self):
        # CT-001 do FEATURE_OK está aprovado; marcá-lo @automacao:feito faz a
        # spec entrar no escopo da checagem.
        feature = FEATURE_OK.replace("@bva ", "@bva @automacao:feito:PR-9 ")
        monta_repo(self.tmp, feature=feature)
        self.escreve_spec("test('CT-001 aceita o valor no limite', async () => {\n"
                          "  expect(await cupom.aplicar(50.00)).toBeTruthy();\n"
                          "});\n")
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 1, saida)
        self.assertIn("spec-sem-assercao-forte", saida)

    def test_spec_forte_passa_de_ponta_a_ponta(self):
        feature = FEATURE_OK.replace("@bva ", "@bva @automacao:feito:PR-9 ")
        monta_repo(self.tmp, feature=feature)
        self.escreve_spec("test('CT-001 aceita o valor no limite', async () => {\n"
                          "  expect(await cupom.aplicar(50.00)).toBe(45.00);\n"
                          "});\n")
        cod, saida = roda_lint("--dir", os.path.join(self.tmp, "cases"))
        self.assertEqual(cod, 0, saida)


class TestSeveridadeInferidaAparece(unittest.TestCase):
    """A skill prometia que o script RECUSA severidade sem nível S1..S4.

    Ele na verdade mapeia `"alta"` → `S2` em silêncio. Mapear é útil na
    migração; decidir calado não é — `S1` contra `S2` é a diferença entre
    interromper o ciclo e liberar a release, e o `CLAUDE.md` lista severidade
    entre o que a IA nunca decide sozinha.
    """

    def test_nivel_escrito_e_declarado(self):
        self.assertTrue(rise_bug.nivel_declarado({"severidade": "S2 — com contorno"}))

    def test_apelido_nao_e_declarado(self):
        self.assertFalse(rise_bug.nivel_declarado({"severidade": "alta"}))

    def test_apelido_ainda_resolve(self):
        """A conveniência continua — o que muda é ela deixar de ser invisível."""
        self.assertEqual(rise_bug.severidade_nivel({"severidade": "alta"}), "S2")
        self.assertEqual(rise_bug.severidade_nivel({"severidade": "critica"}), "S1")


class TestPortao2NaExecucao(unittest.TestCase):
    """O portão 2 vazava no limite da execução.

    `PROCESSO.md` promete que "@nao-aprovado fica fora da suíte oficial" e
    atribui isso a "hook + lint". Nenhum dos dois cobria este ponto: cenário
    `@premissa @nao-aprovado` — comportamento SUPOSTO, esperando o PO — podia
    ser marcado `passou` numa rodada oficial. O lint passava limpo, o painel
    contava como coberto e o relatório do PMO anunciava aprovação sobre isso.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root_original = qa_lint.ROOT
        qa_lint.ROOT = self.tmp
        os.makedirs(os.path.join(self.tmp, "test", "runs"))

    def tearDown(self):
        qa_lint.ROOT = self.root_original
        qa_lint.erros[:] = []
        qa_lint.avisos[:] = []
        shutil.rmtree(self.tmp, ignore_errors=True)

    def grava_run(self, status, por="qa"):
        alvo = os.path.join(self.tmp, "test", "runs", "rodada-1.json")
        with open(alvo, "w", encoding="utf-8") as fh:
            json.dump({"rodada": 1, "resultados": {
                "CT-009": {"status": status, "executado_por": por}}}, fh)

    def roda_lint(self, nao_aprovados):
        qa_lint.erros[:] = []
        qa_lint.avisos[:] = []
        qa_lint.checa_runs({"CT-009": "pendente"}, nao_aprovados)
        return list(qa_lint.erros)

    def test_passou_em_cenario_nao_aprovado_reprova(self):
        self.grava_run("passou")
        erros = self.roda_lint({"CT-009"})
        self.assertTrue(any("execucao-nao-aprovada" in e for e in erros), erros)

    def test_falhou_em_cenario_nao_aprovado_reprova(self):
        """Também vale para falha: ela vira taxa de reprovação no parecer."""
        self.grava_run("falhou")
        self.assertTrue(any("execucao-nao-aprovada" in e
                            for e in self.roda_lint({"CT-009"})))

    def test_nao_executado_em_nao_aprovado_passa(self):
        """É o estado CORRETO de cenário travado por lacuna — não é violação."""
        self.grava_run("nao_executado")
        self.assertEqual(self.roda_lint({"CT-009"}), [])

    def test_passou_em_cenario_aprovado_passa(self):
        self.grava_run("passou")
        self.assertEqual(self.roda_lint(set()), [])


class TestInitRespeitaOPortao2(unittest.TestCase):
    """`qa_run.py --init` montava a rodada com parse_features() inteiro."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cases_original = qa_run.CASES_DIR
        qa_run.CASES_DIR = os.path.join(self.tmp, "cases")

    def tearDown(self):
        qa_run.CASES_DIR = self.cases_original
        shutil.rmtree(self.tmp, ignore_errors=True)

    def escreve(self, feature):
        d = os.path.join(self.tmp, "cases", "x")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "x.feature"), "w", encoding="utf-8") as fh:
            fh.write(feature)

    def test_parse_features_marca_aprovacao(self):
        self.escreve(FEATURE_OK)                       # CT-001 tem @aprovado-por:
        self.assertTrue(qa_run.parse_features()["CT-001"]["aprovado"])

    def test_sem_a_tag_nasce_nao_aprovado(self):
        """Nada nasce aprovado: a ausência da tag é o estado padrão."""
        self.escreve(FEATURE_OK.replace("@aprovado-por:qa @data:2026-07-25",
                                        "@nao-aprovado"))
        self.assertFalse(qa_run.parse_features()["CT-001"]["aprovado"])


class TestPainelTemOQueMostrar(unittest.TestCase):
    """O painel lia `test/cases` cravado.

    Num repositório recém-clonado ele mostrava tudo zerado, e quem fosse
    apresentar a ideia ao PO não tinha o que mostrar. O `qa_lint` já tinha
    `--dir`; o painel, não.
    """

    def roda(self, *args):
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "qa_dashboard.py")] + list(args),
            capture_output=True, text=True, cwd=ROOT)
        return r.returncode, r.stdout + r.stderr

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        monta_repo(self.tmp)                     # 1 caso, CT-001, aprovado
        self.raiz = os.path.join(self.tmp, "cases")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_outra_raiz_produz_painel_com_dados(self):
        cod, saida = self.roda("--dir", self.raiz, "--json")
        self.assertEqual(cod, 0, saida)
        d = json.loads(saida)
        self.assertEqual(d["casos"], 1)
        self.assertEqual(d["aprovados"], 1)
        self.assertEqual(d["cobertura_pct"], 100.0)

    def test_html_e_autocontido(self):
        """Sem CDN e sem servidor: o PO abre com duplo clique, inclusive offline."""
        alvo = os.path.join(self.tmp, "painel.html")
        cod, saida = self.roda("--dir", self.raiz, "--saida", alvo)
        self.assertEqual(cod, 0, saida)
        with open(alvo, encoding="utf-8") as fh:
            html = fh.read()
        for externo in ("http://", "https://", "<script src", "<link rel=\"stylesheet\""):
            self.assertNotIn(externo, html, f"referência externa: {externo}")

    def test_raiz_inexistente_falha_claro(self):
        cod, saida = self.roda("--dir", "nao/existe")
        self.assertEqual(cod, 1)
        self.assertIn("não existe", saida)


class TestKitConsistente(unittest.TestCase):
    """O kit valida a si mesmo: comandos, caminhos, scripts e links."""

    def test_referencias_do_kit_consistentes(self):
        cod, saida = roda_lint("--check-kit")
        self.assertEqual(cod, 0, saida)

    def test_repo_limpo_nao_e_erro(self):
        """Kit recém-clonado não tem feature — e isso não reprova o build."""
        cod, saida = roda_lint()
        self.assertEqual(cod, 0, saida)


if __name__ == "__main__":
    unittest.main(verbosity=2)
