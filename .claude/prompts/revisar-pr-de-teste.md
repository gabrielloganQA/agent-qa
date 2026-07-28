# Revisar PR de teste com o checklist

**Quando usar:** portão 3 — revisão de spec, própria ou de terceiro, antes do
merge. Vale igualmente para código escrito por pessoa e por agente.

---

```
Revise o diff abaixo como revisor do portão 3. Não elogie, não resuma o que o
código faz: aponte o que devolve o PR.

Percorra nesta ordem e responda item a item com SIM/NÃO + evidência (arquivo e
linha). Qualquer SIM é motivo de devolução:

INTENÇÃO
 1. Alguma assertion falha por motivo diferente da intenção do teste?
 2. O valor esperado veio da EXECUÇÃO em vez do requisito? (pergunte de onde
    veio cada número literal)
 3. Existe cenário aqui que não corresponde a nenhuma RN documentada?

FRAUDE DE TESTE
 4. test.skip condicional, if/return, ou assertion frouxa (toBeTruthy em
    status, toContain([200,201]))?
 5. Timeout aumentado, retry acrescentado ou assertion removida para virar
    verde?

DETERMINISMO
 6. Teste depende de estado deixado por outro? describe.serial sem
    justificativa escrita?
 7. Espera por tempo fixo? Massa sem código único? Cleanup ausente? ID
    hardcoded?

CAMADA E ABSTRAÇÃO
 8. Regra de negócio testada em E2E que a API já provaria (ou vice-versa)?
 9. Massa criada pela tela em vez da API?
10. Helper com flag booleana servindo dois chamadores?

RASTREABILIDADE
11. Falta @CT-XXX no título ou no describe?
12. O CT citado existe em test/cases/?

Ao final, responda em uma linha: APROVA ou DEVOLVE, e o item decisivo.

Diff:
---
[cole aqui]
```

---

**O que costuma dar errado**

- **O modelo aprova o que ele mesmo escreveu.** Se a spec veio de um turno
  anterior desta conversa, abra um turno limpo para revisar — ou peça
  explicitamente que ele tente REFUTAR a spec.
- **Ele avalia estilo em vez de intenção.** Se a resposta falar de nomes de
  variável e formatação antes de falar de assertion, o prompt não pegou; repita
  pedindo o item 1 primeiro.
- **Falta o contexto do requisito.** Sem a RN à vista, ninguém consegue
  responder o item 2. Cole também o trecho relevante do `REGRAS.md`.
