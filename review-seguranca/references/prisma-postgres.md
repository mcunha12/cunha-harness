# Segurança em Prisma, TypeORM, Knex, Drizzle e Postgres

## Raw SQL

- **Prisma.** `$queryRawUnsafe(sql, ...params)` e `$executeRawUnsafe` com SQL montado por template/concatenação: injeção. Também vale para `Prisma.raw(userInput)` e `Prisma.sql` interpolando string com `Prisma.raw`. `$queryRaw` como tagged template parametriza sozinho e é seguro. Correção: trocar por `$queryRaw` com tagged template, `Prisma.sql` e `Prisma.join(ids)` para listas.
- **TypeORM.** ``query(`... ${v}`)``, ``createQueryBuilder().where(`x = ${v}`)``, `orderBy(userInput)`, `.select(userInput)`. Correção: `:param` com objeto de parâmetros, allowlist para coluna de ordenação.
- **Knex.** ``knex.raw(`... ${v}`)``, `whereRaw` sem `?`, `orderByRaw(userInput)`. Correção: bindings (`?`, `??` para identificador).
- **Drizzle.** `sql.raw(userInput)`. O tagged `sql` parametriza. `sql.identifier` para nomes.
- **pg/node-postgres.** `client.query('... ' + v)`. Correção: `client.query(text, [values])`.
- **Identificadores dinâmicos** (tabela, coluna, direção, `LIMIT`): parâmetros não cobrem. Valide contra allowlist e mapeie (`const col = ORDER_COLUMNS[sort] ?? 'created_at'`; `dir === 'desc' ? 'DESC' : 'ASC'`).
- **LIKE.** Input com `%` e `_` vira wildcard: DoS por varredura e enumeração. Escape (`\\%`) ou use `contains` do Prisma (ele escapa).

## Operadores e filtros vindos do cliente

- **Prisma.** `where: req.query`, `where: JSON.parse(filter)`, `orderBy: body.orderBy`, `include: body.include`, `select: body.select`. O cliente injeta `{ contains }`, `{ not }`, relações aninhadas (`aluno: { senha: { startsWith: 'a' } }`) e extrai dado por filtro (ataque de oráculo por busca em campo oculto). Correção: monte `where` campo a campo a partir de DTO validado.
- **`data: body` em `create`/`update`/`upsert`.** Mass assignment: grava `role`, `tenantId`, `ownerId`, `status`, `price`. Correção: objeto explícito `{ nome: dto.nome }`.
- **Nested writes do Prisma.** `data: { ...dto }` com `connect`/`create` aninhado do cliente conecta o registro a recurso alheio. Valide a forma do DTO e o ownership do id conectado.
- **`findUnique({ where: { id } })`** sem dono: BOLA. Use `findFirst({ where: { id, ownerId } })` ou `updateMany`/`deleteMany` com dono no `where` e confira `count`.
- **`update`/`delete` por id após checagem separada** (`findUnique` e depois `update`): TOCTOU entre as duas chamadas. Correção: `updateMany({ where: { id, ownerId }, data })` numa só query.
- **TypeORM `findOne(id)`/`findOne({ where: { id: undefined } })`**: `undefined` remove a condição e devolve o primeiro registro. Valide `id` antes. O mesmo vale para Prisma com `where: { id: undefined }` em `findFirst`.
- **`where: { email: body.email }` com `body.email` objeto** em TypeORM antigo: operador injetado. Valide tipo string.

## Autorização na camada de dados

- Multi-tenant: todo `findMany`/`count`/`aggregate`/`groupBy` de tabela com `tenantId` filtra por ele. Query nova sem o filtro é BLOCKER se o dado é por tenant. Considere extensão de client (`$extends` com `query.$allModels`) ou RLS como defesa em profundidade e recomende quando houver ≥3 queries sem filtro.
- Row Level Security do Postgres: `ALTER TABLE ... ENABLE RLS` sem `FORCE` não vale para o dono da tabela. Role da aplicação que é dono ou superuser ignora a política. Confira com qual role a app conecta.
- Conexão com role de superuser ou dona do schema (`postgres`) em runtime: MAJOR. A app precisa de role com `SELECT/INSERT/UPDATE/DELETE` nas tabelas e sem DDL.
- `GRANT ALL`, `PUBLIC` com privilégio em schema novo, função `SECURITY DEFINER` sem `SET search_path`: escalada de privilégio.

## Dados sensíveis

- Modelo com `passwordHash`, `cpf`, `token`, `refreshToken`, `nota`, dado de saúde e consulta sem `select`/`omit`: `findMany()` devolve todas as colunas, e a coluna nova adicionada depois também. Correção: `select` explícito ou `omit` global (`omit: { user: { passwordHash: true } }` no client do Prisma ≥ 5.16).
- Coluna de segredo ou token de terceiro em texto puro. Correção: criptografia em nível de aplicação (AES-GCM, chave fora do banco) ou hash (para tokens de verificação, guarde o hash e compare).
- `console.log(await prisma.user.findMany())`, `log: ['query']` com parâmetros em produção: queries com dados pessoais no log. Handoff para review-observabilidade.
- Backup/dump/seed com dado real de aluno no repo: BLOCKER se versionado.

## Conexão e configuração

- `DATABASE_URL` com credencial literal no código, em `schema.prisma` (`url = "postgres://..."`), em `docker-compose.yml` de prod ou em `.env` versionado. Correção: `env("DATABASE_URL")`, secret manager.
- `sslmode=disable` ou `ssl: { rejectUnauthorized: false }` em conexão para fora da rede privada. Correção: `sslmode=verify-full` com CA.
- `synchronize: true`, `migrate reset`, `db push --accept-data-loss` em script de prod: handoff para review-migrations.
- Prisma Studio, pgAdmin e portas `5432` expostas em `docker-compose` de ambiente compartilhado.
- `pg_stat_statements`/`EXPLAIN` com dados reais em canal público: fora do código, ignore.

## Transações, concorrência e abuso

- Regra de negócio com saldo/cupom/vaga: `check-then-update` sem `SELECT ... FOR UPDATE`, sem `UPDATE ... WHERE saldo >= n` condicional e sem constraint única. Impacto: race condition permite resgate duplo ou overbooking. Correção: update condicional com `count`, constraint `UNIQUE`, `Serializable` com retry, advisory lock.
- Endpoint de listagem/exportação sem `take` máximo. `take: Number(req.query.limit)` sem teto: dump completo e DoS. Correção: `Math.min(limit, 100)`.
- `count()` e busca textual livre sem rate limit em tabela grande: DoS barato (handoff review-queries para o custo).
- Busca por `contains` em coluna sensível (e-mail, CPF) com resposta que distingue 0 e N resultados: oráculo de enumeração. Restrinja o campo ou exija correspondência exata.

## Soft delete e vínculos

- Soft delete (`deletedAt`) sem filtro em query nova: devolve registro "excluído". Para dado pessoal, pedido de exclusão (LGPD) exige remoção real ou anonimização. Correção: middleware/extensão do client com filtro global e rotina de expurgo.
- Cascata (`onDelete: Cascade`) em relação com dado de auditoria: apagar usuário apaga trilha. MINOR com handoff para review-migrations.

## Falsos positivos frequentes

- `$queryRaw` tagged template com variáveis interpoladas (o Prisma converte em parâmetros).
- `$queryRawUnsafe` com SQL 100% literal e parâmetros posicionais (`$1`).
- `findUnique({ where: { id } })` em tabela pública (catálogo, curso) ou após guard que já validou ownership no mesmo fluxo.
- `findMany()` sem `select` em tabela sem colunas sensíveis.
- Conexão `sslmode=disable` em docker-compose de desenvolvimento local.
