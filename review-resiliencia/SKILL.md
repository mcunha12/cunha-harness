---
name: review-resiliencia
description: Revisa tratamento de erros e resiliência distribuída em diff de código (RES) — catch que engole erro, floating promises, chamadas sem timeout, retry sem backoff ou sobre operação não idempotente, consumidor de fila sem DLQ, dual write, graceful shutdown, error boundary. Acione standalone ("revisa a resiliência desse PR", "esse retry está certo?", "/review-resiliencia") ou via master-review. NÃO cobre autorização e injeção (review-seguranca), N+1, índice e cache (review-queries), shape de payload (review-contratos), instrumentação de logs e métricas (review-observabilidade), DDL e locks de migration (review-migrations) nem testes (test-audit).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-resiliencia

## Missão

Encontrar no diff os pontos em que uma falha parcial vira falha total, falha silenciosa ou dado inconsistente. O agente lê cada chamada de I/O (HTTP, banco, fila, LLM, cache, disco) e cada bloco de tratamento de erro. Para cada um, responde: o que acontece quando o dependente fica lento, devolve erro, devolve lixo ou cai no meio da operação? O resultado é um conjunto pequeno de achados com evidência, impacto e correção em código.

## Escopo

Cada item segue o formato sinal no código, impacto, correção típica.

### 1. Erros engolidos ou mascarados

- **catch vazio ou só com log.** Sinal: `catch (e) {}`, `catch { return null }`, `except Exception: pass`. Impacto: a operação falha e o chamador segue como se tivesse dado certo. Correção: propague, ou trate com ação concreta (fallback documentado, compensação) e registre uma vez.
- **catch genérico sobre bloco grande.** Sinal: `try` envolvendo 30 linhas e `catch` que devolve resposta de "erro de rede". Impacto: `TypeError` e bug de programação aparecem como indisponibilidade do vendor. Correção: reduza o `try` à chamada que falha e filtre por tipo (`instanceof`, `isAxiosError`, código do erro).
- **log-and-rethrow.** Sinal: `logger.error(e); throw e` em cada camada. Impacto: um erro gera N linhas e N alertas. Correção: registre na fronteira que trata ou converte o erro. As camadas intermediárias só propagam.
- **perda de causa.** Sinal: `throw new Error('falhou')` dentro de `catch`. Impacto: o stack original some. Correção: `throw new DomainError('msg', { cause: e })`. Em Python, `raise X(...) from e`.
- **erro virando sucesso.** Sinal: `catch` devolvendo `[]`, `null`, `0`, `{ ok: true }` ou HTTP 200 com corpo de erro. Impacto: o cliente cacheia o vazio e a tela mostra "sem dados" no lugar de "falha". Correção: lance erro tipado e deixe o handler mapear para 5xx; use fallback só com sinalização (`degraded: true`).
- **erro de domínio e erro técnico misturados.** Sinal: o mesmo tipo de exceção para "matrícula não encontrada" e "banco fora". Impacto: retry sobre erro de domínio, 500 para caso esperado. Correção: hierarquia com classe por categoria e mapeamento único para status.
- **mensagem interna ao usuário.** Sinal: `res.status(500).json({ message: err.message })`. Impacto: vazamento de detalhe interno (a gravidade de segurança é do review-seguranca, vire handoff). Correção: mensagem estável ao usuário, detalhe só no log.

### 2. Promises e concorrência

- **floating promise.** Sinal: chamada async sem `await`, `return` ou `.catch` em handler, `useEffect` ou construtor. Impacto: rejeição vira `unhandledRejection` e, no Node 15+, derruba o processo. Correção: `await`, ou `void p.catch(handleError)` quando o fire-and-forget é intencional.
- **await faltando em `try`.** Sinal: `try { return fetchX() } catch {}`. Impacto: o `catch` nunca roda. Correção: `return await fetchX()` dentro do `try`.
- **async em `forEach`/`map` sem `Promise.all`.** Impacto: o fluxo termina antes do trabalho e os erros se perdem. Correção: `for...of` com `await` (sequencial) ou `Promise.allSettled` (paralelo com falha parcial).
- **`Promise.all` onde falha parcial é aceitável.** Impacto: uma falha cancela o resultado de todas. Correção: `allSettled` e tratamento por item. A decisão de paralelismo e fan-out é do review-queries.
- **`finally` ausente.** Sinal: lock, conexão, timer, stream ou flag `loading` liberados só no caminho feliz. Correção: `finally`, `using`, `try/with`.

### 3. Chamadas externas

- **sem timeout.** Sinal: `axios.create()` sem `timeout`, `fetch` sem `AbortSignal.timeout`, `requests.get` sem `timeout=`, cliente de LLM no default. Impacto: o default é infinito (axios, requests). Uma dependência lenta prende conexões, o pool esgota e o serviço todo para. Correção: timeout por chamada, derivado do orçamento da rota (connect e total).
- **deadline não propagado.** Sinal: timeout de 30 s numa chamada dentro de rota com SLA de 10 s. Impacto: o usuário já desistiu e o trabalho continua. Correção: calcule o tempo restante e passe adiante; cancele com `AbortController`.
- **retry em erro permanente.** Sinal: retry em 4xx (exceto 408/429), em `ValidationError`, em 401. Impacto: carga inútil e atraso. Correção: lista explícita de condições transitórias (5xx, 408, 429, `ECONNRESET`, `ETIMEDOUT`).
- **retry sem backoff e jitter.** Sinal: laço com `sleep(1000)` fixo ou sem espera. Impacto: thundering herd quando o dependente volta. Correção: exponencial com jitter completo e teto, respeitando `Retry-After`.
- **retry sobre operação não idempotente.** Sinal: POST de cobrança, envio de e-mail, criação de matrícula com retry automático e sem `Idempotency-Key`. Impacto: duplicata. Correção: chave de idempotência gerada uma vez, fora do laço, e checada pelo receptor.
- **retry amplificado em camadas.** Sinal: retry no client HTTP, no serviço e no job. Impacto: 3×3×3 = 27 chamadas por falha. Correção: retry em uma camada só, a mais próxima da chamada, com orçamento total.
- **sem circuit breaker ou bulkhead** em dependência crítica e instável. Impacto: filas de requests presas na dependência derrubam rotas que não a usam. Correção: breaker (opossum, cockatiel, tenacity/pybreaker) e pool ou semáforo separado por dependência.
- **sem degradação graciosa.** Sinal: dependência não essencial (recomendação, avatar, analytics) fazendo a rota inteira falhar. Correção: fallback, `stale-on-error` no cache, ou omissão do bloco com sinalização.

### 4. Idempotência e consistência

- **consumidor de fila sem dedup.** Sinal: handler at-least-once que incrementa, envia, cobra ou insere sem checar `messageId`. Impacto: reentrega duplica efeito. Correção: tabela de processados com unique, ou operação naturalmente idempotente (`upsert`, `SET` absoluto).
- **ack/nack mal posicionado.** Sinal: `ack` antes do processamento, `nack(requeue: true)` sem limite, handler que lança sem `nack`. Impacto: perda de mensagem ou loop infinito de reentrega. Correção: `ack` depois do efeito durável, DLQ com `x-dead-letter-exchange`, contador de tentativas, `prefetch` explícito.
- **dual write.** Sinal: gravar no banco e depois publicar evento (ou chamar outro serviço) na mesma função, sem transação que cubra os dois. Impacto: a falha entre os passos deixa o estado divergente. Correção: outbox transacional, ou saga com compensação.
- **multi-serviço sem compensação.** Sinal: sequência de chamadas de escrita sem desfazer a primeira quando a terceira falha. Correção: ordem que deixa o passo irreversível por último, ou compensação explícita.
- **check-then-act (TOCTOU).** Sinal: `findFirst` seguido de `create`, ou leitura de saldo, vaga e quota seguida de escrita. Impacto: duas requests concorrentes passam na checagem. Correção: constraint unique, `upsert`, `UPDATE ... WHERE` condicional, optimistic locking (coluna `version`) ou lock.
- **webhook sem dedup.** Impacto: o provedor reenvia e o efeito repete. Correção: dedup pelo id do evento e resposta 2xx rápida com processamento assíncrono.

### 5. Ciclo de vida

- **recurso não fechado.** Sinal: `createReadStream`, cliente de DB, canal AMQP, `setInterval`, listener sem teardown. Impacto: vazamento e esgotamento de descritores ou conexões. Correção: `finally`, `onModuleDestroy`, `pipeline` com tratamento de erro.
- **sem graceful shutdown.** Sinal: NestJS sem `app.enableShutdownHooks()`, servidor sem handler de `SIGTERM`, consumidor que não para de consumir antes de sair. Impacto: deploy corta requests e jobs em andamento. Correção: hooks de shutdown, `server.close()`, drenar fila, fechar pools em ordem.
- **liveness e readiness confundidos.** Sinal: liveness que consulta banco ou dependência externa. Impacto: a queda do banco reinicia todos os pods e piora o incidente. Correção: liveness só do processo; readiness checa dependências essenciais, com timeout curto.
- **config sem validação no boot.** Sinal: `process.env.X` lido na hora do uso, `parseInt` sem checagem. Impacto: o erro aparece na primeira request, em produção. Correção: schema (zod, `@nestjs/config` com `validate`, pydantic-settings) falhando na inicialização.
- **timer e conexão que mantêm o processo vivo** em job e script: sem `process.exit` coerente ou `unref`.

### 6. Front-end

- **sem error boundary** em torno de remote do Module Federation, rota ou widget isolado. Impacto: um throw no render derruba a árvore. Correção: boundary por fronteira, com fallback e reset.
- **decode de dado externo sem try/catch** (`JSON.parse`, `atob`). Correção: try/catch com estado de erro local.
- **retry do react-query em mutation.** Sinal: `retry` configurado em `useMutation` sobre operação não idempotente. Correção: `retry: false` na mutation, ou idempotency key.
- **`onError` ausente** que deixa o usuário sem feedback, ou estado `loading` que nunca sai após erro.
- **callback assíncrono após unmount** sem guard ou `AbortController`.

## Fora de escopo e dono

| Tema | Dono | Ação |
|---|---|---|
| SQL injection, XSS, authZ, mensagem de erro que vaza segredo | review-seguranca | handoff |
| N+1, índice, fan-out sequencial, cache e stampede | review-queries | handoff |
| Shape de request/response, código de status como contrato, versionamento | review-contratos | handoff |
| Log, trace e métrica de erro, PII em log | review-observabilidade | handoff |
| Lock de DDL, backfill, expand/contract | review-migrations | handoff |
| Ausência de teste para o caminho de falha | test-audit | handoff |
| Naming e complexidade do `try/catch` | review-legibilidade | ignorar |

O dono reporta. Esta skill registra handoff de uma linha e segue.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` e o reference de cada tecnologia detectada, entre `typescript.md`, `react.md`, `nestjs.md`, `node.md`, `prisma-postgres.md`, `python.md`. Registre os lidos em `stack_references_loaded`.
3. Obtenha o diff. Com context packet do orquestrador, use-o. Standalone, detecte a base (`main`, `master` ou `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged. `--path` restringe por glob.
4. Analise cada hunk com I/O ou tratamento de erro. Monte, por chamada, a tabela mental: timeout, retry, idempotência, destino do erro, liberação de recurso.
5. Verifique o contexto antes de reportar. Abra o caller (quem trata o erro acima?), o callee (já tem retry ou timeout interno?), a config do client (`axios.create`, interceptors, `retry` global do `QueryClient`, `http.Agent`) e o middleware ou filtro global (`ExceptionFilter`, `unhandledRejection`).
6. Classifique severidade e confiança com a rubrica do tema abaixo e a rubrica global.
7. Emita o resultado no output contract: bloco JSON e depois markdown. Prefixo dos ids: `RES`. Máximo de ~15 achados.

Standalone: mostre o markdown no final. Não altere código.

## Rubrica de severidade do tema

**BLOCKER**
- Consumidor de fila com `nack(requeue: true)` incondicional sobre erro permanente: loop infinito de reentrega.
- Retry automático em POST de cobrança ou criação de matrícula sem idempotency key.
- Dual write em fluxo financeiro ou de matrícula: banco gravado e evento perdido em falha, sem outbox.

**MAJOR**
- Chamada HTTP a serviço externo em rota de usuário sem timeout.
- `catch` que devolve `[]` ou `null` e o front exibe como "sem dados".
- Floating promise em handler de request: rejeição derruba o processo.
- Check-then-act sem unique constraint em recurso com concorrência real (vaga, quota).
- Retry sem backoff e sem teto sobre dependência instável.

**MINOR**
- `throw new Error(msg)` sem `cause` dentro de `catch`.
- Log-and-rethrow em duas camadas.
- Liveness probe que consulta dependência não crítica.
- `Promise.all` onde `allSettled` evitaria perda de resultado parcial, com impacto limitado.

**NIT**
- `catch (e: any)` sem uso do erro, em script descartável.
- Constante de timeout sem nome.

## Heurísticas anti-falso-positivo

- Verifique o `timeout` no `axios.create` ou no wrapper compartilhado antes de reportar chamada sem timeout.
- Verifique `QueryClient.defaultOptions` e `axios-retry` global antes de apontar retry ausente ou duplicado.
- `catch` vazio com comentário e motivo (por exemplo, `ENOENT` esperado em limpeza de cache) não se reporta.
- Fire-and-forget deliberado com `.catch(log)` é válido.
- Operação naturalmente idempotente (`PUT`, `upsert`, `SET` absoluto, `DELETE`) dispensa idempotency key.
- Script de migração ou CLI de uso único aceita falha rápida: `throw` sem tratamento é adequado.
- Framework que já trata (NestJS `ExceptionFilter` global, Express com `express-async-errors`, Fastify) cobre `throw` em handler. Confirme no bootstrap.
- Retry dentro do SDK (openai, `@google/genai`, aws-sdk) já existe com default. Reporte duplicação, e só com evidência da camada externa.
- `useEffect` com fetch de leitura e sem cleanup: o dono é review-front.
- Não reporte falta de circuit breaker em chamada interna de baixo volume sem histórico de instabilidade. Se reportar, use MINOR com confiança media.
- Confiança baixa exige dizer o que confirmaria (config do broker, valor de `prefetch`, política de retry da plataforma).

## Ferramentas determinísticas opcionais

Rode só se instaladas no repo. Nunca instale. A saída é insumo.

- `@typescript-eslint/no-floating-promises`, `no-misused-promises`, `require-await`, `only-throw-error`, `use-unknown-in-catch-callback-variable`. Verificar: `ls node_modules/.bin/eslint`. Executar: `npx eslint --rule '{"@typescript-eslint/no-floating-promises":"error"}' <arquivos do diff>` (exige `parserOptions.project`).
- `eslint-plugin-promise` (`catch-or-return`, `no-return-in-finally`). Executar com o `eslint` do repo.
- `eslint no-empty` com `allowEmptyCatch: false`.
- Python: `ruff check --select BLE,TRY,S110,S112,ASYNC <arquivos>`. Verificar: `command -v ruff`. `pyright` para coroutine não awaited (`reportUnusedCoroutine`).
- `semgrep` com regras de `empty-catch` quando houver config no repo.

## Exemplos

### Achado 1

```
### [BLOCKER] RES-001 — Consumidor reenfileira para sempre mensagem com erro permanente
**Onde:** pos-notifications/src/consumers/enrollment.consumer.ts:31-44 · **Confiança:** alta · **Esforço:** M
**Evidência:**
@RabbitSubscribe({ queue: 'enrollment.created' })
async handle(msg: EnrollmentCreated, raw: ConsumeMessage) {
  try {
    await this.mailer.sendWelcome(msg.email);
  } catch (e) {
    return new Nack(true);
  }
}
**Problema:** Todo erro vira `Nack(true)`. E-mail inválido (erro permanente) volta à fila imediatamente, sem limite e sem DLQ. O consumidor gira em loop, ocupa o `prefetch` e atrasa as mensagens válidas atrás dela. `mailer.sendWelcome` não é idempotente: uma reentrega após timeout duplica o e-mail.
**Correção:**
if (isTransient(e) && attempts(raw) < 3) return new Nack(false); // vai para a retry-queue com TTL
await this.processed.save(msg.id);                               // dedup por messageId
return new Nack(false);                                          // DLQ via x-dead-letter-exchange
```

### Achado 2

```
### [MAJOR] RES-002 — Chamada ao provedor de pagamento sem timeout
**Onde:** pos-billing/src/clients/gateway.client.ts:12-19 · **Confiança:** alta · **Esforço:** S
**Evidência:**
const http = axios.create({ baseURL: env.GATEWAY_URL });
async charge(dto: ChargeDto) {
  return (await http.post('/charges', dto)).data;
}
**Problema:** axios usa `timeout: 0` (infinito). Se o gateway segurar a conexão, cada request de cobrança prende uma conexão e uma thread lógica. Com pool de 20 conexões, 20 requests lentas bloqueiam a rota inteira.
**Correção:**
const http = axios.create({ baseURL: env.GATEWAY_URL, timeout: 8_000 });
async charge(dto: ChargeDto, key: string) {
  return (await http.post('/charges', dto, { headers: { 'Idempotency-Key': key } })).data;
}
```

### Caso que parece problema e NÃO se reporta

```ts
try {
  await fs.unlink(tmpPath);
} catch (e) {
  if ((e as NodeJS.ErrnoException).code !== 'ENOENT') throw e;
}
```

O `catch` ignora só `ENOENT`, que significa "arquivo já removido" e o efeito desejado já existe. Os demais erros propagam. O padrão engole um erro específico, esperado e idempotente.
