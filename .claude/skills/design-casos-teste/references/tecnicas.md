# Técnicas de derivação — como aplicar cada uma

Referência carregada ao escolher a técnica. O `SKILL.md` diz *quando* disparar cada
uma; aqui está *como* aplicar e o erro típico de cada.

> A técnica não é etiqueta decorativa: ela determina **quantos casos existem** e
> **quais valores entram**. Declarar a técnica sem seguir o procedimento produz caso
> que parece derivado e não é.

---

## Particionamento de Equivalência

**Dispare quando:** a regra tem faixas ou categorias de entrada.

**Procedimento:** divida o domínio em classes onde o sistema se comporta igual. Uma
classe válida e as inválidas ao redor. Um caso por classe — mais que isso é redundância.

```
Idade para desconto sênior (≥60):
  inválida: < 0        →  1 caso
  válida:   0..59      →  1 caso (não recebe)
  válida:   ≥60        →  1 caso (recebe)
```

**Erro típico:** três casos dentro da mesma classe (61, 65, 70 anos) achando que é
cobertura. É o mesmo caso escrito três vezes.

---

## Análise de Valor Limite (BVA)

**Dispare quando:** há limite numérico, data, tamanho ou quantidade.

**Procedimento:** para cada fronteira, teste **o valor exato, um abaixo e um acima**.
Fronteira de faixa fechada testa os dois extremos.

```
Pedido mínimo R$50,00:
  49,99  recusa
  50,00  aceita     ← a fronteira é o caso que mais pega bug
  50,01  aceita
```

**Erro típico:** testar só "acima" e "abaixo" e pular o valor exato. É nele que mora o
`>` que deveria ser `>=`.

**Atenção ao arredondamento:** valor monetário com percentual quase sempre tem um caso
de meio-centavo. `129,94 × 8% = 10,3952` distingue arredondamento de truncamento.

---

## Tabela de Decisão

**Dispare quando:** a regra combina condições que produzem ações diferentes.

**Procedimento:** monte a tabela com todas as combinações relevantes, marque as
impossíveis, e derive um caso por coluna restante.

| Cupom ativo | Pedido ≥ mínimo | CPF elegível | → Resultado |
|---|---|---|---|
| sim | sim | sim | aplica |
| sim | sim | não | recusa (limite por CPF) |
| sim | não | — | recusa (mínimo) |
| não | — | — | recusa (inativo) |

**Erro típico:** explodir todas as combinações sem marcar as impossíveis, gerando casos
que não existem no mundo real.

---

## Transição de Estados

**Dispare quando:** há status, workflow ou ciclo de vida.

**Procedimento:** desenhe o grafo. Derive casos para **transições válidas** e,
principalmente, para as **inválidas** — é onde o bug mora.

```
Criado → Ativo → Esgotado
              ↘ Expirado
              ↘ Cancelado  (não volta para Ativo)
```

**Erro típico:** cobrir só o caminho feliz do grafo. A transição proibida que o sistema
permite é o defeito clássico dessa técnica.

---

## Teste de Caso de Uso

**Dispare quando:** há fluxo ponta a ponta com um ator.

**Procedimento:** um caso para o fluxo principal, um para cada extensão relevante.
É a técnica que justifica cenário `@camada:e2e` — e as extensões geralmente vão para
`api`.

---

## Pairwise / All-Pairs

**Dispare quando:** há muitos parâmetros independentes e a combinação explode.

**Procedimento:** cubra todos os **pares** de valores em vez do produto cartesiano.
4 parâmetros × 3 valores = 81 combinações → ~9 casos cobrindo todos os pares.

**Erro típico:** usar pairwise onde os parâmetros **não** são independentes. Se a
combinação específica importa (tipo de cupom × meio de pagamento), é Tabela de Decisão.

---

## Teste de Sintaxe

**Dispare quando:** o campo tem formato — CPF, e-mail, código, JSON, data.

**Procedimento:** derive do formato: válido canônico, cada caractere proibido, tamanho
mínimo, tamanho máximo, vazio, só espaços, unicode, string muito longa.

**Erro típico:** testar só "inválido" genérico. `"abc"` e `"111.111.111-11"` falham por
motivos diferentes e podem ter tratamentos diferentes.

---

## Teste de Domínio

**Dispare quando:** múltiplas variáveis são interdependentes.

**Procedimento:** para cada variável, um caso "on" (no limite) e um "off" (logo fora),
mantendo as demais em valor típico.

---

## Error Guessing

**Dispare quando:** há histórico de defeito, ponto notoriamente frágil, empate,
concorrência, ou "isso aqui sempre quebra".

**Procedimento:** não tem procedimento — tem experiência. Registre **por que** você
suspeitou; é o que permite outra pessoa avaliar o caso.

Alvos recorrentes: empate em ordenação, última unidade em estoque, clique duplo,
timeout no meio da transação, virada de dia/mês, fuso horário.

---

## Exploratory Testing

**Dispare quando:** área nova, documentação fraca, ou depois de mudança grande.

**Não vira Gherkin nem automação.** Vira charter com time-box e folha de sessão.
Ver [`testes-manuais.md`](testes-manuais.md).

---

## Checklist-Based

**Dispare quando:** há requisitos transversais que se repetem em toda tela ou endpoint
(acessibilidade, mensagens de erro, paginação, permissão).

**Procedimento:** um checklist versionado, aplicado a cada novo item. Não gera caso por
item — gera um caso de verificação do checklist.

---

## Aleatório / Estatístico

**Dispare quando:** volume, robustez ou carga.

**Procedimento:** entrada gerada com semente **registrada**, para o caso ser
reproduzível. Sem semente, a falha não volta.

---

## Classification Tree Method

**Dispare quando:** há hierarquia de classes de entrada.

**Procedimento:** monte a árvore de classificações, escolha a cobertura (mínima ou
pairwise entre folhas) e derive.

---

## Regra final

**A técnica escolhida entra como tag no cenário** (`@bva`, `@particionamento`…). Isso
permite ao `qa-auditoria` perguntar: *esta regra tem faixa numérica e nenhum caso
`@bva` — por quê?*

Cobertura por técnica é a única forma barata de auditar se a derivação foi feita ou se
alguém só escreveu o caminho feliz com nomes bonitos.
