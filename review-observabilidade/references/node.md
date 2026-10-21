# Observabilidade — Node HTTP (Express, Fastify, Koa)

Carregue quando `express`, `fastify` ou `koa` está nas deps sem Nest.

## Logger de request

- `morgan('combined')` registra URL com query (token, e-mail) e `user-agent` em texto. Para produção, prefira `pino-http` com serializers e `redact`, ou `morgan` com formato JSON e URL sem query.
- `pino-http`: `serializers: { req: (req) => ({ id: req.id, method: req.method, url: req.url.split('?')[0] }), res: (res) => ({ status: res.statusCode }) }`; `genReqId` lendo `x-request-id`/`traceparent`; `customLogLevel` (`>= 500` error, `>= 400` warn, resto info); `autoLogging.ignore` para `/health`.
- `app.use((req, res, next) => { console.log(req.body); next(); })`: PII e senha em log. Remova ou allowlist.
- Fastify: o logger do Pino já vem embutido (`Fastify({ logger: { redact } })`). `request.log` carrega o `reqId`. Use-o em vez de um logger global, para manter correlação.
- Express: sem `pino-http`, injete `req.log = logger.child({ requestId })` em middleware.

## Contexto

- `AsyncLocalStorage` iniciado em middleware no topo da pilha. Middleware registrado antes do que inicia o store perde contexto.
- Em Fastify use `@fastify/request-context` ou `AsyncLocalStorage` em `onRequest`.
- Em Koa, `ctx.state.requestId`, e o logger recebe `ctx.state`. `AsyncLocalStorage` com `await next()`.

## Tratamento de erro e reporte

- Error middleware único com `logger.error({ err, requestId })` para 5xx e `warn` para 4xx. Sem o middleware, o handler default do Express imprime o stack em texto no stderr e, fora de produção, na resposta.
- `NODE_ENV=production` desliga o stack na resposta do Express. Confirme no deploy.
- `process.on('unhandledRejection', ...)` e `uncaughtException`: log estruturado com `err`, reporte ao Sentry com `await Sentry.flush(2000)` antes de sair. Sem flush, o evento se perde ao encerrar.
- Sentry: `Sentry.setupExpressErrorHandler(app)` (v8+) depois das rotas e antes do error middleware próprio. Versões antigas: `Sentry.Handlers.requestHandler()` primeiro e `errorHandler()` depois das rotas.

## Tracing e métricas

- Instrumentação OTel carregada antes de `express`/`fastify` (primeira linha do entrypoint ou `--require`).
- `@opentelemetry/instrumentation-express` nomeia o span pela rota (`/enrollments/:id`). Middleware custom aparece como span: filtre com `ignoreLayersType` quando for ruído.
- Métrica com `prom-client`: `collectDefaultMetrics()`; `Histogram` com `labelNames: ['route','method','status']`; use `req.route?.path` após o roteamento (em `res.on('finish')`). Em 404, `req.route` é `undefined`: use um rótulo fixo (`unmatched`) e nunca `req.path`.
- Endpoint `/metrics` sem autenticação pública na internet: informação interna exposta. Restrinja por rede ou autenticação (dono: review-seguranca; handoff).
- Event loop lag (`perf_hooks.monitorEventLoopDelay`) e handles ativos: métricas de saturação.
- Timeout de resposta: métrica e log do abort (`req.on('aborted')`/`close`) para distinguir cliente que desistiu de erro do servidor.

## Clientes de saída

- Registre dependência externa: duração, status e destino (host e rota templatizada) em métrica `outbound_request_duration_seconds{peer,status_class}`.
- Interceptor axios de log: `config.headers` e `data` completos vazam token e PII. Logue `method`, `url` sem query, `status`, `duration`.
- Propague `traceparent`/`x-request-id` em chamada de saída (auto-instrumentação `http` faz o primeiro; o segundo é manual).

## Filas e jobs

- BullMQ: eventos `completed`, `failed`, `stalled` com log estruturado (`jobId`, `name`, `attemptsMade`, `duration`). Métrica de profundidade via `queue.getJobCounts()` e de latência de espera. Contexto de trace em `job.data._trace` ou `opts` para propagação.
- Job agendado: log de início, fim e duração; métrica `job_last_success_timestamp_seconds`; alerta de job parado.
- `setInterval` com falha silenciosa: sem `try/catch` e sem métrica, o job para de funcionar e ninguém percebe.

## Shutdown de telemetria

```ts
process.on('SIGTERM', async () => {
  server.close();
  await Promise.allSettled([sdk.shutdown(), Sentry.close(2000), logger.flush?.()]);
  process.exit(0);
});
```

- `pino` com `pino.destination({ sync: false })` ou transport assíncrono: sem `flush`/`final` no encerramento, as últimas linhas (as do erro fatal) se perdem.
- Fila de eventos do analytics server-side (`posthog-node`): `await client.shutdown()`.

## Sinais de alerta rápidos

- `console.log(req)` ou `console.log(err)` em handler.
- `res.status(500).send(err.stack)`.
- Métrica com `req.url` ou `req.path` em label.
- Retry de cliente HTTP sem log de tentativa: o plantonista vê latência alta sem explicação. Log `warn` por retry com `attempt` e causa.
