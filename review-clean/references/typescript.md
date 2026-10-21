# Clean em TypeScript

## Funções e parâmetros

- Sinal: `fn(a: string, b: string, c: boolean, d?: number)`. Correção: `fn({ courseId, userId, includeDrafts, limit }: Params)` com `interface Params` nomeada. Parâmetros opcionais em objeto, com defaults na desestruturação.
- Sinal: parâmetro booleano posicional. Correção: duas funções, ou union literal (`mode: 'strict' | 'lenient'`), ou propriedade nomeada no objeto.
- Sinal: overloads de 4+ assinaturas para esconder um union. Correção: union discriminada de entrada.

## Efeitos colaterais

- Sinal: `Array.prototype.sort`, `reverse`, `splice` e `push` em parâmetro ou em estado compartilhado. Correção: `toSorted`/`toReversed`/`toSpliced` (ES2023, confira `lib` e Node 20+) ou `[...arr].sort(...)`.
- Sinal: `Object.assign(target, patch)` com `target` vindo de argumento. Correção: `{ ...target, ...patch }`.
- Sinal: `let` de módulo mutado por funções exportadas (`let cache`, `let current`). Correção: classe com estado injetada, ou `Map` encapsulado atrás de uma API, ou escopo por request.
- Sinal: efeito no import (cliente conectando ao importar, `addEventListener` no topo). Dono: review-modularidade.

## Controle de fluxo e erros

- Sinal: `if/else` aninhado com `return` em todos os ramos. Correção: guard clauses.
- Sinal: `try/catch` que devolve `null` no catch. Correção: `Result`, ou deixar o erro subir. Erro engolido é de review-resiliencia.
- Result tipado: `type Result<T, E> = { ok: true; value: T } | { ok: false; error: E }`. O caller faz narrowing por `ok`. Use `assertNever` em unions de `error`.
- Sinal: `switch` por tipo sem `default: assertNever(x)` quando o union é fechado. Exaustividade como tema de tipo é de review-tipagem. Aqui o foco é o OCP: tabela `Record<Kind, Handler>` que o compilador obriga a completar.

## Classes

- Sinal: classe com 1 método público e nenhum estado (`class XService { run() }`) fora de framework que exige classe. Correção: função exportada.
- Sinal: campos opcionais (`user?: User`) preenchidos só depois de `init()`. Temporary field. Correção: construir já completo (factory estática) ou passar por parâmetro.
- Sinal: `private` sem uso, `protected` sem subclasse, `static` com estado mutável. Correção: remover ou isolar.
- Sinal: herança de classe concreta para reaproveitar código. Correção: composição.

## Value objects

```ts
export class Money {
  private constructor(readonly cents: number) {}
  static fromCents(c: number) {
    if (!Number.isInteger(c) || c < 0) throw new RangeError('cents inválido');
    return new Money(c);
  }
  add(o: Money) { return new Money(this.cents + o.cents); }
}
```

Use para dinheiro, período, CPF, percentual. Em DTO de transporte o valor permanece primitivo e o service converte na entrada.

## Dependências

- Sinal: `import { prisma } from '../db'` dentro de função de domínio. Correção: receber `repo` por parâmetro ou construtor.
- Sinal: `Date.now()`/`new Date()`/`Math.random()` na regra. Correção: parâmetro `now: Date` ou `clock: { now(): Date }`.
- Função de ordem superior para injetar: `const makeGrade = (repo: AnswerRepo) => (examId: string) => ...`.

## Assincronia

- Sinal: função `async` que mistura `await` sequencial independente com regra. Fan-out é de review-queries.
- Sinal: função que ora retorna valor, ora `Promise`. Correção: sempre `async`.
- Sinal: callback e promise misturados na mesma API. Correção: promise.

## Smells típicos de TS

- Data clumps: `(startDate, endDate, timezone)` em 5 assinaturas. Correção: `Period`.
- Message chain com optional chaining longo (`a?.b?.c?.d?.e`) em 3+ lugares: o caller conhece a estrutura. Correção: método ou seletor no dono do dado.
- Parâmetro `options: any` ou `Record<string, unknown>` repassado por 3 camadas: ISP e tipagem.
