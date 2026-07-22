---
name: qa-intake
description: Abre o teste de uma feature — recebe a documentação, aponta ambiguidades e faz o questionário que define o que pode ser testado. Use antes de qualquer outro comando de QA.
---

# /qa-inicio — abertura da feature

## 1. Peça a documentação

Aceite texto colado, arquivo ou link. Se não houver documento, avise que a
feature entra como "documentação fraca" e que Exploratory Testing passa a ser a
técnica dominante — e ofereça levantar as regras explorando o app.

## 2. Aponte as ambiguidades ANTES de perguntar qualquer outra coisa

Leia as regras e liste o que **muda o desenho do teste**:

- regra sem desfecho definido ("o sistema revalida" — e depois?)
- fronteira mal fechada ("acima de R$100" — e exatamente R$100?)
- conflito entre regras
- critério de aceite sem número ("não pode ficar mais lento")

Pergunte ao QA. O que ficar sem resposta vira caso `bloqueado` na execução —
**nunca** comportamento chutado.

## 3. Questionário

⚠️ **Use AskUserQuestion, UMA pergunta por chamada, com opções clicáveis.**
Nunca despeje a lista em texto. Na descrição de cada opção explique **o efeito**
da escolha — o QA precisa saber o que está liberando ou travando.

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

## 4. Travas derivadas — obedeça sem exceção

- Sem banco → **não sugira nenhum caso de validação em banco.** Nem como opcional,
  nem como "seria bom ter". Simplesmente não existe.
- Sem autorização de segurança → nada de SQLi, JWT, IDOR.
- Sem cache/fila/retry → nada de consistência eventual.
- Sem contrato de API → nada de teste de API.

## 5. Grave `test/contexto.json`

```json
{
  "feature": "...", "aplicacao": "...", "versao": "...", "ambiente": "...",
  "executor": "...", "project_id_ap": null,
  "permissoes": { "acesso_banco": false, "acesso_logs": true,
                  "teste_seguranca_autorizado": true, "cadastrar_bug_no_ap": true },
  "contexto_tecnico": { "contrato_api": "Swagger", "tem_cache": false,
                        "tem_fila_assincrona": true, "relatorio_cobertura": null },
  "_efeitos": { "acesso_banco=false": "NÃO sugerir validação em banco" },
  "_pendencias_da_especificacao": ["..."]
}
```

O bloco `_efeitos` não é enfeite: é o que você relê nas conversas seguintes para
não esquecer uma trava.

**Próximo:** `/qa-casos`
