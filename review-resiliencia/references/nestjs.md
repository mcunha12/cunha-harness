# Resiliência — NestJS

Carregue quando `@nestjs/core` está nas deps.

## Exception filters e mapeamento de erro

- Sinal: `throw new Error(...)` em service. Impacto: o Nest converte em 500 genérico e esconde categoria. Correção: lance `HttpException` apropriada na borda ou erro de domínio mapeado por `@Catch()` filter global.
- Sinal: `try/catch` em controller que devolve `{ error: ... }` com 200. Impacto: monitoramento e cliente leem sucesso. Correção: deixe a exceção subir ao filter.
- Sinal: filter global que captura `Error` e devolve sempre 500. Impacto: erro de validação e de domínio viram 500. Correção: filter com `instanceof HttpException` primeiro, domínio depois, inesperado por último, com log do original.
- Filter registrado só no módulo, enquanto o handler de microservice (RMQ, gRPC) roda em contexto diferente. Para `@MessagePattern`/`@EventPattern`, `HttpException` não vale. Use `RpcException` e `ExceptionFilter` para o contexto `rpc`, ou trate no handler.
- `@Catch()` que lê `host.switchToHttp()` em contexto RMQ lança no filter e perde o erro. Verifique `host.getType()`.

## Chamadas HTTP (`@nestjs/axios`, axios direto)

- `HttpService` sem `timeout` na config do `HttpModule.register` e sem `timeout` por chamada: infinito. Correção: `HttpModule.registerAsync({ useFactory: (cfg) => ({ timeout: cfg.get('X_TIMEOUT_MS'), maxRedirects: 3 }) })`.
- `firstValueFrom(this.http.get(...))` sem `timeout()` do RxJS: o observable espera para sempre se a fonte nunca emite. Correção: `.pipe(timeout(5_000), catchError(...))`.
- `lastValueFrom` sobre observable que pode completar vazio lança `EmptyError`. Passe `defaultValue` quando vazio é válido.
- `catchError` que devolve `of(null)` esconde falha. Correção: `throwError(() => new BadGatewayException(...))`, salvo fallback documentado.
- `retry()` do RxJS sem `delay`: repete imediatamente. Use `retry({ count: 3, delay: (e, n) => timer(backoff(n)) })` e filtre transitório.
- Interceptor global que faz retry: confira se o client já faz. A soma amplifica.

## Cliente de microservice e filas

- `ClientProxy.send()` sem `timeout()`: request-reply RPC pendura. `emit()` é fire-and-forget e não garante entrega: não use para efeito que não pode se perder.
- Consumidor RabbitMQ com `@golevelup/nestjs-rabbitmq`:
  - `@RabbitSubscribe` e retorno `Nack(true)` incondicional gera poison loop. Defina `queueOptions.arguments` com `x-dead-letter-exchange` e `x-dead-letter-routing-key`.
  - Sem retorno explícito, o default de `errorBehavior`/`defaultSubscribeErrorBehavior` decide (`REQUEUE` por padrão em algumas versões). Confirme no `RabbitMQModule.forRoot`.
  - `prefetchCount` no `channels` ou na config do módulo. Sem ele, o consumidor recebe lote ilimitado.
  - Handler que lança após efeito parcial e requeue: duplica efeito. Exija dedup.
  - `@RabbitRPC` sem timeout no lado do cliente do RPC.
  - `publish` sem `persistent: true` e sem publisher confirms em mensagem que não pode se perder.
- Publicação de evento logo após `repository.save` sem outbox: dual write.

## Ciclo de vida

- `app.enableShutdownHooks()` ausente em `main.ts`: `OnModuleDestroy` e `OnApplicationShutdown` não rodam em `SIGTERM`. Efeito: conexões Prisma, Redis e AMQP cortadas no meio, requests em voo perdidas.
- Provider com recurso aberto (`ioredis`, `PrismaClient`, canal, `setInterval`) sem `onModuleDestroy` que fecha.
- `OnModuleInit` com `await` de dependência externa sem timeout: o boot trava e a readiness nunca fica verde. Falhe rápido com erro claro.
- Terminus (`@nestjs/terminus`): `HealthCheckService` com `PrismaHealthIndicator`/`HttpHealthIndicator` no endpoint de liveness. Mova para readiness. Cada indicator com `timeout`.
- Config: `ConfigModule.forRoot({ validate })` ou `validationSchema` (Joi/zod). Sem isso, `configService.get('X')` devolve `undefined` e o erro aparece em runtime.
- `@Cron` em múltiplas réplicas executa em todas. Exija lock (advisory lock Postgres, redlock) ou instância única de scheduler. Handler de cron com `try/catch` e log, e sem estado em memória.
- `@nestjs/schedule` com handler async sem catch: rejeição não tratada.

## Validação e erros de entrada

- `ValidationPipe` sem `whitelist` e sem `transform` é tema de contratos e segurança. Aqui importa que a pipe falhe com 400 e que o filter preserve o shape.
- `ParseIntPipe`/`ParseUUIDPipe` em params evitam 500 por `NaN` chegando ao banco.
- `exceptionFactory` customizada que lança `Error` comum vira 500.

## Interceptors, guards e async

- Interceptor com `tap` assíncrono sem catch: erro vira unhandled rejection.
- Guard que lança `Error` comum: 500 no lugar de 401/403. Lance `UnauthorizedException`/`ForbiddenException`. A lógica de authZ é do review-seguranca.
- `@Injectable({ scope: Scope.REQUEST })` cria provider por request: custo e vazamento de recurso se abrir conexão no construtor.
- Fila interna (`EventEmitter2`) com `{ async: true }` e listener sem tratamento: o erro some. Use `suppressErrors: false` ou `try/catch` com log no listener.

## Prisma dentro do Nest

- `$transaction` interativa com chamada HTTP externa dentro: segura a transação durante I/O de rede (timeout padrão da interactive transaction: 5 s). Mova a chamada para fora da transação.
- `PrismaClientKnownRequestError` com `code === 'P2002'` (unique) e `P2025` (não encontrado) tratados e mapeados para 409/404. Sem tratamento, viram 500.
- `onModuleInit` com `$connect` e `enableShutdownHooks` do Prisma, conforme versão.

## Correção típica

```ts
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  catch(e: unknown, host: ArgumentsHost) {
    if (host.getType() !== 'http') throw e;
    const res = host.switchToHttp().getResponse<Response>();
    const { status, body } = mapError(e); // domínio -> 4xx, dependência -> 502/503, resto -> 500
    if (status >= 500) this.logger.error({ err: e }, 'unhandled');
    res.status(status).json(body);
  }
}
```

```ts
// main.ts
app.enableShutdownHooks();
```

```ts
const data = await firstValueFrom(
  this.http.get<Dto>(url).pipe(timeout(5_000), retry({ count: 2, delay: (_e, n) => timer(200 * 2 ** n) }), map((r) => r.data)),
);
```
