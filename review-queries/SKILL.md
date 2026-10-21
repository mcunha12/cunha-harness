---
name: review-queries
description: Revisa performance de rotas e queries num diff - N+1, SELECT *, paginação sem limite ou com OFFSET grande, índices faltando (composto, parcial, covering, funcional), transações longas e locks, pool de conexões, escrita em loop, fan-out sequencial de chamadas independentes, payload e chatty APIs, cache (headers, ETag, Redis TTL, stampede), event loop bloqueado, trabalho pesado síncrono e O(n²). Acionar com "revisa a performance dessa query/rota", "tem N+1 aqui?", `/review-queries`, ou via master-review. NAO cobre SQL injection e authZ (review-seguranca), DDL e locks de migration (review-migrations), timeout e retry (review-resiliencia), re-render e bundle (review-front).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-queries (prefixo QRY)

## Missão

Achar no diff o código que vira problema de latência, throughput ou custo quando o volume real chega. O agente estima cardinalidade (linhas, chamadas, bytes) e impacto antes de reportar, e ignora micro-otimização. Cada achado diz quantas queries ou chamadas a rota faz, quantas linhas toca, e o que muda com a correção.

## Escopo

Cada item segue o formato sinal no código, impacto, correção.

### 1. Banco: padrões de acesso (QRY-DB)

- N+1: query dentro de loop, `map` ou `forEach` sobre resultado de outra query; relação carregada lazy (`await entity.relation`, TypeORM lazy, SQLAlchemy lazy default); `findUnique` por item. Impacto: 1 + N queries, com N igual ao tamanho da página ou da coleção. 200 matrículas com 3 relações dão 601 round trips de ~1-2 ms, ~1 s só de rede. Correção: `include`/`select` aninhado do Prisma, `relations`/`leftJoinAndSelect` do TypeORM, `selectinload`/`joinedload` do SQLAlchemy, `where: { id: { in: ids } }` mais agrupamento em `Map`, ou DataLoader (GraphQL).
- `SELECT *` ou entidade inteira quando o código usa 3 colunas: Prisma sem `select`, TypeORM `find()` sem `select`, `SELECT *`. Impacto: colunas largas (`text`, `jsonb`, `bytea`) trafegam e impedem index-only scan. Correção: `select` explícito.
- Sem `LIMIT`: `findMany()` sem `take`, `SELECT` em tabela que cresce, endpoint de listagem sem teto. Impacto: a resposta cresce com a tabela e derruba memória e latência. Correção: `take` com máximo no DTO, paginação.
- `OFFSET` grande: `skip: page * size` em tabela grande. Impacto: o banco lê e descarta `OFFSET` linhas, custo linear na página (offset 100.000 lê 100.000 linhas). Correção: keyset (`WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT n`), ou cursor do Prisma (`cursor` e `skip: 1`).
- `COUNT(*)` por requisição em tabela grande (Postgres faz scan). Correção: `hasNext` por `take + 1`, contagem aproximada, contador mantido, ou cache com TTL.
- Ausência de `ORDER BY` determinístico com paginação: páginas repetem ou perdem linhas. Correção: desempate por `id`.
- `DISTINCT` ou `GROUP BY` para esconder join que multiplica linhas. Correção: `EXISTS`/semi-join.
- `NOT IN (subquery)` com NULL (resultado vazio) ou lento: `NOT EXISTS`.
- `IN` com lista de milhares de valores. Correção: `= ANY($1::uuid[])` com array, ou tabela temporária e join.
- Subquery correlacionada executada por linha onde um join resolve.
- Agregação em memória sobre milhares de linhas que o banco agrega (`findMany` seguido de `reduce` para `SUM`): `groupBy`/`aggregate`/SQL.
- Leitura de linha seguida de escrita sem lock (check-then-act). Concorrência é do review-resiliencia. Se o custo é transação longa, é daqui.

### 2. Banco: índices (QRY-IDX)

- Coluna em `WHERE`, `JOIN ON` ou `ORDER BY` sem índice, em tabela que passa de ~10^4-10^5 linhas. FK sem índice: Postgres não cria índice automático na coluna referenciadora. Impacto: seq scan em cada consulta, e delete no pai varre a tabela filha. Correção: índice (a DDL em si é do review-migrations: `CREATE INDEX CONCURRENTLY`, aqui só o requisito).
- Índice composto na ordem errada: regra é igualdade primeiro, depois range, depois `ORDER BY`. `WHERE user_id = $1 AND created_at > $2 ORDER BY created_at` pede `(user_id, created_at)`. `(created_at, user_id)` não serve.
- Índice composto com prefixo que a query não usa: consulta só por `created_at` num índice `(user_id, created_at)` não o usa bem.
- Índice parcial para filtro fixo e seletivo (`WHERE deleted_at IS NULL`, `WHERE status = 'PENDING'`). Impacto: índice menor e mais rápido. Soft delete sem índice parcial infla todo índice.
- Covering (`INCLUDE`) para index-only scan em consulta quente com poucas colunas.
- Função sobre coluna indexada: `WHERE lower(email) = $1`, `WHERE date(created_at) = $1`, `WHERE created_at::date = ...`, `WHERE col + 1 = ...`. Impacto: o índice normal não é usado. Correção: índice funcional (`CREATE INDEX ON t (lower(email))`) ou reescrever como range (`created_at >= $1 AND created_at < $1 + interval '1 day'`).
- `LIKE '%x'` ou `LIKE '%x%'`: índice B-tree não ajuda. Correção: `pg_trgm` com GIN, ou full-text (`tsvector`). `LIKE 'x%'` usa B-tree só com `text_pattern_ops` ou collation `C`.
- `OR` entre colunas diferentes: pode virar seq scan. Correção: `UNION ALL` ou índices que permitam BitmapOr.
- Coerção implícita: comparar `varchar` com número, `uuid` com `text` (`id::text = $1`), `bigint` com `numeric`, parâmetro com tipo diferente da coluna (o Prisma e o `pg` mandam tipos por parâmetro). Impacto: cast na coluna e índice ignorado.
- `jsonb` filtrado por `->>` sem índice: GIN (`jsonb_path_ops`) para `@>`, índice funcional para `(col->>'k')`.
- Índice duplicado ou redundante (prefixo de outro) introduzido no diff: custo de escrita sem ganho.
- Índice em coluna de baixa seletividade (booleano) sozinho.
- Cada índice novo custa escrita. Em tabela com alta taxa de insert/update, índice a mais é custo, e o diff precisa de uma consulta que o justifique.
- Quando a severidade depende do plano, peça `EXPLAIN (ANALYZE, BUFFERS)` no `fix` ou no `problem` (e baixe a confiança para `media` até o plano existir). Aponte o que olhar: `Seq Scan` com `Rows Removed by Filter` alto, `Sort Method: external merge`, `Buffers: shared read` alto, estimativa de linhas muito distante da real (estatísticas velhas, `ANALYZE`).

### 3. Banco: escrita, transação e pool (QRY-WR)

- Escrita em loop: `for (...) await prisma.x.create(...)`, `update` por item. Impacto: N round trips e N commits. Correção: `createMany`, `INSERT ... VALUES (...), (...)`, `unnest($1::text[])`, `UPDATE ... FROM (VALUES ...)`, `upsert` em lote com `ON CONFLICT`. Em lotes de milhares, fatie em blocos (500-1000).
- `createMany` sem `skipDuplicates` onde há corrida, `upsert` em loop onde `ON CONFLICT` em lote resolve.
- Transação longa: `$transaction(async tx => { await fetchExternal(); ... })`. Chamada HTTP, LLM ou `sleep` dentro de transação segura conexão e locks. Impacto: o pool esgota e as linhas ficam travadas. Correção: fazer I/O externo fora da transação, transação só com SQL.
- `$transaction([...])` com dezenas de operações. Prisma interactive transaction tem timeout default de 5 s (`timeout`, `maxWait`).
- Lock contention: `SELECT ... FOR UPDATE` amplo, `UPDATE` em linha quente (contador global), ordem de lock inconsistente entre transações (deadlock). Correção: lock mínimo, `FOR UPDATE SKIP LOCKED` para filas, `UPDATE ... SET n = n + 1` atômico, ordenar as chaves.
- Nível de isolamento: `Serializable` exige retry em erro 40001. `READ COMMITTED` com check-then-act tem corrida.
- Pool: `new PrismaClient()` por request ou por módulo importado várias vezes (cada instância abre `connection_limit` conexões). `new Pool()` do `pg` dentro de handler. Correção: singleton por processo. Em serverless, pooler externo (PgBouncer, Prisma Accelerate) e `connection_limit` baixo. Some `pool_size × réplicas` e compare com `max_connections` do banco.
- Conexão que não volta ao pool: `client.connect()` sem `release()` em `finally`.
- Query dentro de `Promise.all` sobre 1000 itens: abre 1000 requisições ao pool de 10. Correção: limite de concorrência (`p-limit`) ou uma query em lote.
- Statement sem `statement_timeout` em endpoint que aceita filtro livre. O timeout é do review-resiliencia, o risco de consulta aberta é daqui.

### 4. HTTP e chamadas entre serviços (QRY-HTTP)

- Chamadas independentes em sequência: `const a = await getA(); const b = await getB();` onde `b` não depende de `a`. Impacto: latência soma (3 chamadas de 200 ms dão 600 ms em vez de 200 ms). Correção: `Promise.all([getA(), getB()])` (TS), `asyncio.gather` (Python). Para falha parcial aceitável, `Promise.allSettled`.
- `await` em loop sobre chamadas independentes (`for ... await http.get`). Correção: `Promise.all` com limite de concorrência.
- API chatty: o cliente faz N chamadas para montar uma tela. Correção: endpoint de composição na camada de agregação (se o repo tiver BFF/gateway pelo README/config) ou parâmetro `include`/`expand`.
- Fan-out sem limite: 1 request entrante gera N saintes (N cresce com dados). Impacto: amplificação de carga no serviço a jusante.
- Payload: resposta com a entidade inteira e dezenas de KB por item, lista sem paginação, base64 de arquivo em JSON, campos que o cliente não usa. Correção: DTO enxuto, `fields`, paginação, URL assinada para arquivo. Compressão (`gzip`, `br`) habilitada no servidor ou no proxy para JSON > ~1 KB.
- Cache HTTP: `Cache-Control`, `ETag`/`If-None-Match` (304), `Last-Modified`, `Vary`. Sinal: `Cache-Control: no-store` em recurso estático ou idempotente de leitura; cache público (`public`) em resposta por usuário (vazamento entre usuários, dono do vazamento é review-seguranca). Correção: `private, max-age=...` para dado por usuário, `stale-while-revalidate` onde tolerável.
- Cache de aplicação (Redis, memória): chave sem escopo (tenant, usuário, versão), TTL ausente (cresce sem limite), invalidação ausente ao escrever, stampede (1000 requisições recalculam a mesma chave expirada). Correção: TTL com jitter, single-flight (`Map` de promises por chave), lock curto (`SET NX PX`), `stale-while-revalidate` em app.
- Cache de erro: guardar `null` ou falha com o mesmo TTL do sucesso.
- Cache de dado que muda por escrita do próprio request sem invalidar: usuário vê dado antigo.
- Streaming: resposta grande montada em memória e enviada de uma vez. Correção: stream, SSE para progresso, paginação.
- Trabalho pesado síncrono na requisição (geração de PDF, ZIP, relatório, e-mail em massa, chamada de LLM longa, import de CSV): impacto timeout do proxy (30-60 s) e worker ocupado. Correção: enfileirar job, devolver 202 e `Location` para consultar o estado.
- Polling agressivo no cliente (a cada 1 s) sobre rota cara. Correção: backoff, SSE, WebSocket, ou cache curto no servidor. O lado do client é do review-front.

### 5. Runtime e algoritmo (QRY-RUN)

- Event loop bloqueado (Node): `JSON.parse`/`stringify` de payload de MB, `readFileSync`/`execSync` em handler, regex pesada, `crypto.pbkdf2Sync`/`bcrypt.hashSync`, `for` sobre 10^6 itens, `zlib.gzipSync`. Impacto: todas as requisições do processo esperam. Correção: versão assíncrona, `worker_threads`, fila, streaming.
- Tudo em memória: ler arquivo ou tabela inteira (`findMany()` sem limite, `readFile` de CSV grande, `Buffer.concat` de upload). Correção: stream, cursor de banco (`cursor`/`FETCH`/`for await`), lotes.
- O(n²): `arr.find`/`includes`/`indexOf`/`filter` dentro de `map`/`for` sobre listas grandes. Impacto: 10.000 × 10.000 = 10^8 comparações. Correção: `Map`/`Set` indexado uma vez (O(n)).
- `[...acc, item]` ou `Object.assign({}, acc, ...)` dentro de `reduce`: O(n²) por cópia. Correção: `push` no acumulador mutável local.
- `await` dentro de `reduce`/`for` serializando o que podia ser paralelo (QRY-HTTP).
- Recomputação em loop de valor invariante (regex compilada por iteração, `new Intl.DateTimeFormat` por linha, query igual repetida): hoisting.
- Serialização dupla (`JSON.parse(JSON.stringify(x))` para clonar) em caminho quente: `structuredClone`, ou evitar o clone.
- Regra: estime N. Se N é no máximo ~100 e o custo por item é micro, não reporte.

## Fora de escopo e dono

| Tema | Dono |
|---|---|
| SQL injection (`$queryRawUnsafe`, concatenação), authZ por tenant | review-seguranca |
| DDL, `CREATE INDEX CONCURRENTLY`, locks de migration, backfill | review-migrations |
| Timeout, retry, circuit breaker, idempotência | review-resiliencia |
| Re-render, bundle, fetch em effect, waterfalls no client | review-front |
| Shape de payload e breaking change | review-contratos |
| Métricas e traces de latência | review-observabilidade |
| Custo de tokens de LLM, caching de prompt | review-ia |
| Tipos do resultado de query | review-tipagem |
| Duplicação de query | review-dry |

Registre em `handoffs` com uma linha. Não desenvolva.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack conforme `review-rules.md`. Leia `references/generic.md` sempre. Leia o reference da tecnologia que existir neste diretório e bater com a stack: `prisma-postgres.md` (Prisma, TypeORM, knex, drizzle, pg), `nestjs.md`, `node.md`, `typescript.md`, `python.md`. Registre os lidos em `stack_references_loaded`.
3. Obtenha o diff. Se o orquestrador enviou um context packet, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`). `--path` restringe os arquivos.
4. Localize o schema: `schema.prisma`, entities do TypeORM, migrations recentes (`git ls-files | grep -i migration`), `models.py`. Leia os índices existentes das tabelas que o diff consulta. Sem o schema, a confiança de achado de índice é `media`.
5. Para cada rota ou função tocada, monte o caminho de execução: quantas queries, quantas chamadas externas, em que ordem, com que tamanho de coleção. Leia o caller para saber o N real (limite do DTO, tamanho da página, tabela pequena ou grande pelo domínio). Procure por padrões: `await` dentro de `for`/`map`, `findMany` sem `take`, `include` profundo, `$queryRaw`, `$transaction`, `new PrismaClient`, `Promise.all`, `.find(` dentro de loop, `readFileSync`.
6. Estime impacto com número: "N = 50 por página, 4 relações, 201 queries por request". Sem número, a confiança cai.
7. Classifique pela rubrica abaixo e pela global. Severidade depende de cardinalidade: o mesmo N+1 é MINOR com N ≤ 10 fixo e BLOCKER numa rota quente sem limite.
8. Emita no formato de `output-contract.md`: bloco JSON primeiro, markdown depois. `agent` vale `review-queries`, ids `QRY-001` em diante, no máximo ~15 achados.

Standalone: ao final, mostre o markdown. Não altere código.

## Rubrica de severidade do tema

**BLOCKER**
- N+1 ou `findMany` sem `take` em rota de alto tráfego sobre tabela que cresce com usuários ou matrículas.
- Chamada externa (HTTP, LLM) dentro de transação de banco numa rota quente, com risco de esgotar o pool.
- `new PrismaClient()` ou `new Pool()` por requisição.
- Event loop bloqueado por operação síncrona de centenas de ms em handler HTTP.
- Query sem índice usável em tabela com milhões de linhas, em rota síncrona de usuário (com plano ou schema confirmando).

**MAJOR**
- N+1 em rota de volume moderado (N de dezenas por página).
- `OFFSET` com paginação profunda em listagem que cresce.
- Chamadas independentes sequenciais em rota de tela principal (soma de 3+ latências).
- Escrita em loop de centenas de itens.
- Cache sem TTL ou sem escopo de usuário.
- `LIKE '%termo%'` ou função sobre coluna indexada em tabela grande.
- Trabalho pesado síncrono (PDF, relatório) dentro da requisição.

**MINOR**
- `SELECT *` com colunas largas em rota de baixo volume.
- `COUNT(*)` em tabela média, sem cache.
- Índice composto com ordem subótima que ainda funciona.
- `Promise.all` sem limite sobre lista pequena e limitada.
- Falta de compressão em resposta de dezenas de KB.

**NIT**
- Preferência entre `include` e `select` aninhado quando ambos geram a mesma query.
- Ordenação de colunas em `SELECT`.

## Heurísticas anti-falso-positivo

- Estime N antes de reportar. Loop sobre lista de tamanho fixo e pequeno (enum, 3 tipos de plano, 5 passos de wizard) não é N+1 de produção.
- Tabela pequena e estável (catálogo de dezenas de linhas, configuração) dispensa índice e paginação. Verifique o domínio e a migration que a cria.
- `include` do Prisma gera 1 query por relação (estratégia `query`) ou join (`relationLoadStrategy: 'join'`). Dois `include` rasos não são N+1.
- Job em lote noturno e script de migração toleram latência. `findMany` completo num job com stream ou lote controlado é aceito.
- Operações dentro de `$transaction` precisam ser sequenciais por desenho: `Promise.all` dentro de transação interativa do Prisma serializa na mesma conexão e não ganha nada.
- Cache em outro nível (CDN, proxy, interceptor global): leia a config antes de pedir cache.
- DataLoader ou batching já presente no resolver: não reporte N+1 em GraphQL sem checar.
- `await` sequencial com dependência real (a segunda chamada usa o resultado da primeira) está correto.
- Índice faltando em coluna que o diff não consulta com frequência nem em tabela grande: MINOR ou nada.
- Sem plano e sem volume conhecido, nenhum BLOCKER. Use `confidence: media` e peça o `EXPLAIN`.
- Micro-otimização (`for` versus `map`, `spread` em array de 20) não é achado.
- Repo com guideline explícita (por exemplo, `take` máximo definido em constante global) vence a preferência do agente.

## Ferramentas determinísticas opcionais

Rode só se instaladas e só em leitura. Nunca instale, nunca conecte a banco de produção. A saída é insumo.

- `EXPLAIN (ANALYZE, BUFFERS)`: só com `psql` disponível, `DATABASE_URL` apontando para banco local ou de teste descartável, e consulta sem efeito colateral. Verificação: `command -v psql`. `EXPLAIN ANALYZE` executa a consulta: nunca em `INSERT/UPDATE/DELETE` sem `BEGIN; ... ROLLBACK;`. Sem banco seguro, descreva o `EXPLAIN` a pedir no achado.
- `prisma validate`: `ls node_modules/.bin/prisma` e `npx --no-install prisma validate`. Verifica o schema e não consulta o banco.
- `eslint` com `@typescript-eslint/no-floating-promises` e `no-await-in-loop` (regra core): `npx --no-install eslint <arquivos do diff> --rule '{"no-await-in-loop":"warn"}'`, se o repo tem ESLint.
- `squawk` (lint de SQL de migration): é do review-migrations.
- Python: `ruff` com regras `PERF` (`command -v ruff`; `ruff check --select PERF <arquivos>`) e `nplusone`/`django-debug-toolbar` só em runtime, não rodar.
- `sqlfluff lint` para SQL cru (`command -v sqlfluff`), com os dialetos do repo.

## Exemplos

### Achado 1

```json
{
  "id": "QRY-001",
  "agent": "review-queries",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "QRY-DB N+1",
  "location": { "repo": "api-matriculas", "file": "src/turmas/turmas.service.ts", "lines": "34-46" },
  "evidence": "const turmas = await this.prisma.turma.findMany({ where: { cursoId } });\nreturn Promise.all(turmas.map(async (t) => ({\n  ...t,\n  totalAlunos: await this.prisma.matricula.count({ where: { turmaId: t.id } }),\n})));",
  "problem": "Cada turma dispara um COUNT. O curso tem até 300 turmas (limite do cadastro em turma.dto.ts), então a rota GET /cursos/:id/turmas executa 301 queries e abre 300 requisições simultâneas ao pool de 10 conexões. Sob 20 requisições concorrentes, o pool satura e as demais rotas do serviço esperam. Sem índice em matricula.turma_id, cada COUNT faz seq scan.",
  "fix": "const turmas = await this.prisma.turma.findMany({ where: { cursoId }, select: { id: true, nome: true } });\nconst contagens = await this.prisma.matricula.groupBy({ by: ['turmaId'], where: { turmaId: { in: turmas.map((t) => t.id) } }, _count: { _all: true } });\nconst porTurma = new Map(contagens.map((c) => [c.turmaId, c._count._all]));\nreturn turmas.map((t) => ({ ...t, totalAlunos: porTurma.get(t.id) ?? 0 }));\n// e garanta @@index([turmaId]) em Matricula (DDL com CREATE INDEX CONCURRENTLY, ver review-migrations)",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["N+1"],
  "introduced_by_diff": true
}
```

### Achado 2

```json
{
  "id": "QRY-002",
  "agent": "review-queries",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "QRY-HTTP fan-out sequencial",
  "location": { "repo": "bff-aluno", "file": "src/home/home.service.ts", "lines": "21-27" },
  "evidence": "const perfil = await this.alunos.getPerfil(userId);\nconst cursos = await this.matriculas.getCursos(userId);\nconst streak = await this.engajamento.getStreak(userId);",
  "problem": "As três chamadas só dependem de userId. A latência da home soma as três (p95 observado nos clients: ~180 ms, ~250 ms, ~120 ms, total ~550 ms) em vez de assumir a maior (~250 ms). A home é a primeira tela após o login.",
  "fix": "const [perfil, cursos, streak] = await Promise.all([\n  this.alunos.getPerfil(userId),\n  this.matriculas.getCursos(userId),\n  this.engajamento.getStreak(userId),\n]);\n// se streak for opcional na tela, use Promise.allSettled e degrade para null",
  "auto_fixable": true,
  "effort": "S",
  "refs": [],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

O diff adiciona um `for (const tipo of TIPOS_AVALIACAO) { await this.repo.count({ tipo }) }` em `resumo.service.ts`. Parece query em loop. Não se reporta: `TIPOS_AVALIACAO` é um array constante de 3 elementos, a rota é de painel interno com poucas chamadas por hora, e a tabela tem índice em `tipo`. O custo é 3 queries curtas. A troca por `groupBy` não muda nada mensurável.
