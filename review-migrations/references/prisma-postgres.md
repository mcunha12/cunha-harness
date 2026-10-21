# Migrations em Prisma, TypeORM, Knex, Drizzle e PostgreSQL

## Lock por statement (Postgres)

| Statement | Lock | Bloqueia | Seguro quando |
|---|---|---|---|
| `CREATE INDEX` | SHARE | INSERT/UPDATE/DELETE | tabela vazia ou pequena |
| `CREATE INDEX CONCURRENTLY` | SHARE UPDATE EXCLUSIVE | só DDL concorrente | sempre (fora de transação) |
| `DROP INDEX` | ACCESS EXCLUSIVE | tudo | rápido, mas enfileira. Use `CONCURRENTLY` |
| `ADD COLUMN` (nullable ou default constante, PG ≥ 11) | ACCESS EXCLUSIVE curto | tudo, por ms | sempre, com `lock_timeout` |
| `ADD COLUMN` default volátil | ACCESS EXCLUSIVE + rewrite | tudo | nunca em tabela grande |
| `ALTER COLUMN TYPE` | ACCESS EXCLUSIVE + rewrite | tudo | só tipos binary-coercible |
| `SET NOT NULL` | ACCESS EXCLUSIVE + scan | tudo | com CHECK validado antes (PG ≥ 12) |
| `ADD FOREIGN KEY` | SHARE ROW EXCLUSIVE nas duas tabelas | escrita | com `NOT VALID` + `VALIDATE` |
| `ADD CHECK` | ACCESS EXCLUSIVE + scan | tudo | com `NOT VALID` + `VALIDATE` |
| `VALIDATE CONSTRAINT` | SHARE UPDATE EXCLUSIVE | só DDL | sempre |
| `ADD UNIQUE`/`PRIMARY KEY` | ACCESS EXCLUSIVE + build | tudo | via índice concorrente + `USING INDEX` |
| `DROP COLUMN` | ACCESS EXCLUSIVE curto | tudo, por ms | no contract, sem leitores |
| `RENAME` | ACCESS EXCLUSIVE curto | tudo | só com expand/contract |
| `TRUNCATE` | ACCESS EXCLUSIVE | tudo | dado descartável |
| `VACUUM FULL`, `CLUSTER` | ACCESS EXCLUSIVE + rewrite | tudo | janela de manutenção |
| `REINDEX` | ACCESS EXCLUSIVE | tudo | `REINDEX CONCURRENTLY` (PG ≥ 12) |

`ACCESS EXCLUSIVE` bloqueia até `SELECT`. Um DDL que espera atrás de uma transação longa forma fila: todas as queries seguintes esperam o DDL. Por isso o `lock_timeout` importa mais que a duração do DDL.

## Cabeçalho de migration segura

```sql
SET lock_timeout = '3s';
SET statement_timeout = '60s';
```

O deploy repete a migration quando o timeout estoura. Num migration runner que usa uma conexão de pool, `SET LOCAL` dentro da transação evita vazar a configuração para outras queries.

## Padrões seguros

```sql
-- SET NOT NULL sem scan bloqueante (PG >= 12)
ALTER TABLE aluno ADD CONSTRAINT aluno_email_nn CHECK (email IS NOT NULL) NOT VALID;
ALTER TABLE aluno VALIDATE CONSTRAINT aluno_email_nn;
ALTER TABLE aluno ALTER COLUMN email SET NOT NULL;
ALTER TABLE aluno DROP CONSTRAINT aluno_email_nn;
```

```sql
-- FK sem bloquear escrita
ALTER TABLE matricula ADD CONSTRAINT matricula_turma_fk FOREIGN KEY (turma_id) REFERENCES turma(id) NOT VALID;
ALTER TABLE matricula VALIDATE CONSTRAINT matricula_turma_fk;
```

```sql
-- UNIQUE sem lock longo
CREATE UNIQUE INDEX CONCURRENTLY matricula_aluno_turma_key ON matricula (aluno_id, turma_id);
ALTER TABLE matricula ADD CONSTRAINT matricula_aluno_turma_key UNIQUE USING INDEX matricula_aluno_turma_key;
```

```sql
-- Backfill em lote, idempotente
UPDATE avaliacao SET nota = nota_final
WHERE id IN (SELECT id FROM avaliacao WHERE nota IS NULL ORDER BY id LIMIT 5000);
```

Repita o `UPDATE` num loop de aplicação ou job até `0 rows`. Um `COMMIT` por lote.

## Prisma Migrate

- **Fluxo.** `prisma migrate dev` gera e aplica em desenvolvimento. `prisma migrate deploy` aplica as pendentes em produção, sem shadow database, sem `reset`. `db push` não grava histórico e serve a protótipo. `db push`, `migrate reset` e `--accept-data-loss` em script de deploy ou CI de produção: BLOCKER.
- **Rename.** Renomear campo ou model no `schema.prisma` faz o Prisma gerar `DROP` + `ADD` (ou `DROP TABLE` + `CREATE TABLE`). O dado some. Com `@map("nome_antigo")` o nome físico permanece e o rename vira só do cliente. Para renomear fisicamente: edite o SQL gerado para `ALTER TABLE ... RENAME COLUMN ...` (sem `--create-only` o Prisma já aplicou: use `prisma migrate dev --create-only`, edite, aplique) e faça expand/contract se há tráfego.
- **Warnings do Prisma.** O CLI avisa "You are about to drop the column ... which contains N non-null values". `--accept-data-loss` silencia. Sinal de BLOCKER.
- **Sem `down`.** Exija plano de rollback no PR: SQL inverso manual ou migration corretiva. O Prisma não executa `down`.
- **Migration editada após aplicada.** O Prisma guarda checksum. `migrate deploy` em ambiente que já aplicou falha com "migration was modified". Correção: migration nova. `prisma migrate resolve --applied` ou `--rolled-back` só com decisão humana.
- **Drift.** `schema.prisma` alterado sem migration (ou migration sem alteração do schema). `prisma migrate diff --from-migrations prisma/migrations --to-schema-datamodel prisma/schema.prisma --exit-code` (exige shadow DB) acusa a diferença.
- **Transação.** O Prisma executa o arquivo SQL como um script. `CREATE INDEX CONCURRENTLY` e `ALTER TYPE ... ADD VALUE` seguido de uso do valor falham em transação. Contorno: um statement por migration, ou execução manual e `migrate resolve --applied`.
- **`@@index` e `@unique`.** `@@index` novo gera `CREATE INDEX` comum (sem CONCURRENTLY). Em tabela quente, edite o SQL gerado.
- **Mudança de tipo no schema** (`Int` para `BigInt`, `String` para `Json`, `DateTime` para `@db.Timestamptz`): leia o `ALTER COLUMN ... TYPE` gerado, ele reescreve e pode perder dado.
- **Campo obrigatório novo** (`String` sem `?` e sem `@default`): o Prisma gera `ADD COLUMN ... NOT NULL` e falha em tabela com dados (ou avisa). Correção: opcional → backfill → obrigatório.
- **Enum.** Novo valor: `ALTER TYPE ... ADD VALUE` (ver `SKILL.md` sobre transação). Remoção: o Prisma recria o tipo e converte, com risco de falha em dado existente.
- **Relação e `onDelete`.** `onDelete: Cascade` novo em relação com histórico.
- **`@default(now())` e `@updatedAt`.** `@updatedAt` é do client, não do banco: inserts por SQL puro não atualizam.
- **`@db.Timestamp` (sem zona) vs `@db.Timestamptz`.** O Prisma usa `timestamp(3)` por padrão. Campo novo que guarda instante: `@db.Timestamptz(3)`.
- **Client desatualizado.** `prisma generate` após alterar o schema. Imagem Docker que não roda `generate` quebra em runtime.
- **Múltiplas réplicas** com `migrate deploy` no start de cada pod: o Prisma usa advisory lock, ainda assim prefira um job/hook único.
- **Pooler (pgBouncer em transaction mode).** `migrate deploy` precisa de conexão direta (`directUrl` em `datasource`). Advisory lock e prepared statements falham em transaction pooling.
- **Shadow database** exige permissão `CREATEDB`. Fora do escopo de produção.
- **`prisma migrate resolve`** em produção sem registro no PR: ação manual não rastreada.

## TypeORM

- `synchronize: true` fora de desenvolvimento: BLOCKER. Procure em `DataSource`/`TypeOrmModule.forRoot*`, em `ormconfig`, e em condicionais (`synchronize: process.env.NODE_ENV !== 'test'` liga em produção).
- `migrationsRun: true` no boot com várias réplicas.
- `migration:generate` sem revisão: gera drop+add para rename, ignora o default de DB em alguns casos, traz alterações alheias ao PR (drift acumulado).
- `down()` vazio ou que não desfaz o `up()`.
- `queryRunner.query` com SQL e `queryRunner.manager` com entidades da app dentro de migration: acopla ao model. Use SQL.
- Transação: `transaction: 'each'` (default `all`) muda o escopo. `CONCURRENTLY` exige `transaction: false` na migration (`transaction = false` na classe da migration). Confira a versão do TypeORM em uso.
- Entidade com `@Column({ nullable: false })` nova em tabela populada: o `generate` produz `NOT NULL` sem backfill.
- Mudança de `@Column({ type })`: o `generate` produz drop+add (perde dado) em vez de `ALTER TYPE`. Revise.

## Knex, Drizzle, Sequelize

- **Knex.** `exports.up`/`exports.down`. Migração roda em transação por padrão. `exports.config = { transaction: false }` para `CONCURRENTLY`. `knex.raw` com SQL: revise o SQL. `down` ausente.
- **Drizzle.** `drizzle-kit generate` produz SQL versionado e `migrate` aplica. `drizzle-kit push` é equivalente a `db push`: proibido em produção. Rename: o kit pergunta se é rename ou drop+add. Revise o SQL gerado.
- **Sequelize.** `queryInterface.changeColumn`, `renameColumn`, `removeColumn`. `sync({ force: true })`/`sync({ alter: true })` em produção: BLOCKER.

## SQL puro e Flyway/Liquibase

- Arquivo versionado imutável (`V12__x.sql`). Editar após aplicar quebra o checksum. Flyway: `repeatable` (`R__`) só para views/funções.
- `undo` pago no Flyway Community: sem `down`. Mesmo plano de rollback.
- Statement sem `IF EXISTS` em migration manual rerodável.

## Ordem, nome e organização

- Timestamp/ordem monotônica. Nome descreve a operação (`add_nota_to_avaliacao`), não `update`/`fix`.
- Uma preocupação por migration. DDL de lock e backfill em migrations separadas.
- Migration junto com o código no mesmo PR quando é expand. Contract em PR posterior.
- Arquivo de migration gerado com alteração alheia (drift de outro PR): remova o ruído e confirme que a migration representa só a mudança do PR.

## Tipos Postgres e armadilhas

- `serial` vs `generated always as identity`: prefira identity em tabela nova. Mudar depois exige trabalho com sequência.
- `varchar(n)` com `n` menor falha com dados maiores. Aumentar `n` não reescreve (PG ≥ 9.2).
- `text` + `CHECK (length(x) <= n)` com `NOT VALID` permite validar depois.
- `jsonb` com índice GIN novo: `CREATE INDEX CONCURRENTLY ... USING gin`.
- Extensão (`pg_trgm`, `pgcrypto`, `uuid-ossp`, `citext`): `CREATE EXTENSION IF NOT EXISTS` precisa de privilégio. Confirme no RDS/Cloud SQL.
- Partição: `ATTACH PARTITION` com `CHECK` validado antes evita scan sob lock.
- `ALTER TABLE ... SET (fillfactor)`, `autovacuum_*`: afeta só novas páginas, sem rewrite.
- Replicação lógica: `ALTER TABLE` sem PK em tabela publicada quebra `UPDATE/DELETE` (REPLICA IDENTITY).

## Perguntas rápidas de volume (Postgres)

```sql
SELECT reltuples::bigint AS linhas_estimadas, pg_size_pretty(pg_total_relation_size(oid)) AS tamanho FROM pg_class WHERE relname = 'tabela';
SELECT pid, now() - xact_start AS idade, state, query FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY idade DESC LIMIT 5;
```

A segunda mostra transações longas que seguram a fila de lock. Cite essas queries no `problem` como o que confirmaria o achado.

## Falsos positivos frequentes

- `ALTER TABLE ... ADD COLUMN x text` nullable: instantâneo.
- `CREATE INDEX` em tabela criada na mesma migration.
- `NOT NULL` em coluna da tabela recém criada.
- `DROP COLUMN` no contract com o expand já em produção.
- `@@map`/`@map` mudado sem SQL gerado.
- `down` ausente no Prisma.
