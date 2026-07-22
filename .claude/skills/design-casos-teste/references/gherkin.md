# Convenções de escrita de cenário

Referência carregada ao escrever `.feature`.

---

## 1. Declarativo, nunca imperativo

Cenário imperativo narra teclas e cliques; declarativo descreve comportamento. O
primeiro morre no próximo redesign; o segundo sobrevive porque regra de negócio é mais
estável que UI.

```gherkin
# ❌ imperativo
Dado que estou na página de login
Quando eu digito "joana@exemplo.com" no campo e-mail
E eu digito "senha123" no campo senha
E eu clico no botão "Entrar"
E eu clico em "Meus pedidos"
Então eu vejo "PayFlow" na tela

# ✅ declarativo — o "como" vive no step definition
Dado que estou autenticada como cliente com um pedido em aberto
Quando eu consulto meus pedidos
Então vejo o pedido em aberto com status "Aguardando pagamento"
```

**Escreva como se não existisse UI.** Se o cenário menciona botão, campo ou tela, ele
provavelmente é imperativo. Exceção legítima: quando o comportamento da própria tela é
o objeto do teste.

---

## 2. Tamanho e foco

- **De 3 a 7 passos.** Acima disso, quase sempre são vários comportamentos no mesmo
  cenário — divida.
- **Um comportamento por cenário.** O título é o "Então" resumido em uma linha.
- **Sem passo de conjunção.** `Dado que faço login e vou para o carrinho` são dois
  passos — existe `E` para isso.

---

## 3. Título

Padrão: **`<resultado observável>` quando `<condição>`**, em minúsculas, sem jargão de
implementação.

```
❌ testa GetQuantitativeReportRawQuery
❌ teste 3 do cupom
❌ valida o método aplicarDesconto
✅ desconta o reservado do disponível
✅ recusa cupom expirado e mantém o valor original do pedido
```

Nome que descreve método amarra o teste ao nome interno da função: quando o método é
renomeado, o teste mente.

---

## 4. Estrutura do arquivo

```gherkin
# language: pt
@feature:cupons @app:PayFlow @sprint:3
Funcionalidade: Aplicação de cupom de desconto

  Como cliente da loja
  Quero aplicar um cupom no checkout
  Para pagar menos

  Contexto:
    Dado que estou autenticada como cliente ativa

  @CT-007 @RN-03 @bva @camada:api @suite:regressao @ia-gerado @aprovado-por:fulano
  Esquema do Cenário: fronteiras do valor mínimo do pedido
    Dado que o pedido soma "<valor>"
    Quando eu aplicar o cupom "PROMO123"
    Então o resultado deve ser "<resultado>"

    Exemplos:
      | valor  | resultado |
      | 49,99  | recusado  |
      | 50,00  | aceito    |
      | 50,01  | aceito    |
```

- **`Contexto`** para pré-condição repetida — não cole o mesmo `Dado` em todo cenário.
- **Um arquivo por feature**, não um por micro-cenário.

---

## 5. `Esquema do Cenário` — com parcimônia

Ótimo para **partição e BVA da mesma regra**: entradas e saídas lado a lado, e um caso
novo custa uma linha.

Péssimo para amontoar **regras diferentes** na mesma tabela — vira um cenário que
ninguém entende quando falha, porque a linha 7 testa outra coisa que a linha 2.

Regra: uma tabela, uma regra.

---

## 6. Steps organizados por conceito de domínio

Step acoplado à feature (`Dado que estou na tela de checkout do cliente premium`) gera
explosão de steps e duplicação. Organize por **conceito de domínio**:

```
✅ Dado que estou autenticada como <perfil>
✅ Dado que existe um cupom <tipo> de <valor>
❌ Dado que estou na tela de checkout do cliente premium com cupom aplicado
```

Antes de escrever um step novo, **procure o existente**. Suíte com 400 steps para 60
cenários é sintoma de que ninguém procurou.

---

## 7. Tags obrigatórias

| Tag | Para quê |
|---|---|
| `@CT-XX` | ID do caso, sequencial por feature, **nunca reciclado** |
| `@RN-XX` | regra de negócio de origem |
| `@camada:` | `api` · `banco` · `contrato` · `e2e` · `performance` · `seguranca` · `manual` |
| `@suite:` | `smoke` · `regressao` · `nightly` · `release` |
| `@ia-gerado` | origem — **nunca removida** |
| `@nao-aprovado` | fora da suíte oficial até o QA aprovar |
| `@aprovado-por:<usuario>` | quem assumiu a responsabilidade |
| `@premissa` | comportamento suposto; espera resposta do PO |
| `@prioridade:` | `alta` · `media` · `baixa`, por risco |
| `@quarentena` | flaky, com prazo |
| `@obsoleto:<data>` | aposentado; o ID não volta a ser usado |
| técnica | `@bva`, `@particionamento`, `@tabela-decisao`… |

O `qa-lint` lê cada uma. Tag faltando reprova o PR.

---

## 8. O cenário é documentação viva

Se ele só faz sentido para quem conhece o código, perdeu a função. O critério é: **o PO
consegue ler e dizer se está certo?**

Quando não conseguir, o problema geralmente é imperatividade — voltou a narrar
mecânica em vez de descrever comportamento.
