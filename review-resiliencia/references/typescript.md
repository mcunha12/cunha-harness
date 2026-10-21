# Resiliência — TypeScript

Carregue quando o repo tem `tsconfig*.json` ou `typescript` nas deps.

## catch e unknown

- Sinal: `catch (e: any)` e acesso a `e.message`, `e.response.data`. Impacto: o valor lançado pode ser string, `undefined` ou objeto sem `message`. O handler lança `TypeError` dentro do `catch` e esconde o erro original. Correção: `useUnknownInCatchVariables` (parte do `strict`), e narrowing.

```ts
function toError(e: unknown): Error {
  return e instanceof Error ? e : new Error(String(e), { cause: e });
}
```

- Narrowing de erro de axios: `axios.isAxiosError(e)` antes de ler `e.response?.status`. Erro de timeout não tem `response`. Código `ECONNABORTED` (timeout), `ERR_CANCELED` (abort), `ETIMEDOUT`, `ECONNRESET`.
- Erro de domínio como classe com `name` e `code` estáveis. `instanceof` falha entre pacotes duplicados e após serialização. Quando cruza fronteira de processo, use `code`.
- `Error.cause`: `new Error('msg', { cause })` exige `lib` ES2022 no `tsconfig`. Sem ela, o segundo argumento é ignorado pelo tipo e a causa se perde sem aviso do compilador em alvos antigos. Confirme `target`/`lib`.

## Promises

- `@typescript-eslint/no-floating-promises` e `no-misused-promises` cobrem o grosso. Sem as regras ligadas no repo, registre o ponto como MINOR de configuração e aponte as ocorrências do diff.
- Pontos de maior risco: callbacks async passados onde se espera retorno `void` (`array.forEach(async ...)`, `emitter.on('x', async ...)`, `setTimeout(async ...)`, `app.get('/', async (req, res) => ...)` em Express 4 sem wrapper). Em Express 4, rejeição em handler async não chega ao error middleware e a request fica pendurada. Correção: `express-async-errors`, wrapper `asyncHandler`, ou Express 5.
- `return promise` dentro de `try` sem `await` pula o `catch`.
- `Promise.all(items.map(async ...))` com milhares de itens dispara tudo de uma vez. Efeito: estouro de conexão e rate limit. Correção: `p-limit`, `p-map` com `concurrency`, ou lotes.
- `async` com `await` em laço sobre chamadas independentes: latência somada. Dono do tema de fan-out: review-queries. Aqui só o efeito de falha.
- `process.on('unhandledRejection')` que só loga e segue mascara estado corrompido. Correção: logar e sair para o supervisor reiniciar, salvo política documentada.

## Timeouts e cancelamento

```ts
const res = await fetch(url, { signal: AbortSignal.timeout(5_000) });
```

- `fetch` nativo não tem timeout default. `AbortSignal.timeout(ms)` (Node 17.3+) cria o limite. Combine com sinal do chamador: `AbortSignal.any([req.signal, AbortSignal.timeout(5_000)])` (Node 20.3+).
- axios: `timeout` cobre a resposta inteira só em parte dos casos (não cobre a fase de DNS em todas as versões). Para limite rígido use `signal: AbortSignal.timeout(...)` além do `timeout`.
- `Promise.race([call(), sleep(ms).then(() => { throw ... })])` deixa `call()` rodando. Prefira abort real.
- Timer de `setTimeout` pendente mantém o processo vivo em teste e CLI. `clearTimeout` no `finally`, ou `.unref()`.

## Retry em TypeScript

- Bibliotecas comuns: `axios-retry`, `p-retry`, `cockatiel`, `async-retry`. Verifique `retryCondition`: o default do `axios-retry` repete só métodos idempotentes e erros de rede, e `retryCondition` customizado que devolve `true` para tudo quebra essa proteção.
- `p-retry` com `AbortError` para marcar erro permanente. Sem ele, todo erro é repetido.
- Backoff com jitter: `retryDelay: axiosRetry.exponentialDelay` não inclui jitter completo em todas as versões. Confirme.
- Retry em volta de `fetch` sem checar `res.ok`: `fetch` só rejeita em falha de rede, e 500 vira resposta "bem-sucedida". Correção: `if (!res.ok) throw new HttpError(res.status)` antes da política de retry.

## zod e dados externos

- `schema.parse` lança `ZodError`. Em borda, converta para erro de domínio 4xx. `safeParse` quando o fluxo trata a falha.
- `JSON.parse` e `res.json()` de fonte externa dentro de `try/catch`, com erro de domínio de "resposta inválida do provedor". Resposta inválida de dependência é 502, não 500 e nem 400.
- `Response.json()` sobre corpo vazio ou HTML de erro de proxy lança `SyntaxError`. Cheque `content-type` ou status antes.

## Result e exaustividade

- Retorno `T | null` ambíguo entre "não existe" e "falhou" força o chamador a adivinhar. Correção: lance para falha, retorne `null` só para ausência esperada, ou use union discriminada `{ ok: true, value } | { ok: false, error }`.
- Em `switch` sobre `error.code`, caso `default` com `assertNever` evita erro novo sem tratamento.

## Streams e eventos (Node)

- Use `stream.pipeline` / `pipeline` de `stream/promises`. `.pipe()` não propaga erro nem destrói o destino.
- `EventEmitter` sem listener de `'error'` derruba o processo.
- Handler de `'close'` e `'error'` em `child_process` e `net.Socket`.

## Padrões de correção prontos

```ts
export async function withRetry<T>(fn: (attempt: number) => Promise<T>, opts: { max: number; baseMs: number; capMs: number; isTransient: (e: unknown) => boolean }): Promise<T> {
  for (let attempt = 1; ; attempt++) {
    try { return await fn(attempt); }
    catch (e) {
      if (attempt >= opts.max || !opts.isTransient(e)) throw e;
      const delay = Math.random() * Math.min(opts.capMs, opts.baseMs * 2 ** attempt); // full jitter
      await new Promise((r) => setTimeout(r, delay));
    }
  }
}
```

```ts
const results = await Promise.allSettled(ids.map((id) => load(id)));
const failed = results.filter((r): r is PromiseRejectedResult => r.status === 'rejected');
```
