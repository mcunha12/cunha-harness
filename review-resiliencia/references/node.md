# Resiliência — Node HTTP (Express, Fastify, Koa) e runtime

Carregue quando `express`, `fastify` ou `koa` está nas deps sem Nest, e para qualquer serviço Node sobre o runtime.

## Handlers e erros

- Express 4: handler `async` que lança não chega ao error middleware. A request fica pendurada até o timeout do cliente. Correção: `express-async-errors`, wrapper, ou Express 5 (propaga rejeição).
- Error middleware precisa de 4 argumentos `(err, req, res, next)` e vir depois das rotas. Com 3 argumentos o Express o trata como middleware comum.
- Erro depois de `res.headersSent`: chame `next(err)` e deixe o handler padrão fechar a conexão. Escrever de novo lança `ERR_HTTP_HEADERS_SENT`.
- Fastify: `reply.send` dentro de `async` handler e `return` simultâneos. `setErrorHandler` global. `schema` de resposta faz erro de serialização virar 500.
- Koa: `ctx.throw` e middleware de erro no topo da pilha, com `app.on('error')`.
- Resposta 200 com `{ success: false }`: evite. O status comunica.

## Processo

- `process.on('uncaughtException')` e `unhandledRejection`: registrar log, fechar o servidor com prazo e sair com código diferente de 0. Continuar executando depois deles mantém estado indefinido.
- `server.close()` espera conexões keep-alive. Sem `server.closeIdleConnections()` (Node 18.2+) ou `keepAliveTimeout` curto, o shutdown demora até o timeout do orquestrador e leva `SIGKILL`.
- `SIGTERM` handler que chama `process.exit(0)` direto corta requests em voo. Correção: `server.close(cb)`, drenar, depois sair, com timer de segurança.
- `server.keepAliveTimeout` menor que o do load balancer gera `ECONNRESET` esporádico (502 no LB). Regra: `keepAliveTimeout` do Node maior que o idle timeout do LB (ex.: ALB 60 s → Node 65 s) e `headersTimeout` maior que `keepAliveTimeout`.
- `server.requestTimeout`, `headersTimeout` ausentes ou zerados: conexão lenta (slowloris) prende socket.

## Clientes de saída

- `http.Agent` / `https.Agent` com `keepAlive: true` e `maxSockets`. Sem limite, pico abre milhares de sockets. Com `maxSockets` baixo e sem timeout, as requests ficam na fila do agent indefinidamente.
- `undici`/`fetch`: `headersTimeout`, `bodyTimeout`, `connectTimeout` no `Agent`. O corpo da resposta deve ser consumido ou cancelado (`res.body.cancel()`), senão a conexão não volta ao pool.
- `got`/`ky`: `retry` default repete GET em alguns erros. Confirme `methods` e `statusCodes`.
- DNS: erro `EAI_AGAIN` e `ENOTFOUND` transitórios em ambiente de container. Conte-os como transitórios no `isTransient`.

## Banco, cache e fila (clientes Node)

- `pg.Pool`: `connectionTimeoutMillis`, `idleTimeoutMillis`, `statement_timeout`/`query_timeout`, `max` coerente com o limite do Postgres e o número de réplicas. Handler `pool.on('error')` obrigatório: erro em cliente ocioso sem listener derruba o processo.
- `client.query` fora de `try/finally` com `client.release()`: vazamento de conexão. Correção: `try { ... } finally { client.release(); }`.
- `ioredis`: handler `redis.on('error')` obrigatório; sem ele, a lib loga e pode emitir erro não tratado. `maxRetriesPerRequest` (default 20 enfileira comandos), `enableOfflineQueue`, `commandTimeout`, `connectTimeout`, `retryStrategy` com teto. Cache que falha não derruba a rota: trate erro do Redis como miss.
- `amqplib`: `connection.on('error')` e `'close'` com reconexão; canal fechado por erro de protocolo exige novo canal. `channel.prefetch(n)` antes de `consume`. Confirmação: `ack` ao fim, `nack(msg, false, false)` para DLQ.
- Lock distribuído com Redis (`SET NX PX`) sem TTL ou com TTL menor que o trabalho: dois executores. Use token no valor e libere com compare-and-delete.

## Filas e jobs em processo

- BullMQ: `attempts` e `backoff` por job, `removeOnFail` com política, `stalledInterval`, `worker.on('failed')` e `on('error')`. Job com efeito externo precisa de idempotência: stall e reentrega executam duas vezes.
- `setInterval` com função async: execuções sobrepostas quando uma demora mais que o intervalo. Correção: `setTimeout` recursivo depois de concluir, ou flag `running`.
- Cron em várias réplicas: lock distribuído.

## Event loop

- Trabalho CPU-bound síncrono (JSON gigante, `crypto` síncrono, regex catastrófica, `readFileSync` em rota) bloqueia todas as requests. Impacto: health check falha, o orquestrador reinicia o pod sob carga. Correção: worker thread, fila, stream. Detalhe de performance é do review-queries; entra aqui quando causa falha de liveness.
- `JSON.parse` de body sem limite: configure `limit` no body parser (`express.json({ limit })`).

## Streams

- `req.pipe(res)` e `.pipe` sem handler de erro. Use `pipeline` de `stream/promises` com `AbortSignal`.
- Cliente que desconecta: escute `req.on('close')` / `res.on('close')` e cancele o trabalho a montante.
- `readable.on('data')` sem backpressure (`await once(writable, 'drain')`) acumula memória.

## Correção típica

```ts
const server = app.listen(port);
server.keepAliveTimeout = 65_000;
server.headersTimeout = 66_000;

process.on('SIGTERM', () => {
  const t = setTimeout(() => process.exit(1), 25_000).unref();
  server.close(async () => {
    await Promise.allSettled([pool.end(), redis.quit(), amqp.close()]);
    clearTimeout(t);
    process.exit(0);
  });
  server.closeIdleConnections();
});
```

```ts
pool.on('error', (err) => logger.error({ err }, 'pg idle client error'));
redis.on('error', (err) => logger.warn({ err }, 'redis error'));
```
