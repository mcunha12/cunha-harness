# Observabilidade — Python

Carregue quando há `pyproject.toml` ou `requirements*.txt`. Regras específicas de Python. O restante vem de `generic.md`.

## Logging

- `print()` em código de serviço: sem nível, sem contexto, sem formato. Use `logging` ou `structlog`.
- `logger.error(f"falhou {user.email}")`: PII por interpolação e f-string avaliada mesmo com o nível desligado. Use argumentos do logging (`logger.info("enrollment.created", extra={...})`) ou `structlog` com kwargs.
- `logger.error(str(e))` ou `logger.error(e)` dentro de `except` perde o traceback. Use `logger.exception("msg")` ou `exc_info=True`. `logger.exception` fora de `except` registra `NoneType: None`.
- `logging.basicConfig` chamado em biblioteca ou em módulo importado: configuração duplicada e handlers repetidos (linhas de log em dobro). Configure uma vez no entrypoint.
- `logger = logging.getLogger(__name__)` por módulo. `logging.getLogger()` raiz usada diretamente perde a hierarquia.
- `extra={"name": ...}` ou `extra={"message": ...}` lança `KeyError` (chaves reservadas do `LogRecord`: `name`, `message`, `args`, `msg`, `levelname`, `module`, `exc_info`...). Use outro nome.
- Formato JSON: `structlog` com `JSONRenderer`, `python-json-logger`, ou `logging.config.dictConfig` com formatter JSON. `structlog.contextvars.bind_contextvars(request_id=...)` no middleware.
- `logging.config.dictConfig` com `disable_existing_loggers: True` (default) silencia loggers de bibliotecas. Defina `False`.
- Nível por config. `logging.DEBUG` fixo em produção: custo e PII.
- `uvicorn`/`gunicorn` access log com query string (tokens): customize o formato ou desligue o access log duplicado.
- Handler de `QueueHandler` + `QueueListener` para log assíncrono em hot path; confira `listener.stop()` no shutdown.

## Contexto e correlação

- `contextvars.ContextVar` para `request_id`/`trace_id`. Middleware ASGI define; o formatter lê. `threading.local` não funciona com asyncio.
- `asyncio.create_task` copia o contexto no momento da criação (o valor da ContextVar acompanha). `run_in_executor` e `loop.call_soon_threadsafe` não copiam em todos os casos: use `contextvars.copy_context().run` ou `asyncio.to_thread` (que copia).
- Celery: propague `request_id` e `traceparent` nos headers da tarefa (`before_task_publish`/`task_prerun`) e restaure no worker. Sem isso, o trace e o id se perdem na fila.
- FastAPI/Starlette: middleware que lê `traceparent`, ou `opentelemetry-instrumentation-fastapi`.

## OpenTelemetry (Python)

- Auto-instrumentação: `opentelemetry-instrument python app.py` ou `FastAPIInstrumentor.instrument_app(app)`, `RequestsInstrumentor().instrument()`, `HTTPXClientInstrumentor`, `SQLAlchemyInstrumentor`, `CeleryInstrumentor`, `Psycopg2Instrumentor`. A instrumentação chama `.instrument()` antes de criar clientes/engines em alguns casos. Confira a ordem.
- Resource com `service.name`, `service.version`, `deployment.environment` (`OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`).
- Span manual:

```python
with tracer.start_as_current_span("enrollments.create") as span:
    span.set_attribute("app.course_id", course_id)
    try:
        ...
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR))
        raise
```

- `start_span` sem `use_span`/context manager não torna o span ativo e deixa de fechar. Use `start_as_current_span`.
- `BatchSpanProcessor` em produção. `provider.shutdown()` no encerramento (lifespan do FastAPI), ou o último lote se perde.
- Fork de processo (gunicorn `--preload`, `multiprocessing`): o SDK precisa inicializar após o fork (`post_fork` hook). Antes, os threads de exportação não existem no filho e nenhum span sai.
- `SQLAlchemyInstrumentor` com `enable_commenter` ou `db.statement` com literais: PII em atributo. Use consultas parametrizadas e `sanitize_query`.
- Métricas: `meter.create_histogram("request.duration", unit="s")`. `prometheus-client`: `Histogram(..., labelnames=[...])`; label com id de usuário ou URL crua cria séries ilimitadas. Em multiprocess (gunicorn), `PROMETHEUS_MULTIPROC_DIR` e `MultiProcessCollector`, senão cada worker expõe um valor diferente.

## Sentry (Python)

- `sentry_sdk.init(dsn=..., environment=..., release=..., send_default_pii=False, traces_sample_rate=...)`. Integrações automáticas para FastAPI, Django, Flask, Celery, SQLAlchemy.
- `sentry_sdk.capture_exception(e)` em `except` que relança duplica com a integração. Use `sentry_sdk.set_tag`, `set_user({"id": ...})`, `set_context` em `push_scope`/`new_scope`.
- Eventos de log: a integração de `logging` envia `ERROR` como evento. `logger.error` para caso esperado gera issue. Ajuste `event_level` ou `ignore_logger`.
- `before_send` para filtrar `HTTPException` 4xx e `asyncio.CancelledError` e para remover PII.
- Celery: `CeleryIntegration` captura falha de tarefa; retries geram eventos repetidos. Configure `ignore_errors`/`propagate_traces`.

## Django, FastAPI, Celery

- Django: `LOGGING` com `django.request` e `django.db.backends` (este em DEBUG loga SQL com parâmetros). `DEBUG=True` em produção expõe tudo (dono do vazamento: review-seguranca). `django-structlog` para correlação.
- FastAPI: `lifespan` inicia e encerra OTel/Sentry; `exception_handler` registra uma vez; dependência que injeta logger com `request_id`. Rota `/health` e `/metrics` fora do tracing e do log de acesso.
- Celery: `task_prerun`/`task_postrun`/`task_failure` com log estruturado (`task_id`, `name`, `retries`, `duration`); `task_track_started`; métricas por fila e por tarefa (`celery-exporter`/`flower`); alerta de profundidade e de idade da fila.

## Ferramentas

- `ruff check --select T20,G,LOG,TRY400,TRY401,BLE <arquivos>`: `print`, formatação de logging (`G`), `logging.exception` (`TRY400`/`TRY401`).
- `bandit -r <path>` para segredo e `assert` em produção.
- `pyright`/`mypy` não cobrem observabilidade; use o grep de triagem do SKILL.md.

## Sinais de alerta rápidos

- `except Exception as e: print(e)`.
- `logger.info(request.json())` ou `logger.debug(payload)` com body de entrada.
- `logging.basicConfig(level=logging.DEBUG)` no módulo.
- Tarefa Celery sem log de falha final e sem métrica de erro.
- Métrica Prometheus com label `user_id`/`path` cru.
