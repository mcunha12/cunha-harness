# Resiliência — Python

Carregue quando há `pyproject.toml` ou `requirements*.txt`. Regras específicas de Python. O restante vem de `generic.md`.

## Exceções

- `except:` e `except BaseException:` capturam `KeyboardInterrupt`, `SystemExit` e `asyncio.CancelledError`. Impacto: o processo não encerra e a task cancelada continua. Correção: `except Exception`, ou re-raise de `CancelledError`.
- `except Exception: pass` e `contextlib.suppress(Exception)`: erro engolido. Aceite `suppress(FileNotFoundError)` com tipo específico.
- `raise NewError(...)` dentro de `except` sem `from e` perde a cadeia explícita. Use `raise NewError(...) from e`. Use `from None` só para esconder detalhe interno de propósito.
- `logger.error(str(e))` perde o traceback. Use `logger.exception(...)` dentro do `except` ou `exc_info=True`.
- `return` dentro de `finally` suprime a exceção em voo.
- `assert` para validar entrada externa some com `python -O`. Lance exceção explícita.
- `ExceptionGroup` e `except*` (3.11+) em `asyncio.TaskGroup`: um `except Exception` comum não captura o grupo da forma esperada.

## asyncio

- Coroutine chamada sem `await` gera `RuntimeWarning: coroutine was never awaited` e o trabalho não roda. `pyright` (`reportUnusedCoroutine`) e `ruff` (`RUF006`, `ASYNC`) apontam.
- `asyncio.create_task(...)` sem guardar a referência: o loop mantém só referência fraca, a task pode ser coletada no meio, e a exceção some (aparece só no GC como "Task exception was never retrieved"). Correção: guarde em um `set` com `add_done_callback(set.discard)`, ou use `TaskGroup`.
- `asyncio.gather(*tasks)` sem `return_exceptions=True`: a primeira exceção sobe e as demais tasks seguem rodando sem dono. Prefira `asyncio.TaskGroup` (3.11+), que cancela as irmãs, ou `return_exceptions=True` com checagem do resultado.
- `asyncio.wait_for(coro, timeout)` cancela a coroutine ao estourar. Sem limite explícito, `await` aguarda para sempre. Use `asyncio.timeout(...)` (3.11+) como context manager.
- `try/except` que captura `asyncio.CancelledError` e não relança quebra cancelamento e shutdown. Relance sempre.
- Chamada bloqueante dentro de `async def` (`requests.get`, `time.sleep`, `open().read()` grande, driver síncrono): bloqueia o event loop inteiro. Correção: `httpx.AsyncClient`, `asyncio.to_thread`, `await asyncio.sleep`.
- Semáforo ausente em `gather` de milhares de chamadas: estouro de conexão e rate limit. `asyncio.Semaphore(n)`.

## HTTP

- `requests.get(url)` sem `timeout=`: espera infinita. `requests` não tem timeout default. Correção: `timeout=(3.05, 10)` (connect, read).
- `requests.Session` com `HTTPAdapter(max_retries=Retry(...))`: configure `allowed_methods` (default exclui POST), `status_forcelist`, `backoff_factor` e `respect_retry_after_header`. `Retry(total=5)` sem `allowed_methods` explícito repete só métodos idempotentes; ampliar para POST sem idempotency key duplica efeito.
- `httpx`: timeout default de 5 s. `httpx.Timeout(10.0, connect=3.0)`. `AsyncClient` criado por request em vez de reutilizado: perde pool e vaza sockets se não fechar. Use `async with` ou ciclo de vida da app (lifespan do FastAPI).
- `response.raise_for_status()` ausente: 4xx/5xx passam como sucesso e o `.json()` falha adiante com erro confuso.
- `tenacity`: `@retry` sem `stop=`, sem `wait=wait_random_exponential(...)` e sem `retry=retry_if_exception_type(...)` repete tudo para sempre. Exija os três. `reraise=True` para não mascarar com `RetryError`.
- `backoff` e `urllib3.Retry` com a mesma regra. Retry duplicado entre `Retry` do adapter e `tenacity`: amplificação.

## Filas e jobs

- Celery: `acks_late=True` com tarefa não idempotente duplica efeito em crash do worker; sem `acks_late`, perde-se a tarefa em crash. Escolha de forma consciente e exija idempotência no primeiro caso. `autoretry_for` com `retry_backoff=True`, `retry_jitter=True`, `max_retries`. `task_time_limit` e `soft_time_limit` ausentes deixam tarefa pendurada. `visibility_timeout` (Redis broker) menor que a tarefa mais longa reentrega a mesma tarefa em paralelo.
- `celery` `retry()` sem `max_retries` e `countdown`: loop.
- RQ, Dramatiq, arq: `max_retries`, `retry_delay` ou `min_backoff`, e timeout por job.
- Consumer de RabbitMQ com `pika`/`aio-pika`: `ack` depois do efeito, `reject(requeue=False)` com DLX para erro permanente, `prefetch_count`.
- Cron/`APScheduler` em várias réplicas: lock distribuído; `misfire_grace_time` e `coalesce`.

## Banco (SQLAlchemy, Django)

- `Session` sem fechar: `with Session(engine) as s` ou `sessionmaker` com escopo por request. Sessão compartilhada entre threads é incorreta.
- `session.commit()` sem `try/except` com `rollback()`: sessão fica em estado inválido (`PendingRollbackError`) após falha. O context manager resolve.
- `pool_size`, `max_overflow`, `pool_timeout`, `pool_pre_ping=True`, `pool_recycle`: conexão morta no pool gera erro na primeira query após ociosidade.
- `connect_args={"connect_timeout": 5}` e `statement_timeout` ausentes.
- Check-then-act: `if not exists(): insert()`. Use constraint unique e `INSERT ... ON CONFLICT`, ou `select(...).with_for_update()`.
- Django: `transaction.atomic()` com chamada externa dentro; `transaction.on_commit(...)` para efeitos externos após commit; `select_for_update()`; `ATOMIC_REQUESTS`; `get_or_create` e `update_or_create` dentro de `atomic` (tratam `IntegrityError` em corrida).

## Ciclo de vida

- FastAPI: `lifespan` (ou `on_event` legado) abre e fecha pools e clientes. Sem fechamento, shutdown deixa conexões penduradas. Handler `@app.exception_handler` para erro de domínio; sem ele, `500` com traceback em debug.
- `signal.signal(SIGTERM, ...)` em worker síncrono; `loop.add_signal_handler` em asyncio. Gunicorn/uvicorn: `graceful_timeout`/`--timeout-graceful-shutdown`.
- Threads daemon fazendo escrita: perdem trabalho no shutdown.
- `multiprocessing`/`concurrent.futures`: exceção no worker só aparece em `future.result()`. Chame-o ou use `as_completed` e trate.
- Config: `pydantic-settings` valida no boot. `os.environ["X"]` lança `KeyError` tardio. `os.getenv("X")` sem validação devolve `None`.

## Ferramentas

- `ruff check --select BLE,TRY,S110,S112,ASYNC,RUF006,B012,PLW0120`
- `pyright --strict` ou `mypy --strict` apontam coroutine não awaited e `Optional` não tratado.
- `bandit -r <path>` para `try/except/pass` (B110) e `requests` sem timeout (B113).

## Correção típica

```python
async with asyncio.timeout(10):
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        r = await client.get(url)
        r.raise_for_status()
```

```python
@retry(
    stop=stop_after_attempt(4) | stop_after_delay(20),
    wait=wait_random_exponential(multiplier=0.5, max=8),
    retry=retry_if_exception_type((httpx.TransportError, TransientHTTPError)),
    reraise=True,
)
async def fetch(): ...
```

```python
tasks: set[asyncio.Task] = set()
t = asyncio.create_task(job())
tasks.add(t)
t.add_done_callback(tasks.discard)
```
