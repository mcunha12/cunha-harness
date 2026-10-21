# Observabilidade — SDKs de LLM

Carregue quando `openai`, `@anthropic-ai/sdk`, `@google/genai`, `langchain*`, `ai` ou o MCP SDK está nas deps. Esta skill cobre a instrumentação. O desenho do prompt, a segurança e o custo por design são do review-ia.

## O que registrar por chamada

| Campo | Fonte | Uso |
|---|---|---|
| `model` (ID exato retornado) | resposta (`response.model`) | regressão por troca de versão |
| `provider`, `operation` | wrapper | agrupamento |
| `tokens_in`, `tokens_out`, `tokens_cached_read`, `tokens_cache_write`, `tokens_reasoning` | `usage` | custo e eficácia do cache |
| `latency_ms` total e `ttft_ms` (time to first token) em streaming | relógio | SLO |
| `stop_reason` (`finish_reason`, `stop_reason`, `finishReason`) | resposta | truncamento (`length`/`max_tokens`), refusal, tool use |
| `error_type`, `http_status`, `retry_count` | exceção | taxa de erro e de 429 |
| `prompt_version` / `template_id` | app | correlação de qualidade com versão |
| `feature` / `use_case`, `tenant` | app | atribuição de custo |
| `cost_usd` estimado | tokens × tabela de preço configurável | orçamento |
| `request_id` do provedor (`x-request-id`, `request-id`) | headers | suporte do provedor |

- Registre contagem e hash do conteúdo, não o conteúdo. Conteúdo completo só em amostra, com redação de PII, retenção curta e acesso restrito. Prompt e resposta carregam dado de aluno e caso clínico.
- O mesmo `trace_id` do request de entrada liga a chamada ao LLM, à tool call e à resposta final.

## Padrão de wrapper (um ponto de instrumentação)

```ts
async function llmCall<T>(meta: { feature: string; promptVersion: string; model: string }, fn: () => Promise<{ result: T; usage: Usage; stop: string; requestId?: string }>) {
  return tracer.startActiveSpan('llm.call', async (span) => {
    const t0 = performance.now();
    span.setAttributes({ 'gen_ai.request.model': meta.model, 'app.feature': meta.feature, 'app.prompt_version': meta.promptVersion });
    try {
      const out = await fn();
      span.setAttributes({ 'gen_ai.usage.input_tokens': out.usage.in, 'gen_ai.usage.output_tokens': out.usage.out, 'gen_ai.response.finish_reasons': [out.stop] });
      llmTokens.inc({ feature: meta.feature, model: meta.model, kind: 'in' }, out.usage.in);
      llmTokens.inc({ feature: meta.feature, model: meta.model, kind: 'out' }, out.usage.out);
      return out.result;
    } catch (e) {
      span.recordException(e as Error);
      span.setStatus({ code: SpanStatusCode.ERROR });
      llmErrors.inc({ feature: meta.feature, model: meta.model, type: errorType(e) });
      throw e;
    } finally {
      llmLatency.observe({ feature: meta.feature, model: meta.model }, (performance.now() - t0) / 1000);
      span.end();
    }
  });
}
```

- Convenções OTel GenAI: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`. Use-as quando o repo já adota; se não, siga o padrão local.
- Labels de métrica: `feature`, `model`, `provider`, `kind`, `outcome`. Nunca `userId`, `conversationId` nem texto de prompt.

## Sinais no diff

- **Chamada direta ao SDK em vários arquivos** sem wrapper: cada uma fica sem instrumentação ou instrumenta de um jeito. Correção: um client/wrapper central.
- **`usage` ignorado** na resposta. Custo e tokens ficam invisíveis. Em streaming, o `usage` vem no evento final (`stream_options: { include_usage: true }` na OpenAI; `message_delta`/`message_stop` no Anthropic; `usageMetadata` no último chunk do Gemini). Wrapper que consome o stream precisa capturá-lo.
- **`stop_reason`/`finish_reason` ignorado**: `length`/`max_tokens` entrega texto cortado como se estivesse completo. Registre e conte como métrica (`truncated_total`). O tratamento da resposta truncada é do review-ia.
- **Refusal** (`refusal` na OpenAI, `stop_reason: 'refusal'` na Anthropic, `finishReason: SAFETY` no Gemini): conte e registre por categoria.
- **Retry do SDK invisível**: `maxRetries` do cliente (default 2 em `openai` e `@anthropic-ai/sdk`) retenta em silêncio e a latência aparece alta sem causa. Registre `retry_count` (hooks, `fetch` customizado ou `response.headers`) e o 429.
- **Streaming sem métrica de TTFT** nem de abandono (cliente cancelou, `AbortError`): informação central de UX de chat.
- **Log do prompt completo**: PII, caso clínico, RAG com dado de outros alunos. BLOCKER quando vai para `info`/`error` em produção sem redação.
- **Log da resposta de erro do provedor** com o corpo do request ecoado (alguns erros devolvem trecho do prompt). Logue `status`, `type`, `code`, `request_id`.
- **Chave de API em log** de configuração ou de erro (`error.config.headers`, `client.apiKey`).
- **Prompt sem versão**: não dá para ligar queda de qualidade a mudança. Inclua `prompt_version` (hash do template ou semver).
- **Tool calls e agentes**: cada iteração do loop e cada tool com span filho (`tool.name`, duração, sucesso, tamanho do resultado). Número de iterações e motivo de parada do agente como métrica. Loop sem contador é invisível até custar caro.
- **RAG**: span de retrieval com `top_k`, número de documentos devolvidos, latência, e ids dos documentos (sem conteúdo). Sem isso, não se explica uma resposta ruim.
- **Embeddings**: tokens e latência também contam, e lote com falha parcial precisa de log por item falho.
- **Batch API / jobs assíncronos**: log de `batch_id`, estado, contagem de sucesso e erro, custo.
- **Avaliação online**: score de feedback do usuário (polegar) ligado ao `trace_id` e ao `prompt_version`.
- **Cache de prompt**: registre `cache_read_input_tokens` e `cache_creation_input_tokens`. Taxa de acerto cai a zero depois de uma mudança de prefixo e só a métrica mostra.
- **Fallback de modelo**: log `warn` com modelo original, modelo usado e motivo; métrica de contagem. Fallback silencioso mascara custo e qualidade.
- **Alertas**: taxa de erro do provedor, p95 de latência, taxa de truncamento, consumo diário de tokens contra o orçamento, picos por `feature`.

## Por SDK

- **openai**: `response.usage` (`prompt_tokens`, `completion_tokens`, `prompt_tokens_details.cached_tokens`, `completion_tokens_details.reasoning_tokens`); Responses API: `usage.input_tokens`/`output_tokens`. Header `x-request-id` via `.withResponse()` (`const { data, response } = await client.chat.completions.create(...).withResponse()`). Streaming: `stream_options.include_usage`.
- **@anthropic-ai/sdk**: `message.usage` (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`), `message.stop_reason`, `message.id`, `_request_id` na resposta. Streaming: `stream.finalMessage()` devolve `usage` completo.
- **@google/genai**: `response.usageMetadata` (`promptTokenCount`, `candidatesTokenCount`, `cachedContentTokenCount`, `thoughtsTokenCount`), `candidates[0].finishReason`, `promptFeedback.blockReason` (bloqueio de segurança sem candidato: acessar `candidates[0]` lança erro; registre o bloqueio).
- **MCP SDK**: log de cada `tools/call` com nome, duração, `isError` e tamanho do resultado; propagação de contexto de trace no servidor MCP quando o transporte permite (`_meta`). Log de stdio do servidor MCP vai para stderr, nunca para stdout (corrompe o protocolo).
- **langchain / `ai` (Vercel)**: callbacks/telemetria (`experimental_telemetry` no `ai`) ligam spans automaticamente; confirme que `recordInputs`/`recordOutputs` estão desligados quando há PII.

## Sinais de alerta rápidos

- `console.log(completion)` ou `logger.info({ completion })`: conteúdo completo e metadados do provedor.
- `catch (e) { return fallbackText }` sem log nem métrica: erro de LLM some.
- Custo calculado com preço fixo hardcoded: tabela de preços em config.
- Métrica de tokens ausente em feature que chama o LLM por request de usuário.
