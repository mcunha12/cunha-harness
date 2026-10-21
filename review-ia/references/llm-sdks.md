# IA — SDKs de LLM (openai, @anthropic-ai/sdk, @google/genai, MCP)

Carregue quando `openai`, `@anthropic-ai/sdk`, `@google/genai`, `langchain*`, `ai` ou o MCP SDK está nas deps. Confirme a versão instalada no lockfile antes de afirmar que um parâmetro existe ou mudou: as APIs mudam entre versões.

## Checklist transversal por chamada

- Cliente instanciado uma vez (singleton), com `apiKey` do ambiente do servidor, `timeout`, `maxRetries` explícitos.
- `model` vindo de config, com ID pinado.
- `max_tokens`/`maxOutputTokens` definido.
- Saída estruturada nativa e validação do lado do app.
- Motivo de parada checado (truncamento, refusal, bloqueio).
- `signal` de cancelamento ligado ao request do usuário.
- Conteúdo do usuário em `user`, instruções em `system`.
- Tools com schema estrito, validação dos args e autorização.

## openai

- **Cliente:** `new OpenAI({ apiKey, timeout, maxRetries })`. Default de `timeout` é 10 minutos e `maxRetries` é 2. Para rota de usuário, `timeout` de 20 a 60 s. `dangerouslyAllowBrowser: true` expõe a chave: BLOCKER em app de produção.
- **Saída estruturada:** `response_format: { type: 'json_schema', json_schema: { name, schema, strict: true } }`, ou helper `zodResponseFormat(Schema, 'name')` com `client.beta.chat.completions.parse(...)` / `client.responses.parse(...)`. Com `strict: true`, o schema exige `additionalProperties: false` e todos os campos em `required`. O `parse` devolve `message.parsed` (pode ser `null`) e `message.refusal`: trate os dois. `response_format: { type: 'json_object' }` só garante JSON sintático, sem schema.
- **Motivo de parada:** `choice.finish_reason`: `stop`, `length` (truncado), `tool_calls`, `content_filter`. Responses API: `response.status` (`incomplete` com `incomplete_details.reason`), `output` itens.
- **Refusal:** `message.refusal` (string) quando o modelo recusa em modo estruturado. `message.content` vem `null`.
- **Tools:** `tools: [{ type: 'function', function: { name, description, parameters, strict: true } }]`. Os `arguments` vêm como string JSON: `JSON.parse` em `try/catch`, validação com schema, e allowlist por `name`. `parallel_tool_calls` desabilitado quando a ordem importa. `tool_choice` explícito quando a tool é obrigatória.
- **Streaming:** `stream: true` e `stream_options: { include_usage: true }` para o uso de tokens. Acumule deltas de `tool_calls` por `index`. Interrompa com `AbortController` ou `stream.controller.abort()`.
- **Parâmetros por modelo:** modelos de raciocínio (série o) rejeitam ou ignoram `temperature`/`top_p` e usam `max_completion_tokens` no lugar de `max_tokens` e `reasoning_effort`. Confirme a combinação para o modelo pinado.
- **Moderation e embeddings:** `moderations.create` para entrada de alto risco; `embeddings.create` em lote com limite de tokens por request; mesmo modelo de embedding na ingestão e na consulta.
- **Prompt caching:** automático acima de 1024 tokens com prefixo idêntico; `usage.prompt_tokens_details.cached_tokens` mede o acerto. Variável no início zera o cache.
- **Batch:** `batches.create` para trabalho offline (desconto e janela de 24 h).
- **Erros:** `OpenAI.APIError` com `status`, `code`, `request_id`; `RateLimitError`, `APIConnectionTimeoutError`, `APIUserAbortError`. Mapeie por tipo.

## @anthropic-ai/sdk

- **Cliente:** `new Anthropic({ apiKey, timeout, maxRetries })`. `maxRetries` default 2. O SDK exige `max_tokens` em `messages.create`. Para requests longos sem streaming, o SDK pode recusar valores altos de `max_tokens`: use `stream`.
- **System:** parâmetro `system` separado (string ou lista de blocos). Instruções e regras vão ali. Conteúdo do usuário em `messages` com `role: 'user'`.
- **Motivo de parada:** `message.stop_reason`: `end_turn`, `max_tokens` (truncado), `stop_sequence`, `tool_use`, `pause_turn`, `refusal`. Trate `max_tokens` e `refusal` como ramos próprios.
- **Tools:** `tools: [{ name, description, input_schema }]`, resposta com blocos `type: 'tool_use'` (`id`, `name`, `input`). `input` é objeto, mas não garantido pelo schema: valide. Devolva `tool_result` com `tool_use_id`. `tool_choice: { type: 'tool', name }` força a tool e vira "saída estruturada" via `input_schema`.
- **Prompt caching:** `cache_control: { type: 'ephemeral' }` no último bloco do prefixo estável (system, tools, documento). Respeite o mínimo de tokens por modelo e o limite de breakpoints. `usage.cache_read_input_tokens` e `cache_creation_input_tokens` medem. Conteúdo variável antes do breakpoint invalida o cache.
- **Streaming:** `client.messages.stream(...)` com eventos; `await stream.finalMessage()` devolve a mensagem completa com `usage`. Cancele com `stream.abort()` ou `signal`.
- **Pensamento estendido:** `thinking: { type: 'enabled', budget_tokens }` exige `budget_tokens < max_tokens` e restringe `temperature`. Blocos de `thinking` devolvidos junto com `tool_use` na continuação. Não exiba o raciocínio bruto ao usuário sem decisão de produto.
- **Citações e documentos:** blocos `document` com `citations: { enabled: true }` para grounding com referência verificável (útil em domínio clínico).
- **Batch:** `messages.batches.create` para offline.
- **Erros:** `Anthropic.APIError` e subclasses (`RateLimitError`, `APIConnectionTimeoutError`, `OverloadedError` 529); cabeçalho `request-id`.
- **Model ID:** use ID de snapshot datado ou alias conscientemente. Alias móvel muda o comportamento sem deploy. Consulte a documentação oficial para IDs vigentes antes de afirmar que um ID existe ou foi descontinuado.

## @google/genai

- **Cliente:** `new GoogleGenAI({ apiKey })` (Gemini API) ou `{ vertexai: true, project, location }`. `GEMINI_API_KEY`/`GOOGLE_API_KEY` só no servidor. Chave `AIza...` em bundle de cliente é público.
- **Chamada:** `ai.models.generateContent({ model, contents, config })`; `config.systemInstruction` para instruções; `config.maxOutputTokens`, `temperature`, `abortSignal`, `httpOptions: { timeout }`.
- **Saída estruturada:** `config.responseMimeType: 'application/json'` e `config.responseSchema` (ou `responseJsonSchema`). Valide no app; o modo JSON reduz, e não elimina, desvio de schema.
- **Parada e bloqueio:** `response.candidates?.[0]?.finishReason` (`STOP`, `MAX_TOKENS`, `SAFETY`, `RECITATION`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `MALFORMED_FUNCTION_CALL`, ...). `response.promptFeedback?.blockReason` quando a entrada é bloqueada: nesse caso `candidates` pode vir vazio. `response.text` pode lançar ou vir `undefined` em bloqueio: checar antes.
- **Tools:** `config.tools: [{ functionDeclarations: [...] }]`; `response.functionCalls` (nome e `args`): allowlist e validação dos args. `config.toolConfig.functionCallingConfig` (`mode: 'ANY'` com `allowedFunctionNames`) restringe.
- **Segurança:** `config.safetySettings` por categoria; o default varia por modelo. Não desligue sem decisão registrada.
- **Streaming:** `generateContentStream`, iterar com `for await`; `usageMetadata` no último chunk.
- **Cache:** `ai.caches.create` (context caching explícito) para prefixo grande reutilizado; TTL; custo de armazenamento. Caching implícito automático em modelos recentes.
- **Uso:** `usageMetadata.promptTokenCount`, `candidatesTokenCount`, `cachedContentTokenCount`, `thoughtsTokenCount`.
- **Contagem prévia:** `ai.models.countTokens` para limitar entrada.
- **Embeddings:** `ai.models.embedContent` com `taskType` coerente (`RETRIEVAL_DOCUMENT` na ingestão, `RETRIEVAL_QUERY` na consulta) e `outputDimensionality` fixo.

## MCP SDK (`@modelcontextprotocol/sdk`, `mcp` em Python)

- **Servidor:**
  - Cada tool: `name`, `description` clara e fixa, `inputSchema` estrito (zod), `annotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`) corretas.
  - Valide args no handler, ainda que o schema exista no protocolo.
  - Autorização por tool com a identidade do cliente autenticado. Transporte HTTP com autenticação (OAuth/token) e validação de `Origin`; bind em `127.0.0.1` em servidor local.
  - stdio: log em `stderr`, nunca em `stdout` (corrompe o protocolo).
  - Tool de filesystem confinada a root, com normalização de caminho (`path.resolve` e checagem de prefixo; symlink).
  - Tool de shell/SQL arbitrário: evite. Use operações nomeadas e parametrizadas.
  - Resultado de tool é entrada para o LLM do cliente: dado de terceiros dentro dele é vetor de injeção indireta; devolva conteúdo mínimo e marque como dado.
  - Limite de tamanho do resultado e timeout por tool.
- **Cliente:** descrição de tool de servidor de terceiros é conteúdo não confiável (tool poisoning, "rug pull" quando a descrição muda após aprovação). Fixe versão do servidor, revise as descrições, exiba aprovação para efeitos, restrinja o conjunto de tools por fluxo.
- **Sampling/elicitation:** servidor que pede ao cliente que invoque o modelo (`sampling/createMessage`) consome orçamento do cliente: exija aprovação e limite.
- **Segredos:** variáveis de ambiente do servidor stdio herdam do processo pai; passe só o necessário.
- **Confused deputy:** servidor que chama API de terceiro com credencial própria faz isso em nome de qualquer cliente. Use credencial do usuário final.

## langchain, ai (Vercel AI SDK) e frameworks

- Abstração esconde `finish_reason`, `refusal` e `usage`. Confirme que o wrapper os expõe e que o código os checa.
- `AgentExecutor`/`createReactAgent`: `maxIterations` explícito (`recursionLimit` no LangGraph). Tools da biblioteca com acesso a shell, Python REPL e requests amplos (`PythonREPLTool`, `ShellTool`, `RequestsGetTool`) são de alto risco.
- `ai` (Vercel): `generateObject`/`streamObject` com schema zod valida a saída; `maxSteps` em tool loop; `abortSignal`; `experimental_telemetry` com `recordInputs: false` quando há PII.
- Retrievers com `filter` por metadados no construtor: verifique que o filtro vem da sessão.
- Memória de conversa por chave previsível (`sessionId` do cliente) permite ler a conversa de outro usuário.
- Callbacks que logam prompts completos: PII.
- Versões de pacotes de framework mudam com frequência; confirme a API contra a versão instalada.

## Sinais de alerta rápidos

- `new OpenAI({ dangerouslyAllowBrowser: true })` ou chave em variável pública.
- `JSON.parse(completion.choices[0].message.content!)` com `!`.
- `tools[call.function.name](JSON.parse(call.function.arguments))`.
- `anthropic.messages.create` sem checar `stop_reason`.
- `response.text` do Gemini sem checar `promptFeedback`/`finishReason`.
- `while (response.stop_reason === 'tool_use')` sem contador.
- Servidor MCP com tool `run_sql`, `exec` ou `read_file(path)` sem confinamento.
- `eval`/`new Function` sobre qualquer coisa vinda de `choices`, `content`, `text`.
