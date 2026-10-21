# Observabilidade — NestJS

Carregue quando `@nestjs/core` está nas deps. Stack típica da squad: winston + OpenTelemetry + New Relic, RabbitMQ via `@golevelup/nestjs-rabbitmq`.

## Logger

- `new Logger(MyService.name)` do `@nestjs/common` escreve texto em console. Em produção com logger JSON, instale-o como logger da app: `app.useLogger(app.get(WINSTON_MODULE_NEST_PROVIDER))` (nest-winston) ou `nestjs-pino`. Sem isso, parte dos logs (do framework e de `Logger` nativo) sai em formato diferente e quebra o parser.
- `NestFactory.create(AppModule, { bufferLogs: true })` e `app.useLogger(...)` em seguida: logs do boot ficam no formato certo.
- `this.logger.error(err.message, err.stack)` do Logger nativo recebe `(message, stack, context)`: formatos misturados. Com logger estruturado, use `this.logger.error({ err, ...ctx }, 'msg')` conforme a assinatura do wrapper do repo.
- `this.logger.log(\`Usuário ${user.email} criado\`)`: PII por interpolação.
- Nível por ambiente via config, não por `if (NODE_ENV)` espalhado.
- Logger por classe com contexto (nome da classe) e `logger.child` por request quando disponível.

## Correlation id e contexto

- Middleware/interceptor global que lê `x-request-id`/`traceparent`, gera se ausente, grava em `AsyncLocalStorage` (`nestjs-cls` é o padrão comum: `ClsModule.forRoot({ middleware: { mount: true, generateId: true } })`) e devolve no response header.
- O logger lê o id do CLS em todo log (`mixin`/`format`).
- Consumidor de fila não passa pelo middleware HTTP: `ClsModule` com `interceptor` ou `guard` mount para RPC, ou `cls.run` manual no handler com o id vindo dos headers da mensagem.
- `@Injectable({ scope: Scope.REQUEST })` só para carregar request id: custo por request. Use CLS.
- Chamada de saída com `HttpService`: interceptor do axios injeta `x-request-id` e `traceparent` (a auto-instrumentação OTel injeta `traceparent` sozinha).

## Interceptor de logging e métricas

```ts
@Injectable()
export class RequestMetricsInterceptor implements NestInterceptor {
  intercept(ctx: ExecutionContext, next: CallHandler) {
    if (ctx.getType() !== 'http') return next.handle();
    const req = ctx.switchToHttp().getRequest();
    const end = httpDuration.startTimer();
    return next.handle().pipe(
      tap({ next: () => end({ route: req.route?.path, method: req.method, status: ctx.switchToHttp().getResponse().statusCode }),
            error: (e) => end({ route: req.route?.path, method: req.method, status: e.status ?? 500 }) }),
    );
  }
}
```

- `req.route?.path` (template). `req.url` e `req.originalUrl` contêm ids e query.
- Interceptor que registra `req.body` por default: PII e senha. Allowlist por rota.
- Interceptor aplicado só a controllers HTTP quebra em `@MessagePattern`/`@EventPattern`. Verifique `ctx.getType()`.
- Filter global `@Catch()`: um único ponto de log e de reporte para erro 5xx. 4xx esperado não vai para `error`.

## Exception filter e reporte

- Log de 4xx em `error`: ruído. Log `warn` ou métrica por `status_class`.
- `captureException` no filter para `status >= 500` apenas.
- Duplicação: `captureException` no service e no filter.
- Filter que engole o erro sem log (`catch () { res.status(500).json(...) }`): falha invisível.

## OpenTelemetry no Nest

- `instrumentation.ts` importado como primeira linha de `main.ts` (ou `node --require`), antes de `@nestjs/*`.
- `@opentelemetry/instrumentation-nestjs-core` gera spans de controller e handler. Combine com `http`, `express`/`fastify`, `pg`, `ioredis`, `amqplib`.
- `service.name` por app. Em monorepo com várias apps, um por app.
- Span manual em use case ou integração sem auto-instrumentação (`openai`, `@google/genai`, MCP). Decorator próprio (`@Span()` de `nestjs-otel`) evita boilerplate.
- `@golevelup/nestjs-rabbitmq`: o publisher não propaga `traceparent` sozinho. Adicione header na publicação (`propagation.inject(context.active(), headers)`) e extraia no consumer (`propagation.extract`), criando span do tipo `CONSUMER` com `messaging.system = rabbitmq`. A instrumentação `amqplib` cobre a camada abaixo e pode dar o resultado sem trabalho extra. Verifique o resultado no trace.
- Sampler: `ParentBasedSampler` com `TraceIdRatioBased`. Sem parent-based, cada serviço decide por conta própria e o trace fica cortado.

## New Relic no Nest

- `import 'newrelic'` na primeira linha de `main.ts`. Fica fora do bundle se o build usa webpack: confirme `externals`.
- Transações de consumer de fila: `newrelic.startBackgroundTransaction('rmq:enrollment.created', 'RabbitMQ', fn)`. Sem isso, a atividade do consumer fica invisível, ou aparece como transação anônima.
- `newrelic.addCustomAttribute` no interceptor com dado pessoal.
- `application_logging.forwarding.enabled` e `logs in context` via `newrelic.getLinkingMetadata()` no formato do logger.
- Não misture `captureException` do Sentry e `noticeError` do NR no mesmo catch sem critério.

## Consumidores RabbitMQ (`@golevelup`)

- Handler sem log de início e fim com `messageId`, `routingKey`, `attempt`, `duration_ms`, resultado (`ack`/`nack`/`dlq`). Sem isso, não há como depurar mensagem perdida.
- Métricas: `messages_consumed_total{queue,result}`, `message_processing_seconds{queue}`, profundidade e idade da fila via management API ou exporter.
- Log da mensagem inteira: PII (payload com e-mail do aluno). Logue `messageId` e ids.
- DLQ sem alerta de profundidade > 0.
- Erro reencaminhado para DLQ sem log com o motivo.

## Health e Terminus

- `@nestjs/terminus` expõe `/health`. Os indicators registram latência de dependência; exporte como métrica.
- Health checks barulhentos nos logs de acesso (probe a cada 5 s): exclua a rota do logger de request e do tracing (sampler ou `ignoreIncomingPaths`).

## Config e boot

- Logue no boot, em `info`, versão, ambiente e flags relevantes (sem segredos). Falha de config validada no boot loga qual variável falta, sem o valor.
- Nível de log e `OTEL_*` via config validada.
- `process.env.NODE_ENV !== 'production'` para ligar debug: confirme que o default de produção é `info`.

## Prisma

- Logs do Prisma: `new PrismaClient({ log: [{ emit: 'event', level: 'query' }] })` em produção loga parâmetros (PII) e inunda o log. Em produção, `warn` e `error`. Query lenta: use o evento `query` com limite de duração e sem `params`.
- `@prisma/instrumentation` para spans de Prisma (`previewFeatures = ["tracing"]` em versões antigas).

## Correção típica

```ts
// main.ts
import './instrumentation';
import 'newrelic';
const app = await NestFactory.create(AppModule, { bufferLogs: true });
app.useLogger(app.get(WINSTON_MODULE_NEST_PROVIDER));
app.enableShutdownHooks();
```

```ts
this.logger.info({ messageId, routingKey, attempt, outcome: 'ack', durationMs }, 'rmq.message.processed');
```
