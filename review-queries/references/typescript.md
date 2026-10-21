# Queries e rotas: padrões de TypeScript/JavaScript

## async e paralelismo

- Dois `await` independentes em sequência: `const [a, b] = await Promise.all([fa(), fb()])`. Cuidado: se `fb` depende de efeito de `fa`, a ordem importa.
- `await` em `for`/`for...of` sobre chamadas independentes: `Promise.all(items.map(fn))` com limite de concorrência quando N é grande:

```ts
import pLimit from 'p-limit';
const limit = pLimit(10);
const results = await Promise.all(items.map((i) => limit(() => fetchItem(i))));
```

- `Promise.all` de operações que escrevem no mesmo recurso sem ordem: corrida (resiliência).
- `await` dentro de `reduce` encadeia em série: troque por `map` mais `Promise.all` quando independentes.
- `Promise.race` para timeout sem cancelar a operação original: a operação segue consumindo recurso. Use `AbortController`/`AbortSignal.timeout(ms)` (o tema de timeout é do review-resiliencia).

## Coleções

- `arr.find(...)`, `arr.includes(...)`, `arr.indexOf(...)`, `arr.filter(...).length` dentro de loop sobre outra lista grande: O(n·m). Correção: `const byId = new Map(items.map((i) => [i.id, i]))` e `byId.get(id)`.
- `Array.prototype.includes` em lista grande chamada por item: `Set`.
- `[...acc, x]` em `reduce`: O(n²). Correção: `acc.push(x)`.
- `Object.keys(obj).length` em loop: guarde.
- `arr.sort()` dentro de loop. Ordene uma vez.
- `arr.shift()` em fila grande: O(n) por chamada. Índice de cabeça ou estrutura própria.
- `.filter().map()` encadeado em listas de 10^5+: uma passada com `reduce`/`for`, só se o perfil mostrar. Micro-otimização em lista pequena não se reporta.
- `JSON.parse(JSON.stringify(x))` para clone em caminho quente: `structuredClone` ou imutabilidade.
- `Array.from({ length: n })` e `new Array(n).fill()` com n grande em handler.
- Spread de array grande em argumento (`Math.max(...arr)` com 10^5+ itens): estoura a pilha. Correção: `reduce` ou loop.

## Datas, regex e strings

- `new Date()`/`Intl.DateTimeFormat` construído por item em loop de milhares: instancie o formatter uma vez.
- Regex literal em loop é compilada uma vez pelo motor. `new RegExp(str)` por iteração, não. Hoist.
- Concatenação com `+=` em loop de milhares: `array.join`.

## Memoização e cache em processo

- `Map` global usado como cache sem limite e sem TTL: vazamento. Use `lru-cache` com `max` e `ttl`.
- Memoização por chave de objeto (`JSON.stringify(args)` como chave) em caminho quente: o custo da chave pode superar o do cálculo.
- Cache de promise por chave (single-flight):

```ts
const inflight = new Map<string, Promise<Data>>();
function load(key: string): Promise<Data> {
  let p = inflight.get(key);
  if (!p) { p = fetchData(key).finally(() => inflight.delete(key)); inflight.set(key, p); }
  return p;
}
```

## Streams e async iterators

- `for await (const chunk of stream)` processa por chunk. Acumular todos os chunks em array anula o stream.
- `readline` sobre arquivo grande em vez de `readFile` e `split('\n')`.

## Browser (quando o diff é de código de cliente e tem custo de rede)

- O custo de render, bundle e effects é do review-front. Daqui: requisições paralelizáveis em `Promise.all`, requisição repetida sem cache (`fetch` em cada render sem react-query), `debounce` ausente em busca por tecla (1 requisição por tecla), polling sem backoff.
