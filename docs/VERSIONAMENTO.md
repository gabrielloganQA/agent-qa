# Versionamento — do kit e dos artefatos

Responde: **o que é versionado, como, e como um QA recebe correção do kit sem perder o
trabalho dele.**

---

## 1. Os três eixos — não confunda

| Eixo | Exemplo | Onde | Quem incrementa |
|---|---|---|---|
| **Kit** — skills, scripts, convenções | `v1.0.0` | `VERSION` + tag git | QA leader, por PR |
| **Produto sob teste** | `v2.3.0` | `test/releases/v2.3.0.md` | quem libera a release |
| **Execução** | `2026-07-22-build482` | `test/runs/*.json` | o CI, automático |

Erro comum: usar a versão do produto para marcar mudança no kit. São ciclos
independentes — o kit pode ficar 3 meses parado enquanto o produto solta 8 releases.

---

## 2. Versão do kit — semver

| | Quando incrementar |
|---|---|
| **MAIOR** `2.0.0` | muda convenção que **invalida artefato existente** — tag obrigatória nova, formato de arquivo, regra de lint que reprova o que antes passava. **Exige migração.** |
| **MENOR** `1.1.0` | skill nova, referência nova, regra de lint nova que ainda não reprova nada existente |
| **CORREÇÃO** `1.0.1` | texto, bug de script, sem mudança de contrato |

Toda mudança entra por **PR**, com entrada no `CHANGELOG.md` e dono no `CODEOWNERS`.
**Skill é código** — não é documento que alguém edita direto na main.

```bash
git tag -a v1.1.0 -m "adiciona qa-auditoria e regra de hash do requisito"
git push --tags
```

---

## 3. 🔴 O problema do `cp -r` — e como resolver

`cp -r qa-example meu-projeto` é **fork**. Dez QAs copiam, você corrige uma skill, e
ninguém recebe. Em três meses existem dez versões divergentes e nenhuma é a verdadeira.

### A separação que resolve

| | Muda com que frequência | De quem é |
|---|---|---|
| **Ferramenta** — `.claude/` (skills, hooks, prompts, settings.json), `test/scripts/`, `docs/`, `templates/`, `.github/`, `CLAUDE.md` | raramente, e para todos ao mesmo tempo | do time |
| **Artefatos** — `test/cases/`, `runs/`, `sessoes/`, `metricas/`, `releases/`, `bugs/` | toda semana, e só naquele projeto | do QA daquela feature |

⚠️ `.claude/settings.local.json` **não** é da ferramenta: é a preferência pessoal
de cada QA (quais MCPs aprovou). Nunca entre nele no `checkout` de atualização.

O projeto do QA é um repositório próprio. A ferramenta vem de fora, por caminho
explícito:

```bash
# uma vez, no projeto de teste
git remote add kit <url-do-repositorio-do-kit>

# quando quiser atualizar a ferramenta
git fetch kit --tags
git checkout kit/v1.2.0 -- \
  .claude/skills .claude/hooks .claude/settings.json .claude/prompts \
  test/scripts docs templates .github CLAUDE.md .mcp.json
git commit -m "chore: atualiza kit de v1.1.0 para v1.2.0"
echo "1.2.0" > VERSION
```

Depois de atualizar, confirme que o kit chegou íntegro:

```bash
python3 test/scripts/qa_lint.py --check-kit
python3 -m unittest discover -s test/scripts/tests
```

O `checkout -- <caminhos>` traz **só** as pastas da ferramenta. `test/cases/`,
`test/runs/` e o resto do trabalho do QA não são tocados.

### Por que não submódulo ou subtree

Submódulo quebra a premissa de "um arquivo, um lugar" — o QA precisa lembrar de
`git submodule update`, e esquece. Subtree esconde a origem no histórico. O
`checkout` por caminho é explícito, visível no diff e não precisa que ninguém aprenda
nada novo.

---

## 4. Migração quando a versão MAIOR muda

Mudança MAIOR invalida artefato existente. Exemplo: se `@camada:` virar obrigatória e
existirem 200 cenários sem ela, o lint reprova tudo no dia seguinte.

Regra: **toda versão MAIOR vem com uma seção de migração no `CHANGELOG.md`**, dizendo o
que reprova e como corrigir em lote. Sem isso, o time desliga o lint — e aí o sistema
morreu.

```markdown
## [2.0.0] — Migração

`@camada:` passa a ser obrigatória em todo cenário.

Para migrar:
  <o comando de migração acompanha a versão, nesta seção>
Depois rode o lint e revise o que ele apontar.
```

O script de migração é escrito junto com a mudança MAIOR e entra no mesmo PR.
Não existe um migrador genérico — cada mudança de convenção quebra uma coisa
diferente.

---

## 5. Versionamento dos artefatos — já resolvido pelo Git

Não precisa de mecanismo novo:

| Pergunta | Resposta |
|---|---|
| Quem mudou este caso e quando? | `git blame` no `.feature` |
| Quem aprovou? | tag `@aprovado-por:<usuario> @data:<AAAA-MM-DD>` |
| O requisito mudou depois de eu escrever os casos? | hash no cabeçalho da `MATRIZ.md`; o lint reprova |
| Por que este caso existe? | `CT-XX → RN-XX → lacuna → resposta do PO`, tudo versionado |
| Este caso já falhou antes? | histórico de `test/runs/` |
| Quem liberou a v2.3.0 e com qual ressalva? | `test/releases/v2.3.0.md`, assinado |

**Caso aposentado nunca tem o ID reciclado** — vira `@obsoleto:AAAA-MM-DD`. É isso que
permite comparar cobertura entre releases sem mentir.

---

## 6. O que fazer agora

O kit ainda **não está em git**. Enquanto não estiver:

- não há tag, não há `git blame`, não há PR, não há `CODEOWNERS` valendo
- o portão 2 (aprovação) é convenção, não mecanismo
- atualizar o kit de dez QAs é trabalho manual

Ordem sugerida:

1. `git init` no kit, primeiro commit, `git tag v1.0.0`
2. Publicar num remoto que o time alcance
3. Ajustar o `README` para `git clone` em vez de `cp -r`
4. Configurar `CODEOWNERS` com os usuários reais (hoje tem placeholders)
5. Rodar o `qa-lint` no CI do repositório de cada projeto de teste
