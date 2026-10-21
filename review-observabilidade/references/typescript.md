# Observabilidade — TypeScript

Carregue quando o repo tem `tsconfig*.json` ou `typescript` nas deps.

## Erros em log

- `logger.error(err.message)` perde `stack`, `cause` e `code`. Correção: `logger.error({ err }, 'msg')` com serializer de erro (`pino.stdSerializers.err`; winston: `format.errors({ stack: true })`).
- `logger.error('falhou: ' + err)` converte para string e perde estrutura. `JSON.stringify(err)` devolve `{}` porque propriedades de `Error` não são enumeráveis. Use o serializer.
- `catch (e)` com `e: unknown`: normalize antes de logar.

```ts
const err = e instanceof Error ? e : new Error(String(e));
logger.error({ err, enrollmentId }, 'enrollment.create.failed');
```

- `Error.cause` aninhado: confirme que o serializer percorre `cause` (pino serializer sim, em versões recentes; winston depende do formato).
- Erro de axios: `logger.error({ err })` serializa `config` (com headers `Authorization`) e `request`. Impacto: vaza token. Correção: logar `{ status: err.response?.status, url: err.config?.url, method: err.config?.method, code: err.code }` ou um serializer próprio para `AxiosError`.
- Erro de Prisma: `err.meta` e `err.message` podem trazer valores de campos (unique violation com o e-mail). Logue `code` e `meta.target`.
- Erro de `zod`: `err.issues` pode incluir o valor recebido. Logue `path` e `code`.

## Contexto assíncrono

- `AsyncLocalStorage` (`node:async_hooks`) guarda `requestId`/`traceId`. O logger lê do store em cada chamada (mixin do pino, `format` do winston).
- `AsyncLocalStorage.run` só no middleware de entrada. `enterWith` em lugar aleatório vaza contexto entre requests.
- Contexto perdido: callback de driver legado sem promisify, `EventEmitter.on`, fila em memória que processa depois. Capture o contexto com `AsyncResource.bind`.

## Redação com pino

```ts
const logger = pino({
  redact: { paths: ['req.headers.authorization', 'req.headers.cookie', '*.password', '*.email', '*.cpf', '*.token'], censor: '[redacted]' },
  serializers: { err: pino.stdSerializers.err },
});
```

- `redact.paths` não cobre chave em posição arbitrária (`a.b.c.email` precisa de path explícito ou wildcard por nível). Confirme a profundidade.
- Logar `req` do Express inteiro sem `pino-http` com `serializers.req` customizado vaza `headers`.

## winston

- `winston.format.json()` sem `format.errors({ stack: true })`: `logger.error(err)` perde o stack.
- `logger.log('error', 'msg', err)`: a ordem de argumentos muda entre versões. Passe objeto de meta.
- Transport de console síncrono em hot path: custo. Em produção use stdout JSON e deixe o agente coletar.
- `exceptions.handle` e `rejections.handle` do winston: sem `exitOnError` consciente, o processo continua após `uncaughtException`.
- `defaultMeta: { service, version }` no logger raiz; `logger.child({ requestId })` por request.

## OpenTelemetry (Node SDK)

- Bootstrap antes de qualquer `import` da app (`--require ./instrumentation.js` ou primeira linha de `main.ts`). Instrumentação carregada depois de `http`, `pg` ou `amqplib` não aplica patch.
- `NodeSDK` com `getNodeAutoInstrumentations()`: `fs` instrumentation gera ruído; desative `@opentelemetry/instrumentation-fs`.
- `service.name`, `service.version`, `deployment.environment` em `Resource`. Sem eles, os dados caem em `unknown_service`.
- Span manual:

```ts
return tracer.startActiveSpan('enrollments.create', async (span) => {
  try {
    span.setAttribute('app.course_id', courseId);
    return await this.repo.create(dto);
  } catch (e) {
    span.recordException(e as Error);
    span.setStatus({ code: SpanStatusCode.ERROR });
    throw e;
  } finally {
    span.end();
  }
});
```

- `span.end()` fora do `finally`: span aberto para sempre em caminho de erro.
- `startSpan` sem `context.with`: o span filho não herda o pai. Prefira `startActiveSpan`.
- Instrumentação de `fetch` nativo (undici) precisa de `@opentelemetry/instrumentation-undici`. Axios usa `http` e é coberto pela instrumentação `http`.
- Exporter: `BatchSpanProcessor` em produção. `SimpleSpanProcessor` exporta por span, de forma síncrona, e degrada latência. Shutdown: `await sdk.shutdown()` no `SIGTERM` para não perder o último lote.
- Métricas: `meter.createHistogram('request_duration', { unit: 's' })`. Atributos finitos.

## New Relic (Node agent)

- `require('newrelic')` na primeira linha do entrypoint.
- `newrelic.addCustomAttributes({ courseId })` e `newrelic.setTransactionName`. Atributo com PII fica retido no NR.
- `newrelic.noticeError(err, attrs)` e captura automática duplicam quando o filter global também chama. Defina um ponto.
- `distributed_tracing.enabled: true`; confira `application_logging.forwarding`. Com `logs in context`, o logger inclui `newrelic.getLinkingMetadata()`.
- Nome de transação com id (`/enrollments/123`) gera "metric grouping issue". Use rota templatizada.
- Custom event (`recordCustomEvent`) com propriedades de alta cardinalidade ou PII.

## Sentry (Node)

- `Sentry.init({ dsn, release, environment, sendDefaultPii: false, beforeSend })`. DSN por variável de ambiente.
- `Sentry.captureException(e)` em `catch` que depois relança duplica com o integration global (`onUncaughtException`, `onUnhandledRejection`) e com o filter do Nest.
- `Sentry.withScope(scope => { scope.setTag('route', ...); scope.setUser({ id }); Sentry.captureException(e); })` para contexto sem vazar entre eventos.
- `tracesSampleRate: 1.0` em produção de alto volume: custo. Use `tracesSampler` por rota.
- `ignoreErrors` e `beforeSend` para `AbortError`, 4xx esperados.

## Tipos e padrões de wrapper

- Tipar o contexto de log evita campo inventado:

```ts
type LogCtx = { requestId?: string; userId?: string; enrollmentId?: string; courseId?: string };
```

- Wrapper de analytics com union de nomes de evento e payload por evento: o compilador impede evento fora do catálogo e payload com campo extra (PII acidental).

```ts
type AnalyticsEvents = {
  course_started: { courseId: string; source: 'home' | 'search' };
  enrollment_completed: { enrollmentId: string };
};
function track<E extends keyof AnalyticsEvents>(e: E, p: AnalyticsEvents[E]): void { /* ... */ }
```

## Sinais de alerta rápidos

- `console.log(JSON.stringify(...))` de objeto de domínio.
- `logger.info(\`... ${JSON.stringify(dto)}\`)`: PII por interpolação.
- `process.on('uncaughtException', (e) => console.log(e))` sem encerrar e sem reportar.
- `catch {}` com `Sentry.captureException` ausente em fluxo crítico: falha invisível.
