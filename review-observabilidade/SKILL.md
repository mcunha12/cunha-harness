---
name: review-observabilidade
description: Revisa observabilidade num diff (OBS) — logs estruturados e nível correto, PII e segredos em log e telemetria (LGPD), correlation id e traceparent entre serviços, spans OpenTelemetry, métricas RED e cardinalidade de labels, Sentry/New Relic com contexto, analytics de produto (naming, PII, disparo duplicado), instrumentação de chamadas a LLM (tokens, latência, custo), audit log e alerta de rota crítica. Acione standalone ("revisa o logging desse PR", "isso está observável?", "/review-observabilidade") ou via master-review. NÃO cobre segredo hardcoded no código (review-seguranca), qualidade do prompt, injection e custo de tokens por design (review-ia), timeout e retry (review-resiliencia) nem testes (test-audit).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-observabilidade

## Missão

Garantir que o código novo permite responder, em produção e sem deploy extra, quatro perguntas: quebrou? onde? para quem? quanto custou? O agente lê o diff atrás de três falhas: falta de sinal (rota, job ou chamada externa invisível), sinal ruim (log sem contexto, nível errado, label de cardinalidade explosiva, evento duplicado) e sinal perigoso (PII, token e segredo indo para log, trace ou analytics). Cada achado traz evidência, impacto operacional e correção em código.

## Escopo

Cada item segue o formato sinal no código, impacto, correção típica.

### 1. Logs

- **log não estruturado.** Sinal: `console.log('user ' + id + ' failed')`, `print(f"...")`, string interpolada. Impacto: sem campo, o log não filtra nem agrega. Correção: logger do repo com objeto de contexto (`logger.info({ userId, enrollmentId }, 'enrollment.created')`).
- **`console.*`/`print` solto** em código de serviço quando o repo tem logger (winston, pino, structlog). Impacto: some do pipeline, sem nível, sem correlation id. Correção: logger injetado.
- **nível errado.** Sinal: `error` para caso esperado (validação, 404 de usuário, retry que depois funciona); `info` para falha real; `debug` em caminho de erro. Impacto: `error` não acionável gera ruído, alerta é ignorado, e o erro real se perde. Regra: `error` exige ação humana; `warn` é degradação tolerada; `info` é evento de negócio; `debug` é diagnóstico desligado em produção.
- **sem contexto.** Sinal: `logger.error('falhou')` ou `logger.error(err.message)`. Impacto: o plantonista não sabe qual request, qual usuário (pseudonimizado) nem qual dependência. Correção: `requestId`/`traceId`, rota, `userId` pseudonimizado, duração, id da entidade, e o objeto de erro inteiro (`{ err }`) para o stack.
- **PII e segredo em log.** Sinal: `logger.info({ body })`, `logger.debug(req.headers)`, log de `user`, `email`, CPF, nome, telefone, token, `Authorization`, cookie, URL com `?token=`, prompt ou resposta de LLM com dado de aluno, caso clínico. Impacto: violação de LGPD (dado pessoal sem finalidade), vazamento por quem lê o log. Dono do tema PII em log: esta skill. Correção: allowlist de campos, `redact` (`pino` `redact.paths`, winston format), pseudonimização por hash, log do id.
- **log dentro de laço quente** sem amostragem: custo de ingestão e latência. Correção: log agregado ao fim do lote, ou sampling.
- **log de corpo/resultado grande** (lista inteira, payload de 1 MB). Correção: contagem e ids.
- **erro duplicado** (log-and-rethrow em várias camadas): 1 erro, N linhas, N alertas. Correção: logar na fronteira que trata. O lado de erro engolido é do review-resiliencia.
- **mensagem dinâmica como identificador.** Sinal: `logger.info(\`user ${id} entrou\`)`. Impacto: não agrupa. Correção: mensagem estável e variáveis no contexto.

### 2. Correlation e tracing

- **request id ausente ou não propagado.** Sinal: middleware sem `AsyncLocalStorage`/`cls-hooked`/`contextvars`; id gerado de novo a cada serviço. Impacto: impossível seguir uma request entre serviços e filas. Correção: ler `traceparent`/`x-request-id` na entrada, gerar se ausente, guardar no contexto assíncrono, injetar no logger e em toda chamada de saída.
- **`traceparent` W3C não propagado** em axios/fetch/gRPC e em mensagens de fila (headers da mensagem AMQP). Impacto: o trace quebra no salto. Correção: instrumentação automática do OpenTelemetry (`@opentelemetry/instrumentation-http`, `-amqplib`) ou propagação manual com `propagation.inject`.
- **span sem atributos úteis** em chamada externa: sem `peer.service`, rota, status, `db.system`, `messaging.destination`. Correção: `tracer.startActiveSpan` com atributos semânticos (convenções OTel) e `span.recordException(e)` + `setStatus({ code: ERROR })`.
- **span que nunca fecha** (`span.end()` fora do `finally`): vaza memória e produz trace incompleto.
- **atributo de span com PII ou alta cardinalidade** (e-mail, corpo, query SQL com valores). Correção: id pseudonimizado, SQL parametrizado.
- **sampling** ausente ou 100% em rota de alto volume: custo. Sampling 0% ou alto demais em rota crítica: cegueira. Prefira tail-based ou head com taxa por rota; sempre amostre erros.
- **contexto perdido** em `setTimeout`, worker, callback de EventEmitter, `Promise` fora do contexto: o span filho vira raiz.

### 3. Métricas

- **rota ou job novo sem RED.** Rate, Errors, Duration por rota e por dependência (histograma de latência). Sem isso, não há SLI nem alerta.
- **USE** para recursos: utilização, saturação e erro de pool de conexões, fila (profundidade, idade da mensagem mais antiga), event loop lag, memória.
- **label de alta cardinalidade.** Sinal: label com `userId`, `email`, `requestId`, URL com id (`/turmas/123`), mensagem de erro. Impacto: milhões de séries, custo e queda do backend de métricas. Correção: template de rota (`/turmas/:id`), enum finito, e id vai para trace e log.
- **tipo de métrica errado.** Média de latência sem histograma, counter que decresce, gauge usado como contador. Correção: histograma com buckets coerentes com o SLO.
- **métrica de negócio ausente** para fluxo central (matrícula concluída, pagamento aprovado, aula concluída, resposta de IA entregue). Sem ela, a falha silenciosa de negócio não aparece enquanto os códigos HTTP seguem 200.
- **métrica sem unidade ou nome padrão** (`snake_case`, sufixo `_seconds`, `_total`, `_bytes`).

### 4. Erros e monitoramento (Sentry, New Relic e equivalentes)

- **erro capturado sem contexto.** Falta de `user` (id pseudonimizado), `tags` (rota, tenant, feature), `extra` mínimo, `release`, `environment`. Correção: `Sentry.withScope`, `setTag`, `setUser({ id })`; New Relic `addCustomAttributes`.
- **duplicação**: `captureException` no `catch` mais o filter global que captura de novo. 1 erro vira 2 issues. Defina um ponto único.
- **captura de erro esperado** (validação 4xx, cancelamento por `AbortError`, 404 de negócio). Impacto: ruído e cota. Correção: ignore por tipo (`ignoreErrors`, `beforeSend`).
- **fingerprint** padrão agrupando erros distintos ou separando o mesmo erro por mensagem dinâmica. Correção: `fingerprint` explícito, mensagem estável.
- **source maps** ausentes no build de front (stack minificado ilegível), ou publicados abertos ao público. Verifique o upload no pipeline e `release` igual ao do SDK.
- **PII no evento de erro** (`sendDefaultPii: true`, breadcrumbs com input de formulário, replay sem mascaramento). Correção: `sendDefaultPii: false`, `beforeSend` com scrub, mascarar inputs no replay.
- **`release`/`environment` ausentes**: não dá para ligar erro a deploy nem separar staging de produção.
- **erro de front** (`window.onerror`, unhandled rejection, error boundary) não enviado: invisível. O boundary chama o reporter com contexto de componente.
- **alerta**: erro novo ou rota crítica sem regra de alerta correspondente. Sinal: diff adiciona fluxo de pagamento, matrícula, nota ou webhook sem mencionar dashboard e alerta. Reporte como MINOR/MAJOR por criticidade e indique o SLI.

### 5. Analytics de produto (PostHog, Mixpanel, GA)

- **naming inconsistente.** Evento fora do padrão do repo (`snake_case` vs `Title Case`, verbo no passado, `objeto_acao`). Impacto: dashboards quebrados, duplicidade de eventos. Correção: siga o dicionário de eventos do repo e o spec do contrato quando existe.
- **propriedade fixa que mente.** Atributo constante que descreve fluxo e não o dispositivo ou contexto real. Confira onde o componente é montado.
- **PII** em propriedade de evento ou `identify` (e-mail, CPF, nome). Correção: id interno, categorias.
- **disparo duplicado.** Sinal: `track` dentro de `useEffect` sem guard e sem deps estáveis, sob `React.StrictMode` (executa 2× em dev), em componente remontado, ou em re-render. Impacto: contagem inflada, funil errado. Correção: ref de disparo único (`useRef`), `useEffect` com deps corretas, ou evento no handler de ação do usuário. Ref booleano único sobre duas fontes assíncronas perde dado: use um ref por condição.
- **evento sem as propriedades necessárias** para a pergunta de negócio (sem `courseId`, sem `source`).
- **evento disparado antes de o dado estar pronto** (ids `undefined`): payload incompleto.
- **consentimento** (cookie/opt-out) ignorado.
- **evento de alto volume** (scroll, mousemove, timeupdate) sem throttle: custo e degradação.

### 6. LLM e custo

- **chamada ao LLM sem registro** de: modelo (ID exato), tokens de entrada/saída (e cache read/write), latência (total e time-to-first-token), custo estimado, versão do prompt, motivo de parada (`finish_reason`/`stop_reason`), taxa de erro e de refusal, e id da conversa ou da feature. Correção: wrapper único ou middleware do SDK que emite span e métricas.
- **log de prompt e resposta completos** sem política: PII, caso clínico e dado de aluno em log. Correção: logar hash, tamanho e versão do template; conteúdo só em amostra, com redação e retenção curta, em armazenamento próprio.
- **custo sem atribuição**: tokens sem label de feature ou tenant impossibilitam orçamento. Cuidado com cardinalidade: label por feature, não por usuário.
- **tool calls de agente sem trace** (cada iteração e cada tool como span filho).
- Dono do desenho do prompt, da segurança e do custo por design: review-ia. Esta skill cobre a instrumentação.

### 7. Auditoria e operação

- **audit log ausente** em ação sensível: lançar ou alterar nota, matrícula, cancelamento, permissão, impersonação, exportação de dados, acesso a dado clínico. Campos: quem (ator), o quê, sobre quê (entidade e id), quando, de onde (IP/origem), antes e depois (ou diff), resultado. Armazenamento append-only e separado do log de aplicação.
- **audit log com PII em excesso** ou editável pela própria aplicação.
- **rota crítica sem alerta ou SLO.**
- **health e readiness** sem métrica; job agendado sem heartbeat ou métrica de última execução com sucesso (job parado em silêncio).
- **debug flag** em produção (`LOG_LEVEL=debug` por default, `console.log` de depuração esquecido no diff).
- **fila**: sem métrica de profundidade e idade; DLQ sem alerta.

## Fora de escopo e dono

| Tema | Dono | Ação |
|---|---|---|
| Segredo hardcoded, `.env` versionado, chave no bundle | review-seguranca | handoff |
| Prompt injection, output do LLM, desenho de custo de tokens | review-ia | handoff |
| Timeout, retry, DLQ, erro engolido | review-resiliencia | handoff |
| Shape de payload e de evento | review-contratos | handoff |
| Cardinalidade e performance de query | review-queries | handoff |
| Teste que verifica o log ou a métrica | test-audit | handoff |
| Comentário no código | review-comentarios | ignorar |

PII em log, em trace e em analytics pertence a esta skill. O review-seguranca só referencia.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` e o reference de cada tecnologia detectada, entre `typescript.md`, `react.md`, `nestjs.md`, `node.md`, `llm-sdks.md`, `python.md`. Registre em `stack_references_loaded`.
3. Obtenha o diff. Com context packet do orquestrador, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged. `--path` restringe por glob.
4. Descubra o que o repo já usa: logger, bootstrap de OTel e APM (`instrumentation.ts`, `newrelic.js`, `Sentry.init`), middleware de request id, dicionário de eventos de analytics, nomes de métricas existentes. Revise contra esse padrão local.
5. Analise cada hunk com rota, handler, job, consumidor, chamada externa, `catch`, `track(...)` ou chamada de LLM. Para cada um, pergunte: que sinal sai daqui, com que contexto, para qual sistema, e que dado pessoal vai junto?
6. Verifique o contexto. Abra o middleware global (redação de log, filter de exceção que já reporta), o bootstrap do tracer (auto-instrumentação já cobre HTTP e AMQP?) e o wrapper de analytics.
7. Classifique severidade e confiança com a rubrica abaixo e a global.
8. Emita no output contract: bloco JSON e depois markdown. Prefixo dos ids: `OBS`. Máximo de ~15 achados.

Standalone: mostre o markdown no final. Não altere código.

## Rubrica de severidade do tema

**BLOCKER**
- Token, `Authorization`, cookie ou senha indo para log, trace ou analytics.
- PII direta de aluno (CPF, e-mail, nome com nota, caso clínico) logada em `info`/`error` em rota de produção.
- Prompt completo de LLM com dado de aluno enviado a log sem redação.

**MAJOR**
- Label de métrica com `userId`, e-mail ou URL com id: explosão de cardinalidade.
- Rota ou job de fluxo financeiro ou de matrícula novo sem métrica de erro, log de falha ou alerta.
- `traceparent` não propagado em novo cliente HTTP ou publisher de fila, quebrando o trace do fluxo principal.
- Evento de analytics disparado em `useEffect` sem guard: contagem inflada de um funil usado em decisão.
- Chamada de LLM sem registro de tokens e modelo em feature de custo relevante.
- Ação sensível (alterar nota, cancelar matrícula) sem audit log.

**MINOR**
- `console.log` onde o repo tem logger.
- `logger.error` para erro de validação esperado.
- Mensagem de log interpolada sem campos estruturados.
- `captureException` sem tags de rota e tenant.
- Nome de evento fora do padrão do repo.

**NIT**
- Nome de métrica sem sufixo de unidade.
- Ordem de campos no objeto de log.

## Heurísticas anti-falso-positivo

- Confirme o redator global (`pino` `redact`, filtro no `winston`, `beforeSend` do Sentry, `Interceptor` de log) antes de reportar PII. Se ele cobre o campo, não reporte.
- Auto-instrumentação do OTel e do New Relic já cria span de HTTP, DB e AMQP. Confirme o bootstrap antes de pedir span manual.
- `console.log` em script de migração, CLI e teste não se reporta.
- Log de `userId` interno opaco (UUID) é pseudonimizado. Reporte só se o id for CPF, matrícula pública ou e-mail.
- `logger.error` em exceção realmente inesperada (5xx) está correto.
- Label de baixa cardinalidade (status, método, rota templatizada, nome de feature) vale.
- Em dev/staging com gate `window.env.ENVIRONMENT !== 'prod'`, log de depuração é aceitável.
- Duplicidade de erro entre filter global e `captureException` com tags novas pode ser deliberada. Verifique `beforeSend`/dedupe antes.
- Em analytics, `StrictMode` só duplica em dev. Confirme se o disparo duplica também em produção (remontagem real, deps instáveis) antes de elevar a MAJOR.
- Confiança baixa exige dizer o que confirmaria (config do logger, bootstrap do tracer, painel).

## Ferramentas determinísticas opcionais

Rode só se instaladas. Nunca instale. A saída é insumo.

- `eslint` com `no-console` e `eslint-plugin-no-secrets`, quando já configurados. Verificar: `ls node_modules/.bin/eslint`. Executar: `npx eslint --rule '{"no-console":"warn"}' <arquivos do diff>`.
- `gitleaks detect --no-git --source <path>` para segredo em log fixture (verificar: `command -v gitleaks`). Segredo no código é do review-seguranca.
- `semgrep --config <regras do repo> <path>` quando houver regras de logging local.
- Python: `ruff check --select T20,G,LOG,TRY400 <arquivos>` (`print`, formatação de logging, `logger.error` com `exception`). Verificar: `command -v ruff`.
- `grep -rnE "console\.(log|debug)|logger\.(info|debug)\(.*(body|headers|req\b|user\b|email|cpf|token)" <arquivos do diff>` como triagem. Cada hit exige leitura do contexto.

## Exemplos

### Achado 1

```
### [BLOCKER] OBS-001 — Header Authorization e e-mail do aluno logados em cada request
**Onde:** pos-gateway/src/middleware/request-logger.ts:14-22 · **Confiança:** alta · **Esforço:** S
**Evidência:**
logger.info({ headers: req.headers, body: req.body, user: req.user }, 'request received');
**Problema:** `req.headers` carrega `authorization` e `cookie`. `req.user` inclui e-mail e CPF. Todo request grava o bearer token e dado pessoal no log de produção, com retenção do pipeline. Quem lê o log pode reutilizar o token. O tratamento fere a LGPD (dado pessoal fora da finalidade).
**Correção:**
logger.info({
  requestId: req.id,
  method: req.method,
  route: req.route?.path,
  userId: req.user?.id,
}, 'request received');
// redact global no logger
const logger = pino({ redact: ['req.headers.authorization', 'req.headers.cookie', '*.email', '*.cpf'] });
```

### Achado 2

```
### [MAJOR] OBS-002 — Label de métrica com id do aluno
**Onde:** pos-api/src/metrics/enrollment.metrics.ts:9-17 · **Confiança:** alta · **Esforço:** S
**Evidência:**
enrollmentDuration.labels({ userId: dto.userId, route: req.originalUrl, status }).observe(elapsed);
**Problema:** `userId` e `originalUrl` (com ids na URL) criam uma série por aluno e por rota-com-id. Com 20 mil alunos ativos, o Prometheus passa de 20 mil séries nessa métrica e o custo e a latência de consulta sobem. O histograma deixa de ser consultável.
**Correção:**
enrollmentDuration.labels({ route: req.route.path, status }).observe(elapsed); // '/enrollments/:id'
// o userId vai para o log e o span
span.setAttribute('app.user_id', hash(dto.userId));
```

### Caso que parece problema e NÃO se reporta

```ts
logger.info({ enrollmentId, userId: user.id, durationMs }, 'enrollment.created');
```

O arquivo está sujeito ao logger com `redact` global. `user.id` é UUID opaco, sem relação direta com a pessoa fora do sistema. A mensagem é estável e os campos são estruturados. O nível `info` cobre evento de negócio. Nenhum dado pessoal sai e o contexto existe.
