# Observabilidade — regras agnósticas de stack

Cada seção traz sinal, impacto e correção. Use junto com o reference da tecnologia.

## 1. Modelo mental

- Log descreve um evento discreto. Trace descreve o caminho de uma request. Métrica descreve o comportamento agregado. Erro monitorado agrupa falhas. Analytics descreve comportamento do usuário. Cada sinal responde uma pergunta diferente. O mesmo dado em todos os sinais gera custo sem ganho.
- Id de alta cardinalidade (usuário, request, entidade) vai para log e trace. Métrica recebe só dimensões finitas.
- Todo sinal carrega o mesmo `trace_id` e `service.name`, para correlacionar entre eles.

## 2. Log

Campos mínimos em log de produção:

| Campo | Exemplo | Observação |
|---|---|---|
| `timestamp` | ISO 8601 UTC | gerado pelo logger |
| `level` | `info` | enum fixo |
| `message` | `enrollment.created` | estável, sem variável |
| `service`, `env`, `version` | `pos-api`, `prod`, `1.42.0` | do bootstrap |
| `trace_id`, `span_id`, `request_id` | hex | do contexto assíncrono |
| `route`, `method`, `status`, `duration_ms` | `/enrollments/:id` | só em log de request |
| `user_id` | UUID | pseudonimizado |
| `err` | objeto com `type`, `message`, `stack` | só em erro, com `cause` |

Regras de nível:

- `fatal`: o processo vai encerrar.
- `error`: algo falhou e exige ação humana. Um `error` sem ação possível vira `warn`.
- `warn`: degradação tolerada, retry que recuperou, fallback usado.
- `info`: evento de negócio e ciclo de vida (boot, shutdown, job concluído, matrícula criada). Volume previsível por unidade de negócio.
- `debug`/`trace`: diagnóstico, desligado em produção.

Antipadrões:

- Mensagem como identificador (`User 123 not found`). Mensagem fixa e `user_id` em campo.
- Log dentro de laço por item. Agregue: `processed: 1200, failed: 3, failedIds: [...até 10]`.
- Log na entrada e na saída de toda função. Gera volume sem informação.
- Log de objeto inteiro (`req`, `user`, `err.response`, `config` do axios). Contém headers e tokens. Selecione campos.
- Mesmo erro logado em cada camada.
- Log como mecanismo de controle de fluxo ou como fila de auditoria.
- Mensagem em linguagem natural longa, sem campos, com stack trace em string multi-linha: quebra o parser. O stack vai em campo `err.stack`.

## 3. PII, segredos e LGPD

Dados a manter fora de log, trace, métrica e analytics:

- Identificadores diretos: CPF, RG, e-mail, telefone, nome completo, endereço, data de nascimento.
- Credenciais: senha, token (`Authorization`, `Cookie`, `Set-Cookie`, `x-api-key`), chave de API, string de conexão, código de verificação.
- Dado clínico, nota individual vinculada a pessoa identificada, conteúdo de prompt e de resposta de IA com dado de aluno.
- URL com token em query (`?token=`, `?code=`), pois URL é logada por proxy, APM e browser.

Correções:

- Allowlist: logue campos nomeados, nunca o objeto.
- `redact` no logger, no APM e no SDK de erro, com lista de caminhos (`*.email`, `req.headers.authorization`).
- Pseudonimização: `hash(salt + id)` quando o correlato é necessário.
- Truncamento e mascaramento: `***.***.***-12`.
- Regra de retenção separada para log de auditoria.
- Exceção deve ter base legal e finalidade, e o armazenamento deve ter controle de acesso.

Pergunta de verificação: se este log vazar para um terceiro, o que ele revela sobre uma pessoa?

## 4. Correlation e propagação

- Gere ou aceite `traceparent` (W3C Trace Context: `00-<trace-id>-<span-id>-<flags>`) na entrada. Armazene em contexto assíncrono. Injete em toda chamada de saída (HTTP, gRPC, mensagem) e em todo log.
- Fila: propague o contexto nos headers da mensagem. No consumidor, crie span com link para o produtor (`messaging.process`), pois o trace do produtor já terminou.
- Job agendado e CLI: crie trace raiz com nome do job.
- Serviço de borda devolve `x-request-id` na resposta para o suporte localizar a request.
- Baggage (`baggage`) só com dado não sensível e de baixa cardinalidade. Ele viaja para todos os serviços e terceiros.
- Contexto perdido: `setTimeout`, `setImmediate`, worker thread, `EventEmitter`, pool de conexões, `asyncio.create_task` sem copiar contexto, thread pool Python. Verifique se `AsyncLocalStorage`/`contextvars` sobrevive.

## 5. Spans

- Nome de span: baixa cardinalidade, `<verbo> <objeto>` (`GET /enrollments/:id`, `enrollments.create`, `publish enrollment.created`). Id no nome dobra o número de nomes.
- Atributos semânticos OTel: `http.request.method`, `http.route`, `http.response.status_code`, `db.system`, `db.operation.name`, `messaging.system`, `messaging.destination.name`, `rpc.service`. Atributos de negócio com prefixo do app (`app.course_id`).
- Erro: `span.recordException(err)` e `span.setStatus({ code: ERROR })`. Status HTTP 4xx de servidor não é erro de span, 5xx é.
- Span manual só onde a auto-instrumentação não cobre: trabalho interno relevante, chamada de SDK sem instrumentação, etapa de pipeline de IA. Span por função trivial gera ruído e custo.
- Sempre `end()` no `finally`.
- Atributo com valor de alta cardinalidade ou grande (corpo, SQL com literais): evite. Eventos de span (`addEvent`) para marcos curtos.

## 6. Métricas

- Método RED por serviço e por rota: `requests_total{route,method,status_class}`, `request_errors_total`, `request_duration_seconds` (histograma).
- Método USE por recurso: utilização, saturação, erro. Exemplos: pool de conexões (em uso, espera, timeout), fila (profundidade, idade do mais antigo, taxa de DLQ), event loop lag, GC pause, heap, descritores.
- Quatro sinais de ouro (Google SRE): latência, tráfego, erros, saturação. Separe latência de sucesso da latência de erro.
- Buckets de histograma alinhados ao SLO (por exemplo, 50 ms, 100 ms, 250 ms, 500 ms, 1 s, 2.5 s, 5 s, 10 s).
- Labels: finitos e conhecidos (`route` templatizado, `status_class`, `operation`, `provider`, `model`). Proibidos: ids, e-mail, URL crua, mensagem de erro, `stack`. Teste: o número de valores distintos tem teto fixo?
- Nome: `snake_case`, unidade no sufixo (`_seconds`, `_bytes`), `_total` em counter. Counter só cresce. Rates se calculam na consulta.
- Métrica de negócio por fluxo central, com contador de resultado (`enrollments_total{result="success|rejected|error"}`). Detecta falha lógica com HTTP 200.
- Heartbeat de job: `job_last_success_timestamp_seconds`. Alerta quando `time() - valor > intervalo * 2`.

## 7. Monitoramento de erro (APM, Sentry e similares)

- Ponto único de captura por erro: o filter global, a borda do consumidor, o error boundary. Captura manual extra só com contexto novo e com dedupe.
- Contexto: `release`, `environment`, `user.id` pseudonimizado, tags de baixa cardinalidade (rota, módulo, feature, tenant), `extra` curto.
- Erro esperado (validação, autenticação inválida, 404 de negócio, cancelamento do usuário) fica fora do monitoramento de erro. Vai para métrica.
- Agrupamento: fingerprint estável. Mensagem com id embutido fragmenta o grupo.
- Front-end: source maps enviados no CI, `release` alinhado ao build, `tracesSampleRate`/`replaysSessionSampleRate` explícitos, mascaramento de texto e inputs no replay.
- Alerta sobre erro novo, regressão e pico por release, com roteamento por dono.

## 8. Alertas, SLO e operação

- Todo fluxo crítico tem SLI (taxa de sucesso, latência p95/p99), SLO e alerta. Alerte por sintoma (taxa de erro, latência, idade da fila), não por causa (CPU de um pod).
- Alerta acionável: tem runbook, dono e threshold justificado. Alerta sem ação gera fadiga.
- Burn rate em duas janelas (rápida e lenta) para SLO.
- Dashboard por serviço com RED, saturação e dependências.
- Sampling: sempre amostre erros e traces lentos (tail-based). Head sampling uniforme a 1% perde o erro raro.
- Custo de telemetria: volume de log por request, cardinalidade, retenção por nível.
- Feature flag e experimento: logue/anote a variante servida para explicar diferenças de comportamento.

## 9. Auditoria

Registro de auditoria difere de log de aplicação.

- Cobre ações sensíveis: autenticação (sucesso e falha), mudança de permissão, nota e frequência, matrícula e cancelamento, impersonação, exportação em massa, acesso a dado clínico ou financeiro, mudança de configuração.
- Campos: `actor` (id e papel), `action`, `target` (tipo e id), `timestamp`, `origin` (IP, user agent, serviço), `before`/`after` ou diff mínimo, `result`, `reason` quando exigido.
- Append-only, com controle de acesso, retenção definida e separação do log operacional. A aplicação não edita nem apaga os próprios registros.
- Escrita do audit log na mesma transação da ação, ou outbox. Registro que pode falhar em silêncio perde a função.
- Minimização: grave ids e campos alterados, não o objeto inteiro com PII.

## 10. Analytics de produto

- Catálogo de eventos: nome, quando dispara, propriedades, dono. Nome no padrão do repo (verbo no passado, `snake_case` ou o que já existe).
- Um evento dispara uma vez por ação do usuário. Dispare no handler da ação, não em effect de render. Em effect, use guard de disparo único e deps estáveis.
- Propriedades: ids internos e categorias. PII fora. Valor constante em propriedade que deveria variar (por plataforma, por origem) distorce a análise.
- `identify`/`alias` uma vez por sessão, com id interno.
- Respeite consentimento e opt-out.
- Teste de contrato do evento (nome e payload) quando o spec define strings e payloads.
- Evento de alta frequência com throttle ou agregação no cliente.

## 11. Perguntas de verificação por mudança

1. O que o plantonista vê às 3h quando isto falha? Qual log, métrica, trace, alerta?
2. Esse sinal tem `trace_id` e contexto suficiente para achar a request?
3. Há dado pessoal ou segredo em algum sinal emitido aqui?
4. Existe métrica de sucesso e de erro do fluxo, em unidade de negócio?
5. A cardinalidade de cada label tem teto?
6. O erro é capturado uma vez, com contexto, e erros esperados ficam de fora?
7. A ação sensível deixa registro de auditoria?

Se a resposta depende de config fora do diff (redator global, bootstrap do tracer), use confiança media e diga o que confirmaria.
