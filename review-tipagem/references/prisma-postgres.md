# Tipagem com Prisma, TypeORM e SQL cru

## Prisma

- O client gera tipos a partir do `schema.prisma`. Sinal: tipo manual que espelha um model (`interface User { id: string; ... }`). Correção: `import type { User } from '@prisma/client'`, ou `Prisma.UserGetPayload<{ include: { enrollments: true } }>`.
- Retorno de query com `select`/`include`: o tipo muda com o argumento. Funções que devolvem esse resultado: use `Prisma.validator<Prisma.UserDefaultArgs>()({ include: ... })` e `Prisma.UserGetPayload<typeof args>` para uma fonte só.
- `Prisma.Decimal`: serializa para string e não é `number`. Sinal: `row.price as unknown as number`. Correção: `row.price.toNumber()` com atenção à precisão, ou manter `Decimal` e converter na borda do DTO.
- `BigInt`: não serializa em `JSON.stringify`. Sinal: campo `BigInt` retornado direto em resposta. Correção: converter para `string` no DTO.
- `Prisma.JsonValue`/`Json` colunas: o tipo é a união de JSON. Cast `as MyType` é afirmação. Correção: schema para parse ao ler, ou `prisma-json-types-generator` com anotação no schema.
- `$queryRaw<T>` e `$queryRawUnsafe<T>`: o genérico é cast. `bigint` de `COUNT(*)` chega como `bigint` (não `number`), `numeric` como `Decimal`, `timestamp` como `Date`. Sinal: `$queryRaw<{ total: number }[]>` com `COUNT(*)`. Impacto: `total` é `bigint` em runtime e `total + 1` lança `TypeError`. Correção: `COUNT(*)::int` no SQL, ou converter com `Number()` com atenção ao tamanho, e parse com schema.
- `Prisma.sql` e `Prisma.join` tipam parâmetros e evitam concatenação (injeção é do review-seguranca).
- `UncheckedCreateInput` versus `CreateInput`: não misture `connect` e `userId`. Sinal: erro de tipo contornado com `as any`.
- Campo opcional do model (`String?`) vira `string | null`. Sinal: DTO com `string | undefined` mapeado direto de `string | null`. Impacto: `null` vaza no JSON e o consumidor trata `undefined`.
- `findUnique` devolve `T | null`. `findUniqueOrThrow`/`findFirstOrThrow` devolvem `T`. Sinal: `(await prisma.x.findUnique(...))!`. Correção: `findUniqueOrThrow` com o erro tratado em filtro (`PrismaClientKnownRequestError` código `P2025`).
- Extensões de client (`$extends`) mudam o tipo do client: funções que recebem `PrismaClient` precisam do tipo estendido (`typeof prismaExtended`).
- Tipo de transação: `Prisma.TransactionClient` em funções chamadas dentro de `$transaction(async (tx) => ...)`.
- Enum do Prisma: importado de `@prisma/client` e é objeto const mais union de literais. Duplicar o enum à mão é drift.

## TypeORM

- Entidade com `@Column() foo: string | null`: o metadado de runtime é `Object`. Correção: `@Column({ type: 'varchar', nullable: true }) foo!: string | null`.
- `Repository<Entity>.findOne` devolve `Entity | null`. Sinal: `!` ou `as Entity`.
- `QueryBuilder.getRawMany()` devolve `any[]`. Tipar com parse.
- `numeric`/`decimal` chegam como `string` no driver `pg`. Sinal: campo `number` no entity com coluna `numeric`. Correção: `transformer` na coluna, ou tipo `string` e conversão explícita.
- `bigint` chega como `string`. Mesmo tratamento.
- Relações com `lazy` retornam `Promise<T>`: tipo precisa refletir.

## Knex, pg, drizzle

- `knex<Foo>('t')` e `.select()` com genéricos de linha são casts. Linhas com `numeric`/`bigint` vêm como string. Parse ou transformação explícita.
- `pg` `pool.query<Foo>()` é cast. `types.setTypeParser` global muda o tipo de todas as colunas daquele OID: mudança no parser exige revisar todos os consumidores.
- `drizzle-orm`: inferência por `$inferSelect`/`$inferInsert` é a fonte do tipo. Tipo manual espelhado é drift.

## Tipos de coluna e TypeScript

| Coluna Postgres | Chega no driver | Tipo TS honesto |
|---|---|---|
| `int4`, `int2` | `number` | `number` |
| `int8`/`bigint`, `COUNT(*)` | `string` (pg) ou `bigint` (Prisma) | `string` ou `bigint` |
| `numeric` | `string` (pg), `Decimal` (Prisma) | `string` ou `Decimal` |
| `timestamptz` | `Date` | `Date` |
| `timestamp` (sem tz) | `Date` interpretada no fuso do processo | `Date`, com a decisão de fuso documentada |
| `date` | `Date` (meia-noite local) ou `string` | `string` `YYYY-MM-DD` na borda |
| `jsonb` | objeto | `unknown` e parse |
| `uuid` | `string` | `string` (brand opcional) |
| `text[]` | `string[]` | `string[]` |

Sinal: tipo TS declarado como `number` para `int8` ou `numeric`. Impacto: soma por concatenação de strings (`"10" + "5" = "105"`) ou `TypeError` com `bigint`.
