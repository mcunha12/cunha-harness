# Queries e rotas em Node (Express, Fastify, Koa)

## Event loop

- Sinal de bloqueio em handler: `fs.readFileSync`, `fs.writeFileSync`, `child_process.execSync`, `spawnSync`, `crypto.pbkdf2Sync`, `crypto.scryptSync`, `bcrypt.hashSync`/`compareSync`, `zlib.*Sync`, `JSON.parse`/`stringify` de payload de MB, `Array.sort` de 10^5+ itens, regex sobre entrada grande, `for` pesado, `new RegExp` em loop. Impacto: cada ms bloqueado atrasa todas as requisições do processo. A 100 req/s, um bloqueio de 50 ms por requisição já satura 1 core (5 s de CPU por segundo). Correção: versão assíncrona, `worker_threads`/`piscina`, fila, streaming.
- `bcrypt` assíncrono usa o threadpool do libuv (4 threads por padrão, `UV_THREADPOOL_SIZE`). Muitas operações simultâneas enfileiram, e o pool é compartilhado com `fs` e `dns`.
- `JSON.stringify` de resposta grande: pagine, ou use stream (`stream-json`).
- Cálculo CPU-bound em handler: `worker_threads`.

## Paralelismo e concorrência

- `Promise.all` sobre array de tamanho de entrada (N sem teto) abre N operações simultâneas. Correção: `p-limit`/`p-map` com concorrência (5-20), ou lotes.
- `for ... await` sobre operações independentes: sequencial. `Promise.all` com limite.
- `await` dentro de `reduce` serializa.
- `Promise.all` com `.map(async ...)` e falha parcial: a primeira rejeição rejeita o conjunto, as outras continuam rodando. `allSettled` quando falha parcial é aceita.
- `forEach(async ...)`: ninguém espera as promises (resiliência é do review-resiliencia), e o código perde a ordem e o limite.

## Memória e streams

- `fs.readFile` de arquivo grande, `Buffer.concat(chunks)` de upload, `res.json(bigArray)`: use stream. `pipeline(readable, transform, res)` com `stream/promises`.
- Upload com `multer.memoryStorage()` para arquivos de MB: memória por requisição. Correção: `diskStorage` ou stream direto ao storage de objetos.
- Cursor de banco: `pg-cursor`, `pg-query-stream`, `for await` sobre `prisma.$queryRaw` não faz stream (traz tudo). Prisma não tem cursor server-side: use paginação por keyset em lotes.
- Vazamento: `Map`/`Set`/array global crescendo por requisição (cache sem limite, listeners acumulados, `setInterval` sem `clear`). Impacto: OOM em dias. Correção: LRU com limite (`lru-cache`), TTL.
- `EventEmitter` com `MaxListenersExceededWarning`: listener adicionado por requisição e não removido.

## HTTP e cache

- Keep-alive no agente HTTP de saída (`http.Agent({ keepAlive: true })`). Node 19+ vem com keep-alive por padrão no agente global.
- Compressão: `compression` (Express) ou `@fastify/compress`, ou no proxy. Evite comprimir respostas pequenas (<1 KB) e tipos já comprimidos.
- `ETag` do Express é fraco e computado sobre o corpo (custo CPU em corpo grande, e o corpo já foi gerado). Para economizar o trabalho, `If-None-Match` contra versão conhecida antes de montar a resposta.
- `express.static` com `maxAge`/`immutable` para assets com hash.
- Header `Cache-Control` explícito em rotas de leitura que toleram atraso.
- Rate limit e proteção de abuso são do review-seguranca.

## Banco com `pg` / mysql2

- `pool.query` por consulta, `pool.connect` só para transação, com `release()` em `finally`.
- `pg` `max` do pool coerente com réplicas × `max_connections`.
- Consulta dentro de `Promise.all` sobre N itens: N consultas simultâneas disputam o pool. Use uma consulta em lote.
- `mysql2`: `execute` (prepared) versus `query`. Prepared statements ocupam cache por conexão.

## Fastify

- `schema.response` ativa `fast-json-stringify` (serialização 2-5× mais rápida e sem campos extras). Rota quente de listagem sem `schema.response` perde esse ganho.
- Hooks `preHandler` com consulta ao banco em toda rota: custo fixo por requisição.
- Decorators e plugins registrados dentro de handler: custo por requisição.

## Express

- Middleware pesado montado em todas as rotas (`app.use(heavy)`) em vez de por rota.
- `res.json` chamado depois de `await` desnecessário.
- `body-parser` com `limit` alto e rota pública.
