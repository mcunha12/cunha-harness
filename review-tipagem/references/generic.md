# Tipagem: princípios agnósticos de linguagem

Cada item: sinal, impacto, correção.

## Teste de honestidade

Um tipo é honesto quando todo valor do tipo pode existir em runtime e todo valor que existe em runtime cabe no tipo. Dois defeitos:

- Tipo largo demais: aceita valores que o domínio proíbe (`status: string`, `{ a?: X; b?: Y }` que exige um dos dois).
- Tipo estreito demais ou falso: afirma garantias que o runtime não dá (`as Foo` sobre JSON, `!` sobre mapa).

Para cada mudança de tipo no diff, pergunte: qual valor real quebra essa afirmação, e quem o produz?

## Parse, don't validate

Dado externo entra como `unknown` (TS), `object`/`Any` não confiável (Python) ou `interface{}`. Uma função de borda devolve o tipo refinado ou falha. O resto do código só recebe o tipo refinado.

- Sinal: o mesmo `if (x.foo)` repetido em vários pontos, porque o tipo não garante `foo`. Impacto: cada ponto reimplementa a checagem de forma diferente. Correção: refinar uma vez na borda.
- O dono da validação em runtime é o review-contratos. O dono do tipo que sai dela é o review-tipagem.

## Estados ilegais

- Procure grupos de campos que só fazem sentido combinados: `(loading, error, data)`, `(startedAt, endedAt)`, `(paymentMethod, cardToken)`.
- Modele como união etiquetada (sum type) com um discriminador literal. O compilador então exige o tratamento de cada caso e impede o acesso a campo de outro estado.
- O custo da modelagem pobre é o bug de combinação, e ele aparece em estados raros (erro com dado em cache, cancelamento durante pagamento).
- Em linguagem sem sum type (Java antigo, Go), use tipos distintos por estado ou construtor privado que valida.

## Exaustividade

- Toda decisão sobre união fechada precisa falhar na compilação quando um caso novo aparece. TS: `never` no `default`. Python: `assert_never` em `match`. Rust e Kotlin: `when`/`match` exaustivo.
- Dado que vem da rede e pode ganhar valor novo degrada com um caso desconhecido explícito.

## Tipos nominais para valores intercambiáveis

- Dois valores do mesmo tipo primitivo que o domínio não permite trocar (ID de aluno e ID de turma, centavos e reais, segundos e milissegundos) merecem tipo nominal: brand em TS, `NewType` em Python, tipo struct em Go/Rust.
- Custo: um construtor por tipo. Benefício: a troca de argumentos não compila.
- Aplique onde há função com 2 ou mais parâmetros do mesmo primitivo e semânticas diferentes, ou no tipo que já causou bug.
- Value object com invariante (CPF válido, dinheiro com moeda) é do review-clean.

## Nulidade

- Um tipo por significado: ausente (`undefined`/opcional), sem valor (`null`), vazio (`""`, `[]`). Função que devolve os três sem distinção força o chamador a tratar os três.
- Prefira retorno que torna a ausência explícita (`T | undefined`, `Option`, `Result`) a sentinelas (`-1`, `""`, `0`).
- Lista nunca é nula. Devolva `[]`.
- Campo anulável no tipo e tratado como obrigatório no uso é erro de modelagem. Corrija o lado mentiroso.

## Erros como tipo

- Função que pode falhar de forma esperada (validação, não encontrado) devolve `Result<T, E>` ou lança erro tipado e documentado. O tipo de retorno `T | null` sem explicar o motivo da falha apaga a informação.
- Em TS, `catch (e)` é `unknown`: estreite com `instanceof` antes de usar. Erro lançado que não é `Error` (`throw 'texto'`) quebra `instanceof`.

## Derivar, não copiar

- Cada tipo tem uma fonte de verdade: schema, banco, OpenAPI, função. As outras representações derivam por operador de tipo ou geração.
- Cópia manual envelhece sem alarme. O sinal é a lista de campos idêntica ou quase em dois arquivos.
- Derivação cria acoplamento intencional: mudar a fonte muda os derivados. Em fronteira de pacote versionado, deriva-se do tipo publicado.

## Estruturas de dados

- Mapa indexado por string devolve ausência para chave inexistente. O tipo precisa dizer isso, ou o chamador precisa verificar.
- Estruturas imutáveis (readonly, frozen, tuple) em parâmetros e constantes impedem mutação acidental e aliasing.
- Coleção heterogênea vira tupla ou objeto nomeado.

## Complexidade de tipos

- Um tipo que ninguém do time lê é dívida. Regra de bolso: se a mensagem de erro do compilador passa de 10 linhas, simplifique.
- Generic só existe para relacionar dois ou mais pontos (entrada com saída, parâmetro com retorno). Parâmetro de tipo usado uma vez pode ser removido.
- Condicionais e mapped types em código de aplicação são cheiro. Em biblioteca interna de utilitários, são aceitáveis com teste de tipo.

## Rigor gradual e migração

- Em repo legado, o objetivo é não regredir. O diff novo precisa ser estrito, mesmo que o resto não seja.
- Cada supressão (`@ts-expect-error`, `# type: ignore[code]`, `eslint-disable`) leva código de erro, motivo em uma linha e, se temporária, ticket.
- Afrouxar config global para fazer um diff compilar é achado, e a alternativa é corrigir o diff ou isolar com supressão local.
