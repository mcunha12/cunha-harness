# Tipagem em TypeScript

## tsconfig: o que cada flag fecha

| Flag | Fecha | Sintoma que aparece sem ela |
|---|---|---|
| `strict` | Pacote: `strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitThis`, `alwaysStrict`, `useUnknownInCatchVariables` | `undefined is not a function`, `any` implícito |
| `noUncheckedIndexedAccess` | `arr[i]` e `rec[k]` viram `T \| undefined` | `TypeError` em índice ausente |
| `exactOptionalPropertyTypes` | `a?: T` não aceita `undefined` explícito | PATCH enviando `undefined` que o servidor lê como "limpar" |
| `noImplicitOverride` | `override` obrigatório | método de base renomeado e subclasse deixa de sobrescrever em silêncio |
| `noFallthroughCasesInSwitch` | `case` sem `break` | caso cai no seguinte |
| `noImplicitReturns` | todos os caminhos retornam | `undefined` inesperado |
| `noPropertyAccessFromIndexSignature` | `obj.x` em index signature exige `obj['x']` | typo de propriedade passa |
| `isolatedModules` / `verbatimModuleSyntax` | re-export de tipo sem `type` | erro de bundler (Babel, SWC, esbuild) |
| `useDefineForClassFields` | semântica de campos de classe | ordem de inicialização com decorators |

Sinal: o diff altera o `tsconfig`. Procure remoção de `strict`, `skipLibCheck` combinado com `include` reduzido, `allowJs` sem `checkJs`, `paths` apontando para fora, `exclude` de pasta com código de produção.

Para `noUncheckedIndexedAccess` em repo que não usa: não exija. Em código novo, evite `arr[0].x` sem guard e cite a flag como refs.

## any e unknown

Fontes de `any` que passam despercebidas:

- `JSON.parse`, `Response.json()`, `Body.json()` do Express (`req.body` é `any`), `axios.get` sem genérico, `localStorage.getItem` (devolve `string | null`, e o `JSON.parse` em seguida devolve `any`), `window.env` sem declaração (`declare global { interface Window { env: ... } }`), `process.env` (devolve `string | undefined`, é correto), `Object.fromEntries` (`{ [k: string]: any }` se a entrada é `any`), `Array.prototype.flat` sobre `any[]`, `require()`, import dinâmico de módulo sem tipos, `catch` com `useUnknownInCatchVariables: false`, `Promise.all` com `any` dentro, `structuredClone` (devolve o mesmo tipo, sem garantia), eventos `CustomEvent<any>`.
- Correção típica: `unknown` na declaração e parse na borda.

```ts
const raw: unknown = JSON.parse(text);
const parsed = FooSchema.parse(raw);
```

`catch`:

```ts
try { await run(); } catch (e) {
  if (e instanceof AxiosError) log(e.response?.status);
  else throw e;
}
```

`catch (e: any)` e `e.response.data.message` sem estreitar é o padrão frágil.

## Asserções

- `as` legítimo: estreitamento que o compilador não infere e que o código acabou de provar (depois de checagem com `in`/`typeof` em estrutura complexa), `as const`, `as unknown` em `unknown` de teste de tipo, DOM (`document.getElementById('x') as HTMLInputElement`, e `instanceof HTMLInputElement` é melhor).
- `as` suspeito: dupla asserção `as unknown as T`, `as T` em retorno de função assíncrona de I/O, `as T` em literal vazio, `as keyof typeof x` em string de usuário, `as never`.
- `satisfies` checa sem alargar nem estreitar:

```ts
const ROUTES = { home: '/', course: '/curso/:id' } satisfies Record<string, string>;
```

- `!` com `Map.get`: troque por `const v = map.get(k); if (v === undefined) throw new Error(...)`.
- `!` em `ref.current` de React: guard com `if (!ref.current) return`.
- `@ts-ignore` versus `@ts-expect-error`: `@ts-expect-error` falha o build quando o erro some. O motivo vai na mesma linha.

## Narrowing e type guards

```ts
function isActive(e: Enrollment): e is Enrollment & { status: 'ACTIVE' } {
  return e.status === 'ACTIVE';
}
```

- Predicado de verdade parcial é bug: o compilador confia no retorno `true`.
- `Array.prototype.filter` com predicado: `.filter((x): x is Foo => x !== null)` (TS 5.5 infere em casos simples). `.filter(Boolean)` não estreita em versões anteriores, e remove `0` e `""` indevidamente.
- Narrowing se perde em closure sobre `let`, em callback assíncrono e após chamada que o compilador acha que invalida. Prefira `const` local.
- `in` operator estreita union por presença de chave. Discriminador literal é mais robusto.
- `typeof x === 'object'` inclui `null`.
- `Array.isArray` estreita para `any[]` em `unknown`. Valide os elementos.

## Unions discriminadas e exaustividade

```ts
function assertNever(x: never): never {
  throw new Error(`Caso não tratado: ${JSON.stringify(x)}`);
}
switch (s.status) {
  case 'idle': return ...;
  case 'loading': return ...;
  default: return assertNever(s);
}
```

- `Record<Status, Handler>` força entrada por valor.
- Evite `string` num campo que é de fato união de literais: `status: string` aceita `'ATVIA'`.
- Template literal types ajudam em chaves compostas (`` `${Entity}:${Action}` ``) até 2 níveis.

## Branded types

```ts
type Brand<T, B extends string> = T & { readonly __brand: B };
type CourseId = Brand<string, 'CourseId'>;
type PackId = Brand<string, 'PackId'>;
const toCourseId = (s: string): CourseId => s as CourseId;
```

- O `as` fica em um único construtor. Parse com schema (`z.string().uuid().brand<'CourseId'>()`) quando o valor vem de fora.
- Brand exige ponto de entrada. Em repo sem a prática, proponha só para os IDs que já foram trocados em bug ou que aparecem em funções com 2+ IDs.

## Enums

- `enum` numérico: aceita qualquer `number`, gera objeto em runtime, o valor reverso vira chave. `const enum` quebra com `isolatedModules`. Enum de string é mais seguro e ainda gera runtime.
- Alternativa sem runtime extra:

```ts
export const Status = { Active: 'ACTIVE', Ended: 'ENDED' } as const;
export type Status = (typeof Status)[keyof typeof Status];
```

- Siga o padrão do repo para código novo.

## Genéricos

- `function pick<T, K extends keyof T>(o: T, k: K): T[K]` relaciona três coisas, e é um bom generic.
- `function log<T>(x: T): void` não relaciona nada.
- Generic com cast interno (`return {} as T`) esconde o problema que o generic devia resolver.
- Defaults `= any` anulam a checagem. Use `= unknown`.
- Overloads: a assinatura de implementação não é visível, e overloads que se sobrepõem escolhem o primeiro que casa. Prefira union ou generic quando possível.

## Utility types para derivar

- Props: `ComponentProps<typeof Button>`, `Omit<ComponentProps<'button'>, 'onClick'>`.
- Retorno: `Awaited<ReturnType<typeof getUser>>`.
- Elemento: `(typeof list)[number]`.
- Chaves: `keyof typeof obj`.
- Zod: `z.infer<typeof S>` (saída) e `z.input<typeof S>` (entrada, relevante com `transform`/`default`).
- Parcial de mutação: `Partial<Pick<Foo, 'a' | 'b'>>`.

## Object.keys, entries e Map

- `Object.keys(o)` devolve `string[]` porque objetos podem ter chaves extras. O cast é válido quando o objeto é literal fechado e vem de `as const`. Encapsule em `typedKeys` com um comentário de uma linha.
- `new Map(Object.values(X))` onde `X` é `as const` infere chaves literais. `map.get(someString)` falha no type-check. Correção: `new Map<string, string>(...)`.
- `Object.fromEntries` perde o tipo da chave.

## Declaration files e módulos

- `declare module 'x';` sem corpo torna todo o módulo `any`. Escreva os tipos que o código usa.
- `declare global` para `Window.env`: tipar cada campo, sem `[key: string]: any`.
- Import de JSON: `resolveJsonModule` tipa o shape do arquivo. O dado continua sem validação se o JSON vem de fora do repo.

## Async

- `async` function com `void` esperado em callback: `onClick={async () => ...}` cria promise flutuante (resiliência é do review-resiliencia).
- `Promise.all` com tupla preserva tipos por posição. `Promise.all(arr.map(...))` devolve array homogêneo.
- `Promise<any>` anula a cadeia.

## Código de teste

- Fixture parcial tipada com `as Foo` é aceita. Fixture com `as any` que mascara campo obrigatório novo passa pelo compilador e quebra quando a fixture divergir do tipo real. Prefira helper de factory com `Partial<Foo>` e defaults.
