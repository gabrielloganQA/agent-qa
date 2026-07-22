# Agente executando contra o ambiente — guardrails

Referência carregada quando um agente vai **operar o produto** (navegador, app, API)
em vez de apenas escrever arquivos.

---

## 1. A divisão que não se negocia

> **O agente explora, autora e diagnostica. A regressão é código determinístico.**

| Atividade | Quem faz | Por quê |
|---|---|---|
| Exploração guiada | **Agente**, dirigido pelo QA | O valor é a variabilidade; o agente é a mão |
| Autoria de caso e de spec | **Agente** | Trabalho repetitivo com revisão humana depois |
| Diagnóstico de falha | **Agente** | Ler log, rede, console e correlacionar é onde ele é bom |
| Reprodução de defeito | **Agente**, com confirmação humana | Precisa ser reproduzível por outra pessoa |
| **Regressão oficial** | **Código determinístico** | Precisa dar o mesmo resultado toda vez |
| **Parecer de release** | **Pessoa** | Decisão de risco tem nome |

### Por que a regressão não pode ser do agente

Um agente decide **em runtime** como interagir com a tela. Duas execuções do mesmo
cenário podem seguir caminhos diferentes — clicar em outro elemento, esperar de outro
jeito, interpretar o estado de outra forma. Isso é exatamente o que se quer na
exploração e exatamente o que **não** se quer numa suíte que serve de critério de saída.

Consequências de usar agente como regressão:

- **O resultado não é comparável entre builds.** "Passou" numa execução e "falhou" na
  seguinte pode ser o agente, não o produto — e você não tem como distinguir.
- **Não existe diff.** Spec versionada mostra o que mudou; prompt não.
- **O verde não é auditável.** Ninguém consegue dizer *o que exatamente* foi verificado.

➡️ Se o agente executou, o resultado é **evidência de exploração**, não linha de
regressão. Registre em `test/sessoes/`, nunca como run oficial em `test/runs/`.

---

## 2. Como registrar execução feita por agente

Sessão de agente vira **folha de sessão**, com o mesmo peso de uma sessão exploratória
humana:

```
test/sessoes/2026-07-22-cupons-agente.md
```

Conteúdo mínimo: charter, build e ambiente, o que foi tentado, o que foi observado,
achados, e **o que virou caso novo ou defeito**.

Se um achado precisar entrar na regressão, ele vira `@CT-XX` na matriz e depois **spec
determinística** — nunca o log do agente como prova.

### O campo `executado_por`

`test/runs/*.json` aceita `executado_por: "qa"` (execução humana) e
`executado_por: "ci"` (suíte determinística). **`"agente"` não é resultado oficial** —
se aparecer, o `qa-lint` reprova e o relatório do PMO não computa.

---

## 3. Ambiente e credenciais

- **Ambiente de QA apenas.** Credencial de produção nunca entra em configuração de
  agente, nem "só para olhar".
- Segredos vêm do cofre do CI ou de variável de ambiente. **Nunca em arquivo de
  configuração de MCP**, que costuma ser versionado.
- Usuário de serviço dedicado, com o mínimo de permissão necessária. Quando a pessoa
  sai da empresa, a automação não morre junto — e o histórico não fica com o nome errado.
- Dado pessoal sempre anonimizado.

---

## 4. Segurança de MCP

O servidor MCP é dependência de software e **a descrição de cada ferramenta é, para o
modelo, instrução**. Isso muda o que "confiar numa ferramenta" significa.

- **Allowlist com versão fixada.** Atualizar servidor MCP é mudança de dependência:
  entra por PR, com revisão.
- **Tool poisoning:** um servidor comprometido pode alterar a descrição de uma
  ferramenta para induzir comportamento. Servidor de terceiro só entra depois de
  auditoria do que ele expõe.
- **Nunca dê ao agente ferramenta de escrita que ele não precisa** para a tarefa. Um
  agente de exploração precisa navegar e ler — não precisa apagar registro.
- Skill de terceiro roda com as permissões de quem a executa. Auditoria antes de instalar.

---

## 5. Contaminação de setup — a armadilha prática

Montar estado escrevendo direto em `localStorage`, `sessionStorage` ou banco **não
equivale** a montar pela interface: a aplicação pode não re-renderizar e o agente
registra falha que não existe.

➡️ **Diante de falha inesperada, refaça pela interface antes de reportar.**

Isso já aconteceu neste repositório: um "defeito" no Reset App State foi, na primeira
tentativa, artefato de estado injetado por fora. Refeito com cliques, o defeito se
confirmou — mas poderia não ter se confirmado, e um ticket falso teria sido aberto.

---

## 6. Log da sessão

Toda sessão de agente contra o ambiente registra o que foi chamado: URLs visitadas,
ações executadas, requisições observadas. Sem isso não há como responder "o que o
agente fez às 14h?" depois de um incidente no ambiente compartilhado.

O log entra na folha de sessão, resumido — não o transcript inteiro.

---

## 7. Checklist antes de soltar o agente no ambiente

- [ ] É exploração, autoria ou diagnóstico? (Se for regressão, **pare**.)
- [ ] Ambiente de QA, com build identificado?
- [ ] Credencial de serviço, sem acesso de produção?
- [ ] O QA está dirigindo, ou o agente vai navegar sozinho? (Sozinho: só com charter escrito.)
- [ ] Servidores MCP na allowlist, versão fixada?
- [ ] Sabe onde a folha de sessão vai ser gravada?
- [ ] Combinado que achado vira `@CT` ou defeito — e não linha de regressão?
