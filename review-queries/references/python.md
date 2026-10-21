# Queries e rotas em Python

## SQLAlchemy

- N+1 por lazy loading (default em `relationship`): iterar `for a in alunos: a.matriculas`. Correção: `selectinload(Aluno.matriculas)` (1 query adicional com `IN`, boa para coleções), `joinedload` (1 query com join, boa para muitos-para-um), `subqueryload` raro. Defina `lazy="raise"` em desenvolvimento para pegar.
- `joinedload` de coleção com `LIMIT`: o limite age sobre as linhas multiplicadas. Use `selectinload` com paginação.
- `session.query(Model).all()` sem filtro e sem limite. `yield_per(n)`/`stream_results` para varreduras.
- `session.add` em loop com `commit` por item: um commit por linha. Correção: `session.add_all`, `session.execute(insert(Model), [dicts])` (bulk, 2.0), `bulk_insert_mappings`, commit uma vez.
- `session.execute(select(Model))` traz entidades completas. `select(Model.id, Model.nome)` para colunas.
- `len(query.all())` para contar: `select(func.count())`.
- `Session` por requisição fechada em `finally` ou via dependência (`Depends(get_session)` com `yield`). Sessão global compartilhada entre threads é bug e vazamento de conexão.
- Pool: `create_engine(pool_size, max_overflow, pool_pre_ping)`. `NullPool` em ambiente com pooler externo.
- Async (`AsyncSession`): `await` em loop sequencial; `asyncio.gather` para independentes (cada tarefa com sua sessão, sessão não é segura para concorrência).
- Lazy load em contexto async lança `MissingGreenlet`: carregue com `selectinload`.

## Django ORM

- N+1: `select_related('fk')` (join, FK/OneToOne) e `prefetch_related('m2m')` (query extra com `IN`). Template ou serializer que acessa `obj.relacao.campo` em loop.
- `.count()` vs `len(qs)`: `len` carrega tudo. `.exists()` em vez de `if qs`.
- `.values()`/`.values_list()`/`.only()`/`.defer()` para colunas.
- `bulk_create`, `bulk_update` (com `batch_size`), `update()` por queryset, `F()` para incremento atômico.
- `iterator(chunk_size=...)` para varredura grande.
- `Model.objects.filter(...)[N:M]` é offset. Keyset manual para volume.
- `atomic()` envolvendo chamada HTTP: segura conexão e locks.
- `select_for_update()` fora de `atomic()` não trava.
- `QuerySet` avaliado no template várias vezes sem cache: atribua a lista.

## FastAPI e async

- `def` (sync) em rota roda no threadpool. `async def` com chamada bloqueante dentro (`requests.get`, `time.sleep`, driver sync, `open().read()` grande) bloqueia o event loop inteiro. Correção: `httpx.AsyncClient`, `asyncio.sleep`, `asyncio.to_thread`, driver async (`asyncpg`).
- `asyncio.gather(a(), b())` para chamadas independentes. `gather` com limite: `asyncio.Semaphore`.
- `httpx.AsyncClient()` criado por requisição: perde pool e keep-alive. Cliente único no lifespan.
- `BackgroundTasks` para trabalho curto pós-resposta. Trabalho pesado ou que precisa de retry: fila (Celery, RQ, arq).
- Resposta grande: `StreamingResponse`.
- Cálculo CPU-bound em `async def`: `ProcessPoolExecutor` ou fila.

## Pandas e processamento em memória

- `df.iterrows()`/`apply(axis=1)` em DataFrame grande: operações vetorizadas.
- `pd.read_sql` de tabela inteira: `chunksize` ou filtro no SQL.
- `list` em `in` dentro de loop (`x in lista_grande`): `set`.
- Concatenação `df = pd.concat([df, row])` em loop: acumule em lista e concatene uma vez.

## Ferramentas

- `ruff check --select PERF` (regras de performance como `PERF401` list comprehension, `PERF203` try/except em loop) se `ruff` está instalado.
- `django-debug-toolbar` e `nplusone` são ferramentas de runtime. Não rode.
