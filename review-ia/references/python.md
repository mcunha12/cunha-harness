# IA — Python

Carregue quando há `pyproject.toml` ou `requirements*.txt`. Regras específicas de Python. O restante vem de `generic.md` e `llm-sdks.md`.

## Validação da saída

- `json.loads(text)` sobre saída do modelo lança `JSONDecodeError`. Envolva com `try/except` e ramo de reparo.
- `re.search(r"\{.*\}", text, re.S)` para extrair JSON: frágil. Use saída estruturada do provedor e valide com Pydantic.

```python
class Question(BaseModel):
    stem: str = Field(min_length=10, max_length=2000)
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)

class Quiz(BaseModel):
    questions: list[Question] = Field(min_length=1, max_length=20)

try:
    quiz = Quiz.model_validate_json(text)
except ValidationError as e:
    quiz = await repair(text, e.errors())  # no máximo 1 a 2 tentativas
```

- `instructor`, `client.beta.chat.completions.parse(response_format=Model)` e `messages.parse` combinam schema e validação. Verifique `refusal`/`stop_reason` mesmo assim.
- `model_validate` em dict e `model_validate_json` em string: `strict=True` quando o tipo importa (evita coerção de `"3"` em `3`).
- `Literal[...]`/`Enum` para classificações: o modelo devolve um valor da lista fechada.
- `typing.cast(Quiz, data)` e `Any` na fronteira: sem validação.

## Execução de código e desserialização

- `eval`, `exec`, `compile`, `os.system`, `subprocess.run(..., shell=True)`, `pickle.loads`, `yaml.load` (sem `SafeLoader`), `marshal`, `__import__` sobre texto do modelo: BLOCKER.
- Sandbox de código gerado: processo separado, container sem rede, usuário sem privilégio, FS somente leitura mais tmp efêmero, limites (`resource.setrlimit`, cgroups), timeout. Nunca no processo da aplicação.
- `ast.literal_eval` é válido para literais simples e não executa código arbitrário; continua exigindo validação de tamanho e de valores.
- SQL: query parametrizada; o modelo escolhe parâmetros ou uma operação nomeada, nunca o texto da query. Text-to-SQL exige usuário de banco read-only, schema restrito, `statement_timeout`, limite de linhas e allowlist de tabelas, com parse da query (`sqlglot`) antes de executar.
- `torch.load` e `pickle.load` em arquivo de fonte externa executam código: use `weights_only=True`/`safetensors`. `from_pretrained(..., trust_remote_code=True)` executa código do repositório do modelo: BLOCKER em fonte não confiável; pine `revision` por hash.

## Tools e agentes

- Registro de tools como `dict[str, Callable]` fechado; `name` do modelo procurado com `.get` e erro explícito para ausente.
- Args validados por Pydantic (`TypeAdapter`/modelo por tool). `**kwargs` direto dos args do modelo para função: parâmetros extras e injeção de argumentos.
- Identidade (`user_id`, `tenant_id`) injetada pelo servidor (closure, `functools.partial`, contexto), ausente do schema exposto.
- Loop de agente com `for step in range(MAX_STEPS)` em vez de `while True`. Orçamento acumulado de tokens e tempo (`time.monotonic`). Parada em chamada repetida idêntica.
- LangChain/LangGraph: `recursion_limit` no config; tools como `PythonREPLTool`, `ShellTool`, `RequestsGetTool` e `SQLDatabaseToolkit` com usuário privilegiado são de alto risco. Restrinja ou envolva com confirmação.
- Tool de arquivo: `Path(base).joinpath(arg).resolve()` e checagem `is_relative_to(base)`. Symlinks e `..`.

## Chamadas, concorrência e cancelamento

- Cliente síncrono (`OpenAI()`) dentro de `async def` bloqueia o event loop. Use `AsyncOpenAI`/`AsyncAnthropic` ou `asyncio.to_thread`.
- `timeout=` por chamada ou no cliente (`httpx.Timeout`). O default dos SDKs é alto (10 min).
- Cancelamento: `asyncio.CancelledError` propaga para a chamada do SDK assíncrono e interrompe a requisição. Não capture sem relançar. No FastAPI com `StreamingResponse`, verifique `await request.is_disconnected()` no laço do gerador.
- `asyncio.Semaphore(n)` limita concorrência contra o provedor. `asyncio.gather` de milhares de chamadas dispara 429 em cascata.
- Retry: `tenacity` com `wait_random_exponential`, `stop_after_attempt`, `retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError))` e `reraise=True`. O SDK já tem `max_retries`: um só nível.
- Streaming: `async with client.messages.stream(...) as stream:` fecha o stream no `finally` do context manager. Gerador que para no meio sem fechar mantém a conexão.
- Resultado do `to_thread`/executor não propaga cancelamento para a thread: o trabalho continua.

## RAG e dados

- Vector stores (Chroma, pgvector, Qdrant, Pinecone, FAISS): `filter`/`where` por metadados na consulta (`collection.query(query_embeddings=..., where={"course_id": {"$in": ids}})`, `retriever.as_retriever(search_kwargs={"filter": ...})`). O filtro vem da sessão. Sem filtro, o índice inteiro responde.
- FAISS e índices locais sem metadado de permissão: filtragem pós-consulta só com `k` grande e checagem completa, ou um índice por tenant.
- pgvector: `WHERE tenant_id = $1 ORDER BY embedding <=> $2 LIMIT k` com índice HNSW/IVFFlat; o filtro seletivo pode reduzir o recall (`hnsw.iterative_scan`, ou índice parcial por tenant). Documente a escolha.
- Documentos de PDF/HTML na ingestão (`pypdf`, `unstructured`, `BeautifulSoup`): remova texto oculto e comentários; registre `source_id`.
- Anonimização com `presidio` ou regras próprias antes da chamada; regex de CPF e e-mail sozinhas deixam nome passar.
- DataFrame inteiro ou ORM model serializado no prompt (`df.to_json()`, `model.dict()`): minimize colunas.
- Log do prompt (`logger.debug(prompt)`) com dado de aluno: dono da regra de log é o review-observabilidade; aqui reporte o envio de dado desnecessário.

## Config e segredos

- `os.environ["OPENAI_API_KEY"]` no servidor; `pydantic-settings` com `SecretStr` evita impressão acidental em `repr` e log.
- Chave em notebook, `.env` versionado, exemplo de documentação: segredo (dono: review-seguranca; handoff).
- Model ID em `Settings`, pinado, por ambiente.

## Notebooks e scripts de avaliação

- Notebook com dado real de aluno ou de paciente commitado com saídas (`.ipynb` com células executadas): PII no repositório. Limpe as saídas (`nbstripout`).
- Script de eval fora do app com chamadas em lote: limite de custo (`--max-cases`), cache de respostas, semente e temperatura registradas.
- Dataset de eval versionado com hash e anonimizado.

## Ferramentas

- `bandit -r <path>`: `B102` (exec), `B307` (eval), `B301`/`B614` (pickle/torch.load), `B602` (shell=True).
- `ruff check --select S,ASYNC,BLE,PGH <arquivos>`.
- `pyright --strict`/`mypy --strict` para `Any` na fronteira.
- `pip-audit` para dependências de IA.
- `gitleaks detect --no-git --source <path>` para chaves (`sk-`, `sk-ant-`, `AIza`).

## Sinais de alerta rápidos

- `eval(response.choices[0].message.content)`.
- `json.loads(re.search(r"\{.*\}", text, re.S).group())`.
- `tools[call.function.name](**json.loads(call.function.arguments))`.
- `while True:` com `client.messages.create` dentro.
- `OpenAI().chat.completions.create` dentro de `async def`.
- `vectorstore.similarity_search(q, k=8)` sem `filter`.
- `from_pretrained(name, trust_remote_code=True)`.
