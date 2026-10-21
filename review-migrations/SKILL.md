---
name: review-migrations
description: Revisa migrations e mudanças de schema num diff (MIG) - expand/contract, locks em Postgres e MySQL, CREATE INDEX sem CONCURRENTLY, ALTER COLUMN TYPE, FK/CHECK sem NOT VALID, SET NOT NULL, backfill, reversibilidade e plano de rollback, migration de dados, ORM (Prisma, TypeORM synchronize, Alembic, Django), enum, seed e timezone. Acione em "revisa essa migration", "esse DDL trava a tabela?", "é seguro rodar em produção?", `/review-migrations` ou via master-review. NÃO cobre performance de query e índice de leitura (review-queries), contrato de API (review-contratos), autorização (review-seguranca) nem testes (test-audit).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-migrations

## Missão

Garantir que cada mudança de schema e de dados roda em produção sem derrubar o serviço, sem perder dado e sem acoplar o deploy do código ao do banco. O agente estima o lock que cada DDL pede, o tempo sob lock e o que acontece com as instâncias antigas do código durante o deploy. Cada achado traz o statement exato, o impacto com a ordem de grandeza da tabela e a migration corrigida em SQL ou no ORM. Zero achados é resultado válido.

## Escopo

Formato de cada item: sinal, impacto, correção. Detalhes de sintaxe por tecnologia em `references/`.

### 1. Expand/contract (deploy em duas fases)

Durante o deploy convivem código antigo e código novo contra o mesmo banco. Toda migration compatível com os dois lados é segura. Incompatível com um lado derruba o outro.

- **Rename de coluna ou tabela.** Sinal: `RENAME COLUMN`, `RENAME TO`, `ALTER TABLE ... RENAME`, Prisma que gera `DROP` + `ADD` para rename. Impacto: o código antigo falha em cada query até o deploy terminar. Dado some quando o ORM faz drop e add. Correção: expand (coluna nova, escrita dupla, backfill), migrar leituras, depois contract (drop) em deploy posterior.
- **Drop de coluna, tabela ou índice no mesmo deploy do código que para de usá-la.** Impacto: instância antiga ainda lê a coluna e quebra. Rollback do código não restaura o dado. Correção: deploy N remove o uso. Deploy N+1 remove a coluna.
- **NOT NULL em coluna existente.** Sinal: `ADD COLUMN x ... NOT NULL` sem default, `SET NOT NULL`. Impacto: INSERT do código antigo (que não conhece `x`) falha. Correção: nullable, deploy do código que escreve, backfill, constraint.
- **Mudança de tipo.** Sinal: `ALTER COLUMN ... TYPE`. Impacto: rewrite da tabela sob `ACCESS EXCLUSIVE` e quebra de leitura no código antigo. Correção: coluna nova com o tipo novo, escrita dupla, backfill em lotes, troca de leitura, drop da antiga.
- **Mudança de semântica** (unidade, timezone, enum com valor novo, status reinterpretado) com o mesmo nome de coluna. Correção: coluna nova com nome novo.
- **Código novo depende de coluna que a migration cria.** A migration precisa rodar antes do código novo. Documente a ordem. Se o deploy roda migration no `preDeployHook` do Helm, ela roda antes das instâncias novas e depois das antigas ainda servirem tráfego: a migration precisa ser compatível com o código antigo.
- **Cross-repo.** Banco compartilhado entre serviços: procure em repos irmãos (`related_repos`, se houver) o uso da coluna, com `grep` do nome da tabela e da coluna.

### 2. Locks e disponibilidade (Postgres)

- `CREATE INDEX` sem `CONCURRENTLY` em tabela com escrita: bloqueia INSERT/UPDATE/DELETE durante a construção (lock `SHARE`). `CONCURRENTLY` não roda dentro de transação, e o Prisma Migrate executa o arquivo como um script único (transação implícita quando há mais de um statement). Contornos a documentar no `fix`: (1) arquivo de migration com só o `CREATE INDEX CONCURRENTLY`, um statement por migration, e teste em banco de staging; (2) criar o índice por SQL manual fora do `migrate deploy` e registrar com `prisma migrate resolve --applied <nome>`.
- `DROP INDEX` sem `CONCURRENTLY`: lock `ACCESS EXCLUSIVE` curto, mas fila de lock pode bloquear tudo.
- `ALTER COLUMN TYPE` com rewrite: reescreve a tabela e os índices sob `ACCESS EXCLUSIVE`. Exceção sem rewrite: `varchar(n)` para `varchar(m)` com `m > n` ou para `text` em PG ≥ 9.2, e `numeric(p,s)` com aumento de precisão sem mudar a escala em PG ≥ 9.2.
- `ADD FOREIGN KEY`/`ADD CHECK` sem `NOT VALID`: varre a tabela inteira sob lock `SHARE ROW EXCLUSIVE`. Correção: `ADD CONSTRAINT ... NOT VALID` e depois `VALIDATE CONSTRAINT` (lock que não bloqueia escrita).
- `SET NOT NULL`: varre a tabela inteira sob `ACCESS EXCLUSIVE`. PG ≥ 12 pula o scan se já existe `CHECK (col IS NOT NULL)` validado. Correção: `ADD CONSTRAINT c CHECK (col IS NOT NULL) NOT VALID`, `VALIDATE CONSTRAINT`, `SET NOT NULL`, `DROP CONSTRAINT c`.
- `ADD COLUMN ... DEFAULT <constante>`: instantâneo em PG ≥ 11. `DEFAULT` volátil (`now()`, `random()`, `gen_random_uuid()`) reescreve a tabela. Em PG ≤ 10 todo default reescreve. Correção: coluna sem default, default separado (`SET DEFAULT`) e backfill em lotes.
- `ADD COLUMN ... GENERATED ALWAYS AS (...) STORED`: rewrite.
- `ADD UNIQUE`/`ADD PRIMARY KEY` direto: constrói índice sob lock. Correção: `CREATE UNIQUE INDEX CONCURRENTLY` e `ADD CONSTRAINT ... USING INDEX`.
- `REINDEX`, `VACUUM FULL`, `CLUSTER`, `ALTER TABLE ... SET TABLESPACE`: `ACCESS EXCLUSIVE`. `REINDEX CONCURRENTLY` em PG ≥ 12.
- `TRUNCATE`, `DROP TABLE`, `DROP COLUMN`: lock exclusivo e perda irreversível. Exigem confirmação explícita no PR.
- `lock_timeout` e `statement_timeout` ausentes: o DDL espera na fila atrás de uma transação longa e bloqueia todas as queries seguintes (fila de lock). Correção: `SET lock_timeout = '3s'; SET statement_timeout = '60s';` no começo da migration, com retry do deploy.
- Várias statements em uma migration única seguram o lock até o `COMMIT`. Divida em migrations pequenas ou garanta que cada uma é curta.
- Triggers, `ALTER TABLE ... ENABLE/DISABLE TRIGGER`, `ALTER TYPE ... ADD VALUE` (ver seção 7).
- Partições: `ATTACH PARTITION` sem `CHECK` prévio varre a tabela. Correção: `CHECK ... NOT VALID` + `VALIDATE` antes.

### 3. Locks e disponibilidade (MySQL e MariaDB)

- DDL online: `ALGORITHM=INPLACE, LOCK=NONE` ou `ALGORITHM=INSTANT` (MySQL ≥ 8.0.12 para `ADD COLUMN` no fim; ≥ 8.0.29 em qualquer posição). Sem a cláusula, o MySQL escolhe e pode copiar a tabela (`ALGORITHM=COPY` bloqueia escrita). Declare a cláusula: o servidor recusa se não puder.
- Operações que sempre copiam: mudar tipo da coluna, `CHANGE COLUMN` com tipo novo, mudar charset/collation, `DROP PRIMARY KEY`. Use `gh-ost` ou `pt-online-schema-change` em tabela grande.
- Metadata lock: DDL espera transação aberta e bloqueia as queries seguintes. Mesmo cuidado de timeout (`lock_wait_timeout`).
- `utf8` (3 bytes) em tabela nova: use `utf8mb4`.
- Foreign key com `foreign_key_checks=0` na migration: dado órfão silencioso.

### 4. Backfill

- **Fora da migration de schema.** Sinal: `UPDATE tabela SET x = ...` sem `WHERE` ou `LIMIT` na mesma migration que cria a coluna. Impacto: transação única longa, lock de linha em toda a tabela, WAL gigante, replicação atrasada, bloat. Correção: migration de schema só cria a estrutura. Script ou job separado faz o backfill.
- **Em lotes e com throttling.** `UPDATE ... WHERE id IN (SELECT id ... WHERE x IS NULL LIMIT 5000)` em loop, com `COMMIT` por lote, pausa entre lotes e observação de lag de réplica.
- **Idempotente e retomável.** O critério `WHERE x IS NULL` (ou cursor por id) permite reiniciar sem repetir trabalho nem corromper.
- **Verificação.** Contagem de linhas pendentes antes de `SET NOT NULL`/constraint. Falha se restar alguma.
- **Escrita dupla durante o backfill**, para que linhas novas já nasçam preenchidas (trigger ou código novo).
- **Dados em larga escala** (>1M linhas): estime `linhas / tamanho_do_lote × tempo_do_lote` no `problem`.

### 5. Reversibilidade e rollback

- Migration destrutiva (`DROP`, `TRUNCATE`, `DELETE` sem `WHERE`, `ALTER TYPE` com perda de precisão, `UPDATE` que sobrescreve): sinalize no título do PR e exija backup/snapshot verificado antes do deploy.
- Prisma Migrate não tem `down`. Exija no PR um plano de rollback: SQL inverso, ou "roll forward" com a migration corretiva. Rollback de código sem rollback de schema só funciona se a migration é de expand.
- Alembic: `downgrade()` vazio (`pass`) em migration que cria objeto. Django: `RunPython` sem `reverse_code`, `RunSQL` sem `reverse_sql` (impede `migrate` para trás).
- Down que perde dado (drop da coluna criada, onde a coluna já tem dados de produção): o `down` precisa dizer isso.
- Migration que não é idempotente (`CREATE TABLE` sem `IF NOT EXISTS` onde o runner pode repetir). Aceitável quando o runner registra o estado.

### 6. Migration de dados

- **Importa models da aplicação.** Sinal: `import { User } from '../models'`, Django `from app.models import X` dentro da migration (em vez de `apps.get_model`), SQLAlchemy `Base.metadata` do app, entidade TypeORM importada. Impacto: a migration quebra quando o model muda no futuro, porque o histórico fica acoplado ao código atual. Correção: SQL puro, ou o model histórico (`apps.get_model`), ou tabela declarada inline na migration.
- **Lógica de negócio na migration.** Chamadas a serviços, HTTP, filas, e-mail. Correção: job separado.
- **Dado derivado de regra que muda** (cálculo de nota, status). A migration congela a regra de hoje. Documente.
- **Dedup antes de unique.** `CREATE UNIQUE INDEX` falha se houver duplicata. Faça a query de dedup antes e documente a decisão sobre qual linha mantém.
- **Dados pessoais** em migration (cópia de CPF para tabela nova): LGPD, retenção. Handoff para review-seguranca.

### 6.1 Seeds e dados de referência

- Seed de dados de teste, usuário admin ou senha em migration que roda em produção: BLOCKER. Correção: seed por ambiente fora do runner de migrations.
- Dado de referência (tabela de status, planos) que a aplicação exige: `INSERT ... ON CONFLICT DO NOTHING`/`upsert` idempotente, ids explícitos.

### 7. Enum, tipos e timezone

- **Enum.** `ALTER TYPE ... ADD VALUE` não roda dentro de transação em PG < 12. Em PG ≥ 12 roda, e o valor novo só pode ser usado depois do `COMMIT`. Migration Prisma com `ADD VALUE` e uso do valor no mesmo arquivo falha. Contorno: `ADD VALUE` sozinho numa migration, uso em migration seguinte. Remover valor de enum exige recriar o tipo (`CREATE TYPE ..._new`, `ALTER COLUMN TYPE ... USING col::text::tipo_novo`) com rewrite. Alternativa: `text` + `CHECK` ou tabela de domínio.
- **Enum no código antigo.** Valor novo de enum emitido pelo código novo e lido por consumidor antigo: quebra de contrato (handoff review-contratos).
- **Timezone.** `timestamp` sem `tz` guarda hora local sem zona. Prefira `timestamptz`. Converter `timestamp` para `timestamptz` com `USING col AT TIME ZONE 'UTC'` define a zona explicitamente. Sem `USING`, o Postgres assume a zona da sessão. `DEFAULT now()` com `timestamp` e sessão em zona não UTC grava hora local.
- **Precisão.** Dinheiro em `float` ou `real`: use `numeric(p,s)` ou inteiro em centavos.
- **Chaves.** `serial`/`int` em tabela que crescerá além de 2^31: `bigint`. Troca posterior é rewrite.
- **UUID.** `gen_random_uuid()` exige PG ≥ 13 (ou `pgcrypto`). `uuid_generate_v4()` exige `uuid-ossp`.
- **Extensão** nova (`CREATE EXTENSION`) exige privilégio de superuser/rds_superuser: confirme no ambiente.
- **Collation/charset.** Mudar altera ordenação e unicidade e reconstrói índices.

### 8. ORM e fluxo de deploy

- **TypeORM `synchronize: true` fora de desenvolvimento**: BLOCKER. O TypeORM altera o schema no boot de cada instância, pode dropar coluna e roda concorrente em várias réplicas.
- **Prisma `db push`** em ambiente com dados e `migrate reset`/`--accept-data-loss` em script de deploy: BLOCKER. Prisma em produção usa `prisma migrate deploy`.
- **Prisma `migrate dev`** em CI/produção: não é o comando de deploy.
- **Prisma: migration editada depois de aplicada.** O checksum muda e `migrate deploy` falha com drift. Correção: migration nova.
- **Prisma: rename detectado como drop+add.** Renomear campo no `schema.prisma` gera `DROP COLUMN` + `ADD COLUMN` e perde dado. Correção: editar o SQL gerado para `RENAME COLUMN` (ou fazer expand/contract).
- **Prisma: `schema.prisma` alterado sem migration** correspondente no diff (ou o contrário): drift.
- **Alembic `--autogenerate` sem revisão**: gera drop de tabela que o metadata não conhece, perde `server_default`, não detecta rename, ignora enums e CHECK. Leia o script gerado.
- **Django `makemigrations`** que gera `RemoveField`/`AlterField` no mesmo release do código; `RunPython` sem `atomic=False` para operações longas; `AddField` com default em tabela grande.
- **Knex/Sequelize/TypeORM migrations** com `up` sem `down`.
- **Múltiplas heads/migrations conflitantes**: dois PRs criam migrations com a mesma base (Alembic multiple heads, Django conflito de `0003_`, Prisma com timestamps fora de ordem). Verifique ordem e dependências.
- **Execução concorrente**: várias réplicas rodando migration no boot sem lock (advisory lock). Prisma `migrate deploy` usa lock; scripts caseiros não.

### 9. Integridade e modelagem

- Constraint ausente que o código assume (`UNIQUE`, `NOT NULL`, FK): o código garante na aplicação e dois requests concorrentes violam. Correção: constraint no banco (via `NOT VALID` + `VALIDATE` em tabela grande).
- FK sem índice na coluna filha: `DELETE` no pai varre a filha (handoff review-queries para o índice, aqui só o DDL).
- `ON DELETE CASCADE` em relação com dado de auditoria/financeiro: apagar o pai apaga o histórico.
- Tabela nova sem PK, sem `created_at`, sem índice na FK.
- Coluna `jsonb` onde há campos consultados e constraints. MINOR.

## Fora de escopo, com dono

| Tema | Dono |
|---|---|
| Índice para acelerar leitura, N+1, plano de query | review-queries |
| Contrato de API/evento afetado pelo novo campo ou enum | review-contratos |
| Dado pessoal novo, SQL injection em migration | review-seguranca |
| Timeout, retry e idempotência do runner de job | review-resiliencia |
| Tipo TS do model diferente do schema | review-tipagem |
| Teste da migration, teste do backfill | test-audit |

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia `references/prisma-postgres.md` quando houver `prisma`, `typeorm`, `knex`, `drizzle-orm`, `pg` ou arquivos `.sql`. Leia `references/python.md` quando houver Alembic, Django ou SQLAlchemy.
3. Obtenha o diff. Se o orquestrador enviou um context packet, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged e arquivos novos. Com `--path`, restrinja ao glob.
4. Encontre o escopo: arquivos em `migrations/`, `prisma/migrations/`, `alembic/versions/`, `db/migrate`, `*.sql`, `schema.prisma`, `*.entity.ts`, `models.py`, config do ORM (`synchronize`, `DATABASE_URL`) e scripts de deploy que rodam migration. Sem nada disso no diff, devolva `skipped_reason`.
5. Descubra o contexto de execução: versão do Postgres/MySQL (Docker, `docker-compose`, Terraform, README), como a migration roda em produção (`prisma migrate deploy`, Helm `preDeployHook`, `alembic upgrade head`, boot da app), se roda em transação, e o tamanho provável da tabela (procure comentário do autor, volumetria no PR, outras migrations, `README`). Sem versão ou volume, use o pior caso plausível, `confidence: media` e diga o que confirmaria.
6. Para cada statement do SQL, classifique: lock pedido, rewrite, scan, destrutivo, compatível com código antigo. Para `schema.prisma` alterado, leia o SQL gerado, que é o que roda.
7. Verifique o contexto. Abra o código que usa a tabela e a coluna (query, DTO, model). Confira se o código novo e o antigo funcionam contra o schema novo. Procure a mesma tabela em outras migrations do diff (a ordem importa).
8. Classifique pela rubrica abaixo e pela global.
9. Emita no output contract. Prefixo `MIG`. Máximo de ~15 achados. O `fix` traz a migration corrigida (SQL) ou o plano em fases (migration 1, deploy, migration 2).
10. Standalone: mostre o markdown ao final. Não altere código.

## Rubrica de severidade

**BLOCKER**
- `synchronize: true` em config de produção, `prisma db push` ou `migrate reset` em script de deploy.
- `DROP COLUMN`/`DROP TABLE`/rename no mesmo PR do código que deixa de usar o objeto, ou `DROP` de coluna que o código ainda lê.
- `ALTER COLUMN ... TYPE` ou `SET NOT NULL` em tabela grande com escrita constante, sem plano de janela.
- Migration de dados que sobrescreve ou apaga dado sem backup nem `WHERE` verificável.
- Seed de senha/usuário admin em migration de produção.

**MAJOR**
- `CREATE INDEX` sem `CONCURRENTLY` em tabela com escrita contínua (vira BLOCKER com volume confirmado >1M linhas e sem janela).
- `ADD FOREIGN KEY`/`CHECK` sem `NOT VALID` em tabela grande.
- Backfill dentro da migration de schema, sem lote.
- Falta `lock_timeout` em DDL de lock exclusivo.
- Migration que importa models da aplicação.
- Prisma sem plano de rollback em migration destrutiva.

**MINOR**
- `timestamp` sem timezone em coluna nova.
- `down`/`downgrade` vazio em migration reversível de baixo risco.
- FK sem índice na coluna filha em tabela pequena.
- Tabela nova sem `created_at`.

**NIT**
- Nome de migration pouco descritivo, constraint sem nome explícito.

Calibragem: o impacto depende do volume e do tráfego. Sem volume no diff, assuma `confidence: media` e escreva no `problem` o que confirmaria (`SELECT reltuples::bigint FROM pg_class WHERE relname = 'x'`). Tabela criada na própria migration, vazia, não sofre os riscos de lock.

## Heurísticas anti-falso-positivo

- Tabela criada no mesmo PR (vazia): `CREATE INDEX`, `ADD FOREIGN KEY`, `SET NOT NULL` e `ALTER TYPE` são seguros e rápidos.
- Tabela pequena e de baixo tráfego (configuração, catálogo, <10 mil linhas) com DDL de lock curto. Reporte no máximo como NIT.
- `ADD COLUMN` nullable sem default: instantâneo em qualquer versão.
- `ADD COLUMN ... DEFAULT <constante> NOT NULL` em PG ≥ 11: instantâneo. Confirme a versão antes de reportar.
- `CREATE INDEX` sem `CONCURRENTLY` em banco que o time derruba em janela de manutenção documentada, ou em projeto sem produção ainda.
- `DROP` em contract phase com o PR anterior (expand) já em produção. Confirme no histórico de commits/ticket antes de reportar. Se não dá para confirmar, `confidence: media`.
- Migration de dev/test (`docker-compose.test.yml`, fixtures).
- `ALTER TYPE ... ADD VALUE` em PG ≥ 12 numa migration que não usa o valor novo na mesma transação.
- Alteração de tipo que não reescreve (`varchar(50)` para `varchar(100)`, `varchar` para `text`).
- Diff de `schema.prisma` só com `@@map`, `@map`, comentários e relações virtuais: Prisma não gera SQL. Confira o SQL da migration.
- `down` ausente no Prisma: a ferramenta não tem. Peça o plano de rollback, não o `down`.

## Ferramentas determinísticas opcionais

Rode só se instaladas. Nunca instale. A saída é insumo, não veredito.

| Ferramenta | Checagem | Execução |
|---|---|---|
| squawk | `command -v squawk` | `squawk <arquivos .sql do diff>` (aceita `--reporter json`) |
| Prisma | `test -x node_modules/.bin/prisma` | `node_modules/.bin/prisma migrate diff --from-migrations prisma/migrations --to-schema-datamodel prisma/schema.prisma --script` mostra drift. Exige `--shadow-database-url` |
| Alembic | `command -v alembic` | `alembic heads` (mais de um head é conflito), `alembic upgrade head --sql` gera o SQL sem executar |
| Django | `test -f manage.py` | `python manage.py makemigrations --check --dry-run` e `python manage.py sqlmigrate <app> <n>` |
| TypeORM | `test -x node_modules/.bin/typeorm` | `typeorm migration:show` |
| sqlfluff | `command -v sqlfluff` | `sqlfluff lint <arquivos> --dialect postgres` |
| git | sempre | `git diff --name-status <base>...HEAD -- '*migrations*' '*.sql' '*schema.prisma'` |

Squawk regras úteis: `require-concurrent-index-creation`, `adding-not-nullable-field`, `ban-drop-column`, `ban-drop-table`, `changing-column-type`, `constraint-missing-not-valid`, `renaming-column`, `renaming-table`, `prefer-bigint-over-int`, `prefer-timestamptz`, `disallowed-unique-constraint`. Squawk não conhece o volume da tabela. Pese cada resultado com o contexto.

## Exemplos

### Achado 1: índice com lock de escrita

```json
{
  "id": "MIG-001",
  "agent": "review-migrations",
  "severity": "MAJOR",
  "confidence": "media",
  "category": "Lock: CREATE INDEX sem CONCURRENTLY",
  "location": { "repo": "exemplo-api", "file": "prisma/migrations/20261010120000_add_idx_progresso/migration.sql", "lines": "1" },
  "evidence": "CREATE INDEX \"progresso_aluno_id_aula_id_idx\" ON \"progresso\"(\"aluno_id\", \"aula_id\");",
  "problem": "O CREATE INDEX comum pede lock SHARE e bloqueia INSERT/UPDATE/DELETE em progresso até terminar. A tabela recebe escrita a cada aula assistida. Com milhões de linhas o índice leva minutos e a gravação de progresso fica parada. Para confirmar o volume: SELECT reltuples::bigint FROM pg_class WHERE relname = 'progresso'.",
  "fix": "Prisma envolve a migration em transação e CONCURRENTLY não roda em transação. Crie o índice fora do migrate: CREATE INDEX CONCURRENTLY IF NOT EXISTS progresso_aluno_id_aula_id_idx ON progresso (aluno_id, aula_id); depois mantenha o arquivo da migration só com um comentário e rode prisma migrate resolve --applied 20261010120000_add_idx_progresso. Declare @@index([alunoId, aulaId]) no schema.prisma.",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["Postgres: CREATE INDEX CONCURRENTLY"],
  "introduced_by_diff": true
}
```

```
### [MAJOR] MIG-001 — CREATE INDEX sem CONCURRENTLY em tabela de escrita contínua
**Onde:** exemplo-api/prisma/migrations/20261010120000_add_idx_progresso/migration.sql:1 · **Confiança:** media · **Esforço:** M
**Evidência:** CREATE INDEX "progresso_aluno_id_aula_id_idx" ON "progresso"("aluno_id", "aula_id");
**Problema:** bloqueia escrita em progresso durante a construção. Confirme o volume com a query no JSON.
**Correção:** índice por SQL manual com CONCURRENTLY e `prisma migrate resolve --applied`.
```

### Achado 2: rename como drop+add

```json
{
  "id": "MIG-002",
  "agent": "review-migrations",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "Expand/contract: rename",
  "location": { "repo": "exemplo-api", "file": "prisma/migrations/20261010130000_rename_nota/migration.sql", "lines": "1-4" },
  "evidence": "ALTER TABLE \"avaliacao\" DROP COLUMN \"nota_final\",\nADD COLUMN \"nota\" DECIMAL(5,2);",
  "problem": "O schema.prisma renomeou nota_final para nota e o Prisma gerou DROP + ADD. Todos os valores de nota_final são apagados na produção. A instância antiga do código também deixa de achar a coluna durante o deploy.",
  "fix": "Fase 1 (expand): ALTER TABLE avaliacao ADD COLUMN nota DECIMAL(5,2); com escrita dupla no código e backfill em lotes (UPDATE avaliacao SET nota = nota_final WHERE nota IS NULL AND id IN (SELECT id FROM avaliacao WHERE nota IS NULL LIMIT 5000);). Fase 2: leitura passa para nota. Fase 3 (contract, deploy posterior): ALTER TABLE avaliacao DROP COLUMN nota_final; Para rename direto aceito pelo time, edite o SQL para ALTER TABLE avaliacao RENAME COLUMN nota_final TO nota; e sincronize o código no mesmo deploy.",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["expand/contract"],
  "introduced_by_diff": true
}
```

### Caso que não se reporta

```sql
CREATE TABLE "certificado" ("id" TEXT PRIMARY KEY, "aluno_id" TEXT NOT NULL REFERENCES "aluno"("id"));
CREATE INDEX "certificado_aluno_id_idx" ON "certificado"("aluno_id");
```

Parece `CREATE INDEX` sem `CONCURRENTLY`. A tabela nasce na mesma migration, está vazia e nenhuma instância a usa ainda. O índice é construído em milissegundos e não bloqueia nada. O FK também é seguro: a tabela `aluno` só recebe lock de linha curto para validar a referência. Não reporte.
