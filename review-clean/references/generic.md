# Clean: referência agnóstica de stack

## Como medir "motivo de mudança"

Para uma unidade (classe, função, componente), liste os atores que pedem mudança nela: produto (regra), infra (banco, fila, vendor), apresentação (formato, texto), integração (contrato externo). Dois ou mais atores = candidato a SRP. Confirme com `git log --oneline -- <arquivo>`: commits recentes por razões diferentes provam divergent change.

## Heurísticas de tamanho que viram achado

| Medida | Limiar de atenção | Observação |
|---|---|---|
| Parâmetros posicionais | 4+ | 3+ do mesmo tipo já justifica objeto |
| Níveis de aninhamento | 4+ | 3 com `else` é guard clause pendente |
| Linhas de função | 60+ | só com 3+ níveis de abstração misturados |
| Dependências injetadas | 6+ | sinal de SRP, confirme por motivo de mudança |
| Métodos públicos de classe | 12+ | sem coesão de estado entre eles |
| `case` do mesmo switch repetido | 2 funções | OCP |

Limiar é sinal para abrir o código. O achado exige o dano concreto.

## SOLID: gatilhos práticos

- SRP: o nome da unidade exige "e" para descrever (`validaESalvaEEnvia`). O teste da unidade exige mockar 4+ coisas.
- OCP: adicionar o próximo tipo exige editar N arquivos. Meça N com `git grep` pelo `kind`/`type`/enum.
- LSP: o caller faz `if (x instanceof Y)`. A subclasse lança em método herdado. O override retorna tipo mais fraco.
- ISP: implementação vazia de método de interface. `Partial<Mock>` com 1 método usado.
- DIP: `new` de classe de IO fora da raiz de composição. `Date.now()` em regra de negócio. Import direto de client dentro de regra.

## Efeitos colaterais: como achar

1. Para cada função nova ou alterada, liste as chamadas de IO e as escritas (campo, global, parâmetro).
2. Compare com o nome. `get`, `is`, `has`, `calculate`, `format`, `validate`, `to*` prometem pureza.
3. Para funções chamadas em loop, render, `useMemo`, getter de classe ou retry, o efeito multiplica. Eleve a severidade.
4. Procure `Object.assign(param, ...)`, `param.x =`, `arr.sort()`, `arr.reverse()`, `splice`, `delete obj.k` em argumento.

## CQS: aceitável e inaceitável

Aceitável: `pop()`, `queue.dequeue()`, `upsert` que devolve o registro, `UPDATE ... RETURNING`. O nome comunica a escrita e a operação é atômica.
Inaceitável: consulta com nome neutro que escreve, ou comando que exige chamar uma consulta antes para o caller saber se funcionou, com janela de corrida.

## Estados nulos e erros

Escolha por intenção:

| Situação | Retorno |
|---|---|
| Ausência é normal (busca por id opcional) | `T \| undefined` / `Optional` / `null` documentado |
| Falha esperada que o caller trata | `Result`/union discriminada com a causa |
| Falha de programação ou invariante quebrada | exceção |
| Vários motivos de ausência | union com o motivo, nunca `null` |

`null` que significa "não existe", "sem permissão" e "falhou" ao mesmo tempo é MAJOR quando o caller decide algo sobre ele.

## Value objects: quando compensa

Compensa quando o conceito tem invariante (CPF válido, dinheiro não negativo, período com início antes do fim), operações próprias (somar, comparar, formatar) ou aparece em 3+ assinaturas. Um `type` alias sem validação não é value object. Sem invariante e sem operação, deixe o primitivo.

## Functional core: formato do refactor

```
// shell
const input = await load(id);
const decision = decide(input);
await apply(decision);
```

`decide` é pura, determinística, sem relógio e sem IO. Os testes do `decide` usam tabelas de entrada e saída. Os testes do shell usam fakes dos 2 adapters.

## Refactors: ordem segura a sugerir

1. Renomear e extrair função pura (sem mudar comportamento).
2. Introduzir parâmetro/objeto no lugar do `new` interno.
3. Separar consulta de comando.
4. Substituir `switch` por tabela ou polimorfismo.
5. Dividir a classe.

Cada passo do `fix` cabe em um commit. Para `effort: L`, o achado descreve o passo 1 ou 2 em código e lista os seguintes.

## Calibração de confiança

- alta: abri o caller e o callee, o efeito ou o acoplamento aparece no código.
- media: o dano depende de volume, de concorrência ou de um segundo caller que o diff não mostra.
- baixa: o smell aparece, a dor não. Diga o que confirmaria (um segundo caller, um bug passado em `git log`).
