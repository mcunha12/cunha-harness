# Resiliência — Prisma e Postgres (e ORMs de Node)

Carregue quando `prisma`, `@prisma/client`, `typeorm`, `knex`, `drizzle-orm` ou `pg` está nas deps. O desempenho de query (N+1, índice) é do review-queries. O DDL é do review-migrations. Aqui entram falha, concorrência e consistência.

## Timeouts e pool

- Prisma: `connection_limit` e `pool_timeout` na URL (`?connection_limit=10&pool_timeout=10`). O pool default é `num_cpus * 2 + 1`. Com N réplicas, N × pool pode passar de `max_connections` do Postgres. Efeito: `P1001`/`too many connections` sob escala. Correção: dimensione ou use PgBouncer (`?pgbouncer=true`).
- `PrismaClient` instanciado por request ou por chamada: cada instância abre um pool. Correção: singleton (provider do Nest, módulo único).
- `statement_timeout` e `lock_timeout` ausentes na role ou na sessão: query lenta e espera por lock seguram conexão por tempo indefinido. Defina por role (`ALTER ROLE app SET statement_timeout = '15s'`) ou na URL (`options=-c statement_timeout=15000`).
- Prisma `$transaction` interativa: `timeout` default 5 s e `maxWait` 2 s. Estouro lança `P2028` e faz rollback. Trabalho de I/O de rede dentro da transação (HTTP, LLM, e-mail) estoura e segura lock. Correção: mova I/O para fora; use `$transaction([...])` em lote quando as operações são independentes.
- `pg.Pool`: veja `node.md` (`connectionTimeoutMillis`, `query_timeout`, `pool.on('error')`, `release` no `finally`).
- TypeORM: `QueryRunner` criado manualmente sem `release()` em `finally` vaza conexão. `extra: { max, connectionTimeoutMillis, statement_timeout }`.

## Erros do Prisma

Mapeie os códigos esperados em vez de deixar virarem 500:

| Código | Significado | Resposta típica |
|---|---|---|
| `P2002` | unique constraint | 409 ou ramo idempotente (tratar como "já existe") |
| `P2025` | registro não encontrado em update/delete | 404 |
| `P2003` | FK violada | 409/422 |
| `P2034` | conflito de escrita/deadlock em transação | retry limitado (transitório) |
| `P2024` | timeout aguardando conexão do pool | 503, com alerta |
| `P1001`/`P1002` | banco inalcançável / timeout | 503, retry com backoff |

- `catch (e)` que testa `e.code` sem `e instanceof Prisma.PrismaClientKnownRequestError` acessa propriedade em tipo errado.
- `findUniqueOrThrow` e `findFirstOrThrow` lançam `P2025`/`NotFoundError`. Quem chama precisa mapear.
- `update` e `delete` sem `where` suficiente: `P2025` em corrida entre duas requests. Prefira `updateMany` com checagem de `count` quando "nenhuma linha" é caso válido.

## Concorrência e check-then-act

- Sinal: `findFirst`/`findUnique` seguido de `create`/`update` com base no resultado.

```ts
const exists = await prisma.enrollment.findFirst({ where: { userId, courseId } });
if (!exists) await prisma.enrollment.create({ data: { userId, courseId } });
```

  Impacto: duas requests simultâneas passam na checagem e criam duplicata (ou uma recebe `P2002` sem tratamento). Correção: `@@unique([userId, courseId])` e `upsert`, ou `create` com captura de `P2002`.

- Contador e saldo: `const v = await find(); update({ data: { n: v.n + 1 } })` perde incrementos. Correção: `update({ data: { n: { increment: 1 } } })`, que é atômico no banco.
- Estado com máquina de transição: `updateMany({ where: { id, status: 'PENDING' }, data: { status: 'PAID' } })` e cheque `count === 1`. Garante a transição única sem lock explícito.
- Optimistic locking: coluna `version Int @default(0)`, `where: { id, version }` e `data: { version: { increment: 1 } }`. `count === 0` indica conflito: recarregue ou devolva 409.
- Pessimistic: `SELECT ... FOR UPDATE` via `$queryRaw` dentro de `$transaction`, com `lock_timeout`. Ordem consistente de aquisição de lock evita deadlock (`40P01`).
- Isolamento: default `READ COMMITTED` no Postgres. Regra que depende de leitura estável entre duas queries precisa de `Serializable` e retry em `40001`/`P2034`, ou de lock.
- `SKIP LOCKED` para fila em tabela: permite vários workers sem disputa. Sem ele, workers bloqueiam uns aos outros.

## Transações e consistência

- Operações dependentes entre si fora de `$transaction`: falha no meio deixa estado parcial (matrícula criada sem registro de pagamento). Correção: `$transaction`.
- `$transaction([a, b])` (batch) não permite usar o resultado de `a` em `b`. Use a forma interativa.
- Efeito colateral externo dentro da transação (e-mail, evento, HTTP) executa mesmo que ocorra rollback depois. Correção: outbox na mesma transação e relay após commit; ou dispare após o `await $transaction` retornar.
- Evento publicado antes do commit: o consumidor lê o banco e não encontra o dado. Publique depois do commit.
- Cache invalidado antes do commit: a próxima leitura repopula com dado antigo. Invalide depois.
- Réplica de leitura: leitura logo após escrita pode vir defasada. Direcione para a primária no mesmo fluxo.

## Retry de banco

- Transitórios que valem retry: `40001` (serialization failure), `40P01` (deadlock), `57P01` (admin shutdown), `08006`/`08001`/`ECONNRESET` (conexão). Retry só do bloco de transação inteiro, nunca de uma instrução no meio dela.
- Não repita em `23505` (unique) nem em `23503` (FK): erro determinístico.
- Operação com efeito não idempotente dentro do bloco que repete: separe-a para depois do commit.

## Bulk e lotes

- `createMany` com `skipDuplicates: true` oculta conflito. Se o conflito indica bug, o dado some em silêncio.
- Loop de `await prisma.x.update` com milhares de itens: sem atomicidade, sem retomada. Use lote com `$transaction`, ou `updateMany`, ou SQL com `UPDATE ... FROM`. Estado de progresso persistido para retomar.
- Operação em lote sem limite de tamanho: parâmetros de bind passam de 32767 no Postgres (`P2035`/erro de protocolo). Divida em chunks.

## Cache e idempotência no banco

- Tabela `processed_events(event_id unique)` gravada na mesma transação do efeito: dedup confiável.
- `INSERT ... ON CONFLICT DO NOTHING RETURNING` informa se o evento é novo.
- Idempotency key com TTL e resposta salva: o reenvio devolve a primeira resposta.

## Correção típica

```ts
try {
  return await prisma.enrollment.create({ data: { userId, courseId } });
} catch (e) {
  if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2002') {
    return prisma.enrollment.findUniqueOrThrow({ where: { userId_courseId: { userId, courseId } } });
  }
  throw e;
}
```

```ts
const res = await prisma.order.updateMany({ where: { id, status: 'PENDING' }, data: { status: 'PAID' } });
if (res.count !== 1) throw new ConflictError('ORDER_ALREADY_PROCESSED');
```

```ts
await prisma.$transaction(async (tx) => {
  const order = await tx.order.update({ where: { id }, data: { status: 'PAID' } });
  await tx.outbox.create({ data: { type: 'order.paid', payload: { id: order.id } } });
}, { maxWait: 2_000, timeout: 5_000 });
```
