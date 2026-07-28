# Extrair regras de negócio de ata de reunião

**Quando usar:** a feature não tem documento formal, só a ata (ou a transcrição)
de uma reunião de refinamento. Situação mais comum do que se admite.

**Antes:** avise que o requisito nasce **derivado** — não foi fornecido nem
confirmado pelo PO — e que toda RN daí é premissa até ele confirmar.

---

```
Abaixo está a ata de uma reunião de refinamento. Extraia dela as regras de
negócio testáveis.

Para cada regra candidata, produza uma linha com:
  - o enunciado, com o DESFECHO explícito
  - a frase exata da ata que a originou, entre aspas
  - quem falou, se a ata identificar

Regras do trabalho:
1. Regra sem desfecho NÃO é regra. "O sistema revalida o saldo" é meia frase —
   revalida e daí? Se você não consegue escrever o resultado esperado, é
   LACUNA, não RN.
2. Não invente número, prazo ou limite que a ata não diz. "Não pode ficar mais
   lento" vira lacuna, não "< 2s".
3. Discordância entre participantes é LACUNA, não a opinião do mais graduado.
4. Separe a saída em três blocos:
     REGRAS       — enunciado testável + citação
     LACUNAS      — o que ficou em aberto + o impacto de não responder
     FORA DE ESCOPO — o que foi discutido e explicitamente adiado

Ata:
---
[cole aqui]
```

---

**O que costuma dar errado**

- **O modelo transforma discussão em decisão.** Quando dois participantes
  divergem e ninguém conclui, ele escolhe um e escreve como regra. Confira toda
  RN contra a citação: se a citação for uma pergunta, é lacuna.
- **Verbos de intenção viram regra.** "A gente devia validar o CPF" não é regra
  — é intenção. Regra é o que o sistema faz.
- **Ata longa faz o modelo resumir o começo e detalhar o fim.** Em ata acima de
  ~40 minutos, quebre em blocos e rode uma vez por bloco.
