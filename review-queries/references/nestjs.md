# Queries e rotas em NestJS

## Chamadas em paralelo

- `await this.a.get(); await this.b.get();` independentes: `Promise.all`. Para múltiplos clients HTTP (`HttpService` devolve Observable): `forkJoin([...])` com `firstValueFrom`, ou `lastValueFrom(forkJoin(...))`.
- `Observable` com `.pipe(switchMap)` em série onde os passos são independentes: `forkJoin`/`combineLatest`.
- `firstValueFrom(this.http.get(...))` dentro de `for`: sequencial. Use `Promise.all` com limite.

## Camada de serviço e N+1

- Service que chama `repo.findOne` por item de uma lista recebida de outro service: N+1 entre services. Sinal clássico em Nest: método `enrich(items)` com `Promise.all(items.map(i => this.other.get(i.id)))`. Correção: método de lote no outro service (`getMany(ids)`), um `IN`.
- Interceptor ou guard que consulta o banco (carrega usuário, permissões) em toda requisição: custo fixo por requisição. Cache por requisição (`REQUEST` scope é caro: instancia o grafo por request), cache curto em Redis, ou claims no JWT.
- Providers com `Scope.REQUEST` ou `Scope.TRANSIENT` sem necessidade: recriam o provider (e a cadeia de dependências) por requisição, e propagam o escopo a quem depende. Impacto: latência e GC. Correção: `Scope.DEFAULT` com `AsyncLocalStorage`/`nestjs-cls` para dado por requisição.
- GraphQL (`@nestjs/graphql`): `@ResolveField` que consulta por pai é N+1. Correção: DataLoader com escopo de request.

## Interceptors, cache e serialização

- `CacheInterceptor`/`@UseInterceptors(CacheInterceptor)` e `@CacheTTL`: chave padrão é a URL do GET. Sem escopo de usuário, rota autenticada com dado por usuário serve resposta de um usuário a outro. Correção: `CacheKey` custom (`trackBy`) que inclui o usuário, ou não cachear.
- `@nestjs/cache-manager` v5+: TTL em milissegundos (era segundos). Sinal: `ttl: 60` achando que são 60 s (hoje são 60 ms). Verifique a versão.
- `ClassSerializerInterceptor` com entidades grandes: `instanceToPlain` por item tem custo O(itens × campos). Para listas de milhares, mapeie no SQL (`select`) e devolva objetos planos.
- `ValidationPipe` com `transform` e `whitelist` em payload grande tem custo proporcional. Limite o tamanho (`bodyParser` limit) e `@ArrayMaxSize`.
- Compressão: `compression()` middleware no `main.ts`, ou no proxy. Sinal: JSON de dezenas de KB sem compressão em nenhum nível, e a config do repo não menciona proxy.

## Redis (ioredis, cache-manager-ioredis)

- `KEYS pattern` em produção: O(N) bloqueante. Correção: `SCAN` com `COUNT`, ou índice de chaves em set.
- Loop de `GET`/`SET` por item: `MGET`, `pipeline()`, `multi()`. `await redis.get` em `for` sobre 100 chaves: 100 round trips.
- `SET key value` sem `EX`/`PX`: sem expiração. Correção: `SET key v EX 300` (ioredis: `redis.set(k, v, 'EX', 300)`).
- Stampede: `get` → miss → computa → `set` sem trava. Correção: `SET lock:key 1 NX PX 10000`, ou promise por chave em memória (`Map<string, Promise<T>>`).
- Valor grande (centenas de KB) por chave com leitura frequente: compressão ou quebra.
- `JSON.parse` de valor grande a cada requisição: event loop.
- Conexões: uma instância ioredis por processo, via provider singleton. `new Redis()` dentro de service por requisição vaza conexões. `maxRetriesPerRequest` e `enableOfflineQueue` mudam o comportamento sob falha (resiliência é do review-resiliencia).
- Pub/sub e BullMQ usam conexões dedicadas (subscriber não faz outros comandos).

## HTTP client (axios, HttpService)

- Axios por padrão sem keep-alive em Node (versões antigas): nova conexão TCP/TLS por chamada. Correção: `httpAgent`/`httpsAgent` com `keepAlive: true` e `maxSockets`. Em Node 19+, o agente global tem keep-alive por padrão.
- Timeout: do review-resiliencia.
- `responseType: 'arraybuffer'`/`'blob'` para arquivo grande em memória: `responseType: 'stream'`.
- Chamada a serviço lento sem cache onde a resposta muda raramente.

## Filas (RabbitMQ via @golevelup)

- Handler que processa mensagem com I/O pesado sem `prefetch` adequado: um consumidor com `prefetchCount` alto pega muitas mensagens e as processa em paralelo ilimitado, e com `prefetchCount: 1` sequencializa. Ajuste ao custo do handler. A semântica de ack/nack é do review-resiliencia.
- Handler que faz N+1 por mensagem. Mesmo tratamento: lote.
- Publicação em loop de milhares de mensagens com `await` por mensagem (confirm channel): `Promise.all` em blocos, ou publicar em lote.
- Trabalho pesado de endpoint: `POST` que gera relatório inline. Correção: publicar a tarefa, responder 202.

## Scheduler e cron

- `@Cron` que carrega tabela inteira em memória. Cursor ou lotes.
- Cron em várias réplicas executa N vezes. Lock distribuído (`SET NX`, `pg_advisory_lock`) ou instância única. O efeito de duplicidade é do review-resiliencia, o custo da execução repetida é daqui.

## Paginação em controllers

- `@Query() { page, limit }` sem `@Max` em `limit`. Correção: `@Max(100)` no DTO e default no servidor.
- Resposta paginada com `total`: confirme custo do `COUNT`.
