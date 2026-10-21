# Queries com Prisma, TypeORM, knex, drizzle, pg e Postgres

## Prisma: N+1 e carregamento

- `findMany` seguido de `map` com `await prisma.x.find*`: N+1. Correção: `include`/`select` aninhado, ou `where: { id: { in } }` com `Map`.
- `include` aninhado em 3+ níveis em lista grande. Padrão `relationLoadStrategy: 'query'` (default) faz 1 query por relação. `relationLoadStrategy: 'join'` (preview em algumas versões, estável nas recentes) faz 1 query com `LATERAL JOIN`. Em relação 1-N com muitos filhos, `join` repete as colunas do pai por filho. Meça.
- `include: { relacao: true }` traz todas as colunas da relação. Use `select` aninhado para as colunas usadas.
- `findMany()` sem `take`: sem limite. `take` sem `orderBy` determinístico: ordem arbitrária.
- Paginação por cursor: `cursor: { id }, skip: 1, take: n, orderBy: { id: 'asc' }`. Ordenação por campo não único exige `orderBy: [{ createdAt: 'desc' }, { id: 'desc' }]`, e o cursor precisa de índice nessa ordem.
- `count` em toda requisição: `prisma.x.count({ where })` faz `SELECT COUNT(*)`. Em tabela grande, cache ou `take + 1`.
- Filtros `contains` (vira `LIKE '%x%'`), `mode: 'insensitive'` (vira `ILIKE`): seq scan. Correção: `pg_trgm` com GIN, ou full-text via SQL cru.
- `where: { OR: [...] }` com colunas diferentes: plano pior. Meça.
- `distinct` do Prisma pode executar em memória no client (depende da versão e do `orderBy`). Para volume, `groupBy` ou SQL cru com `DISTINCT ON`.
- `groupBy`/`aggregate` em vez de `findMany` e `reduce`.
- `$queryRaw` com `Prisma.sql` para joins e janelas que o client não gera. Verifique `bigint` em `COUNT(*)` (o tipo é do review-tipagem).
- `findUnique` em loop: dataloader do Prisma (`@prisma/client` agrupa `findUnique` do mesmo tick em `IN` quando as chamadas são feitas no mesmo tick, via `Promise.all`). Em `for ... await` sequencial, o agrupamento não ocorre.
- Relação `onDelete: Cascade` com filhos numerosos: delete do pai varre a filha. A FK precisa de índice (Prisma não cria índice em FK no Postgres automaticamente; `@@index([fk])` explícito).

## Prisma: escrita e transação

- `create`/`update` em loop: `createMany({ data, skipDuplicates })`, `updateMany`, ou SQL com `unnest`/`VALUES`. `createMany` não retorna os registros (use `createManyAndReturn` nas versões que têm).
- `upsert` em loop: `INSERT ... ON CONFLICT DO UPDATE` em lote por SQL cru. O `upsert` do Prisma usa `ON CONFLICT` nativo só quando as condições do `where` permitem, senão faz select e depois escreve.
- `$transaction([a, b])` (batch): uma conexão, sequencial, curta. `$transaction(async (tx) => ...)` (interativa): segura a conexão pelo tempo do callback, e tem `maxWait` (2 s) e `timeout` (5 s) por padrão. I/O externo dentro dela é achado.
- Operações independentes dentro de `$transaction` interativa com `Promise.all`: serializam na conexão. Sem ganho.
- Increment atômico: `data: { total: { increment: 1 } }` e não ler, somar e escrever.
- Concorrência otimista: coluna `version` e `updateMany({ where: { id, version } })` com checagem de `count`.
- `SELECT ... FOR UPDATE` só por `$queryRaw` dentro de transação interativa.

## Prisma: conexão

- Uma instância de `PrismaClient` por processo. Padrão em NestJS: `PrismaService extends PrismaClient` com `onModuleInit`/`enableShutdownHooks`, provider singleton. Sinal: `new PrismaClient()` em service, handler, função utilitária, ou em módulo importado por vários pontos.
- Em hot reload de desenvolvimento, `globalThis.prisma`. Não é achado de produção.
- `connection_limit` na `DATABASE_URL` (default `num_cpus * 2 + 1`). Total = instâncias × réplicas × `connection_limit` precisa caber em `max_connections` (ou no PgBouncer). `pgbouncer=true` na URL em modo transaction.
- Query lenta que segura a conexão por mais que o `pool_timeout` (10 s): `P2024` (timeout do pool). Sinal de esgotamento.

## TypeORM

- `relations: [...]`/`leftJoinAndSelect`: carga eager. `eager: true` na entidade carrega a relação em todo `find`, em toda query. Impacto: join extra invisível. Correção: eager só onde sempre usada, caso contrário `relations` por consulta.
- Lazy relations (`Promise<T>`) são N+1 em loop.
- `find()` sem `take`. `skip/take` com joins: o TypeORM faz 2 queries (ids distintos, depois dados) quando há relações de coleção. Para `getMany()` com `leftJoinAndSelect` de coleção, `take` age sobre as linhas já multiplicadas, e por isso use `skip/take` e não `limit/offset` no QueryBuilder.
- `save()` em loop: um round trip por entidade. `insert()` em lote, `createQueryBuilder().insert().values([...])`, `save(arrayDeEntidades)` com `chunk`.
- `synchronize: true` em produção: é do review-migrations.
- `QueryRunner` sem `release()`.
- `repository.count()` em toda requisição (mesmo cuidado do Prisma).

## knex, pg, drizzle

- `knex.batchInsert` para lotes. `.select('*')`.
- `pg.Pool`: um por processo. `max` padrão é 10. `pool.connect()` sem `release()` em `finally` vaza. Consulta única: `pool.query`.
- Parametrização (`$1`) também ajuda o planejamento. Parâmetro com tipo diferente da coluna dispara coerção.
- `types.setTypeParser`: mudança global de parsing.
- drizzle: `db.query.x.findMany({ with: {...} })` gera 1 query com `LATERAL` json. `db.select()` sem colunas traz todas.

## Postgres: padrões a reconhecer no SQL do diff

```sql
-- função sobre coluna indexada, índice ignorado
WHERE lower(email) = lower($1)
-- índice funcional que resolve
CREATE INDEX CONCURRENTLY idx_user_email_lower ON "User" (lower(email));

-- data por cast, índice ignorado
WHERE created_at::date = '2026-10-10'
-- range sargable
WHERE created_at >= '2026-10-10' AND created_at < '2026-10-11'

-- offset profundo
SELECT ... ORDER BY created_at DESC, id DESC OFFSET 100000 LIMIT 20
-- keyset
SELECT ... WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT 20

-- NOT IN com NULL
WHERE id NOT IN (SELECT user_id FROM bans)
-- semi-join seguro
WHERE NOT EXISTS (SELECT 1 FROM bans b WHERE b.user_id = u.id)

-- lista grande
WHERE id IN ($1, $2, ... $5000)
-- array
WHERE id = ANY($1::uuid[])
```

- `ORDER BY random()` em tabela grande: seq scan e sort. Correção: `TABLESAMPLE`, ou sorteio por id.
- `OFFSET` com `ORDER BY` por coluna sem índice: sort completo por página.
- `LIMIT 1` sem `ORDER BY`: resultado arbitrário.
- CTE: no Postgres 12+ é inlined por padrão quando referenciada uma vez, e `MATERIALIZED` força materialização. Em versões ≤11, CTE é barreira de otimização.
- `UNION` (dedup, sort) versus `UNION ALL` quando não há duplicata possível.
- `COUNT(DISTINCT x)` em tabela grande: caro.
- `jsonb`: `col @> '{"k":"v"}'` usa GIN. `col->>'k' = 'v'` precisa de índice funcional na expressão.
- `FOR UPDATE SKIP LOCKED` para filas em tabela.
- `SELECT ... FOR UPDATE` sem `ORDER BY` consistente entre transações: deadlock.
- `UPDATE` de muitas linhas numa transação só: bloat e lock longo. Lotes de 1000-10000 com `commit` entre eles (backfill é do review-migrations).
- Tabela grande com `UPDATE` frequente: `fillfactor` e HOT updates. Índice em coluna que muda a cada update impede HOT. Raro de aparecer no diff, mencione só com evidência.
- Autovacuum e estatísticas: depois de carga em massa, `ANALYZE`.

## Ler o plano (quando pedir EXPLAIN)

Peça: `EXPLAIN (ANALYZE, BUFFERS, SETTINGS) <consulta com parâmetros reais>` em banco com volume parecido com produção. O que procurar:

- `Seq Scan` em tabela grande com `Rows Removed by Filter` alto: falta índice ou índice inutilizado.
- `Index Scan` com `Heap Fetches` alto: covering/visibility map.
- `Nested Loop` com `loops=` grande sobre filho: N+1 dentro do plano, índice faltando na junção.
- `Sort Method: external merge Disk`: `work_mem` ou índice para a ordenação.
- `rows=` estimado muito diferente do real: estatísticas velhas (`ANALYZE`), ou correlação entre colunas (`CREATE STATISTICS`).
- `Buffers: shared read` alto: cache frio ou scan grande.
- `Planning Time` alto com muitas partições ou joins.
