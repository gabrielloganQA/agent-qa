---
name: qa-intake
description: Abre o teste de uma feature — recebe a documentação, registra o requisito, extrai as regras numeradas, aponta as ambiguidades e faz o questionário que define o que pode ser testado. Use antes de qualquer outro comando de QA.
---

# /qa-intake — abertura da feature

Transforma a documentação crua da feature em **matéria-prima rastreável**: requisito
versionado, regras numeradas, lacunas registradas e travas de teste declaradas.

Entrada: documentação da feature (texto, arquivo ou link).
Saída: `test/requisitos/RF-XX-<slug>.md` · `test/cases/<feature>/REGRAS.md` ·
`test/cases/<feature>/LACUNAS.md` · `test/contexto.json`.

⚠️ **Os quatro arquivos são obrigatórios.** O `design-casos-teste` recebe o requisito e
o `REGRAS.md` como entrada, e o `qa_lint.py` reprova a feature que não tiver
`REGRAS.md` e `LACUNAS.md`. Terminar o intake só com o `contexto.json` quebra a corrente.

---

## 1. Peça a feature com as regras

Aceite texto colado, arquivo ou link. Peça explicitamente **as regras de negócio**, não
só a descrição da feature.

Se não houver documento, avise que a feature entra como "documentação fraca" e que
Exploratory Testing passa a ser a técnica dominante — e ofereça levantar as regras
explorando o app. Nesse caso o requisito nasce marcado como **derivado**, e toda RN é
premissa até o PO confirmar.

## 2. Registre o requisito

Grave a matéria-prima crua em `test/requisitos/RF-XX-<slug>.md` — um arquivo por RF.
É ele que responde "por que este caso existe?" seis meses depois.

```markdown
# RF-12 — Transferência entre contas

**Aplicação:** ... · **Origem:** Jira PROJ-4471 · **Hash da fonte:** a1b2c3d4e5f6
**Levantado por:** ... · **Revisado por:** ...

[o texto da regra como veio, sem reescrever]
```

- Fonte no Jira ou Confluence → guarde **link + hash**. Sem isso ninguém prova o que
  foi lido.
- Requisito derivado por exploração → abra o arquivo com o aviso de que **não foi
  fornecido nem confirmado por PO**.

⚠️ Não edite o requisito para "melhorar" a redação. Ele é a fonte; o `qa_lint.py`
tira `sha256` dele e reprova a matriz quando ele muda sem revisão dos casos.

## 3. Extraia as regras numeradas

Quebre o requisito em `RN-XX`, uma regra testável por linha, em
`test/cases/<feature>/REGRAS.md`:

```markdown
# Regras de negócio — <feature> (RF-XX)

Extraídas de [`RF-XX-<slug>.md`](../../requisitos/RF-XX-<slug>.md).

| Regra | Origem | Enunciado |
|---|---|---|
| **RN-01** | RF-12 | Enunciado testável, com o desfecho explícito. |

## Regras nascidas de lacuna

Quando a resposta do PO cria uma regra que não estava no documento, ela entra aqui com
origem na **lacuna**, não no requisito: `| RN-08 | L-03 | ... |`
```

Regra boa tem **desfecho**. "O sistema revalida o saldo" não é regra — é meia frase.
Se você não consegue escrever o resultado esperado, não é RN: é lacuna, vai para o
passo 4.

**Mostre as RN ao QA e espere confirmação** antes de seguir. Numeração errada
contamina matriz, casos e defeitos.

## 4. Aponte as ambiguidades e grave as lacunas

Liste o que **muda o desenho do teste**:

- regra sem desfecho definido ("o sistema revalida" — e depois?)
- fronteira mal fechada ("acima de R$100" — e exatamente R$100?)
- conflito entre regras
- critério de aceite sem número ("não pode ficar mais lento")

Grave tudo em `test/cases/<feature>/LACUNAS.md`, com data e responsável pela resposta,
em duas seções: **Abertas** e **Respondidas**. Cada lacuna leva `L-XX`, a pergunta e o
**impacto se não for respondida**.

O que ficar sem resposta vira caso `bloqueado` na execução — **nunca** comportamento
chutado. Cenário que dependa de lacuna aberta leva `@premissa` e fica fora da suíte
oficial.

## 5. Questionário

⚠️ **Use AskUserQuestion, UMA pergunta por chamada, com opções clicáveis.**
Nunca despeje a lista em texto. Rótulo curto e uma frase por opção dizendo **o que
libera ou trava** — o QA decide rápido, não estuda o repositório.

Pule o que a documentação já responder e diga o que preencheu sozinho.

| # | Pergunta | Opções |
|---|---|---|
| 1 | Ambiente | Homolog · Stage · Dev · Produção |
| 2 | Acesso ao banco? | Leitura e escrita · Só leitura · Não |
| 3 | Acesso a logs? | Sim · Não |
| 4 | Contrato de API? | Swagger/OpenAPI · Collection Postman · Não existe |
| 5 | Cache, fila ou retry? | Fila · Cache · Os dois · Nenhum |
| 6 | Segurança autorizada? | Sim · Não · Só com aviso prévio |
| 7 | Relatório de cobertura? | Sim · Não |
| 8 | Projeto no AP | liste os reais: `curl -s -H "authtoken: $RISE_AUTH_TOKEN" "$RISE_BASE_URL/api/projects"` |

Depois, em texto: **nome do executor** (assina o relatório do PMO).

## 6. Travas derivadas — obedeça sem exceção

- Sem banco → **não sugira nenhum caso de validação em banco.** Nem como opcional,
  nem como "seria bom ter". Simplesmente não existe.
- Sem autorização de segurança → nada de SQLi, JWT, IDOR.
- Sem cache/fila/retry → nada de consistência eventual.
- Sem contrato de API → nada de teste de API.

## 7. Grave `test/contexto.json`

```json
{
  "feature": "...", "aplicacao": "...", "versao": "...", "ambiente": "...",
  "executor": "...", "project_id_ap": null,
  "permissoes": { "acesso_banco": false, "acesso_logs": true,
                  "teste_seguranca_autorizado": true, "cadastrar_bug_no_ap": true },
  "contexto_tecnico": { "contrato_api": "Swagger", "tem_cache": false,
                        "tem_fila_assincrona": true, "relatorio_cobertura": null },
  "_efeitos": { "acesso_banco=false": "NÃO sugerir validação em banco" },
  "_pendencias_da_especificacao": ["L-01 — ...", "L-02 — ..."]
}
```

O bloco `_efeitos` não é enfeite: é o que você relê nas conversas seguintes para
não esquecer uma trava. `_pendencias_da_especificacao` espelha as lacunas abertas.

## 8. Confira antes de encerrar

Checklist do intake — os quatro arquivos existem? As RN estão numeradas e confirmadas
pelo QA? As lacunas têm data e responsável pela resposta? Se não, o intake não terminou.

⚠️ **Não rode o `qa_lint.py` aqui esperando verde.** Ao fim do intake a pasta da
feature ainda não tem `.feature` — ele nasce no `/design-casos-teste` — e o lint
reprova com `estrutura: pasta sem nenhum .feature`. Isso é o estado **correto** de uma
feature entre o intake e o desenho, não um defeito. Rode o lint depois do portão 2.

**Próximo:** `/design-casos-teste`
