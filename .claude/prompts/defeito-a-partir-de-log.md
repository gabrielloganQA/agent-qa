# Redigir defeito a partir de log de falha

**Quando usar:** a suíte ficou vermelha e você tem stack trace, resposta HTTP ou
log — mas ainda não tem o ticket. Passos ruins são o motivo nº 1 de bug devolvido
pelo dev.

**Antes:** confirme que existe **RN violada**. Sem ela não abre defeito — vira
lacuna (regra não documentada) ou sugestão (preferência).

---

```
A partir do log abaixo, monte o rascunho de defeito no modelo estrutural.

Produza JSON com estas chaves, e nada além delas:
  escopo, resumo, descricao, comportamento_atual, resultado_esperado,
  passos, ambiente, anexos, severidade, prioridade, impacto, caso_de_teste

Regras:
1. `resultado_esperado` vem da REGRA DE NEGÓCIO, citando a RN — nunca do que
   "deveria funcionar". Se você não consegue citar a RN, PARE e diga isso.
2. `passos` numerados, reproduzíveis por alguém que nunca viu a feature.
   Incluem massa necessária e estado inicial. Nada de "faça o fluxo normal".
3. `comportamento_atual` é o observado, com o dado concreto (status, valor,
   mensagem). Sem interpretação.
4. `severidade` começa pelo nível: "S2 — <descrição>". O script recusa sem isso.
   Se você não tem base para decidir o nível, escreva "S? — a definir" e diga
   que a escolha é do QA.
5. `impacto` é a consequência para o NEGÓCIO, não para o teste. "O teste falha"
   não é impacto.
6. Não invente `prioridade`: proponha e marque como a confirmar.

Depois do JSON, liste em texto:
  - o que no log NÃO deu para explicar
  - o que precisa ser confirmado manualmente antes de abrir

RN violada: [cite aqui]
Caso: [CT-XXX]
Log:
---
[cole aqui]
```

---

**O que costuma dar errado**

- **O modelo confunde sintoma com causa.** Stack trace aponta onde quebrou, não
  por quê. Se o `descricao` afirmar causa raiz, corte: diagnóstico é do dev.
- **Passos genéricos.** "Acesse o sistema e execute a operação" volta do dev em
  24h. Exija massa e valores concretos.
- **Severidade inflada.** Todo defeito parece S1 na hora que a suíte fica
  vermelha. Severidade é do QA, e é uma pergunta clicável no `/qa-defeito`.
