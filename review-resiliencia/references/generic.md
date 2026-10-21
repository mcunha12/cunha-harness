# Resiliência — regras agnósticas de stack

Cada seção traz sinal, impacto e correção. Use junto com o reference da tecnologia.

## 1. Orçamento de tempo

- Toda chamada de rede tem timeout de conexão e timeout total. Sem os dois, o default da biblioteca vale, e o default costuma ser infinito.
- O timeout interno é menor que o externo. Rota com SLA de 10 s: chamada A com 3 s, chamada B com 3 s, margem de 4 s. Soma dos timeouts sequenciais maior que o SLA da rota sinaliza orçamento quebrado.
- Propague o deadline restante em vez de reiniciar o relógio a cada salto. Header `X-Request-Deadline`, `grpc-timeout` ou `AbortSignal.any([...])`.
- Cancele o trabalho quando o cliente desiste (`AbortController`, `req.on('close')`, `context.Context`, `asyncio.timeout`). Trabalho sem dono consome capacidade.

Correção típica (pseudo-código):

```
remaining = deadline - now()
if remaining <= 0: fail_fast(DeadlineExceeded)
call(dep, timeout = min(remaining, per_call_cap))
```

## 2. Retry

Retry só vale com as cinco condições juntas:

1. O erro é transitório: rede, 502/503/504, 408, 429, deadlock detectado, serialization failure.
2. A operação é idempotente, ou carrega idempotency key.
3. O intervalo cresce de forma exponencial com jitter completo: `sleep = random(0, min(cap, base * 2^n))`.
4. Há número máximo de tentativas e orçamento total de tempo.
5. Só uma camada da pilha faz retry.

Sinais de problema:

- `while (true)` com `try/catch` e `sleep` fixo.
- Retry em `catch` genérico, sem olhar o tipo do erro.
- Retry que ignora `Retry-After` de 429 e 503.
- Retry em POST sem chave. Efeito: duplicata de cobrança, matrícula, e-mail.
- Retry no cliente HTTP, no wrapper do serviço e no job: amplificação multiplicativa. 3 tentativas em 3 camadas dão até 27 chamadas ao dependente já degradado.
- Retry de operação que falhou por timeout sem saber se o servidor concluiu. Sem idempotência, duplica.

## 3. Idempotência

- Chave de idempotência nasce no originador, uma vez, fora do laço de retry. Chave gerada dentro do retry vale zero.
- O receptor grava a chave junto com o efeito, na mesma transação, com unique constraint. Reenvio devolve o resultado original.
- Operações naturalmente idempotentes (`PUT` absoluto, `DELETE`, `upsert` por chave natural, `SET x = 5`) dispensam chave. `x = x + 1` e `INSERT` sem chave natural precisam dela.
- Handler de evento (fila, webhook, cron com sobreposição) assume entrega duplicada e fora de ordem. Dedup por `eventId`; compare `version` ou `updatedAt` para descartar evento velho.

## 4. Fila e mensageria

- `ack` só depois do efeito durável. `ack` antes do processamento perde mensagem quando o processo cai.
- Erro permanente (payload inválido, entidade inexistente) vai para DLQ no primeiro erro. Erro transitório volta com atraso (retry-queue com TTL) e contador.
- `requeue` imediato e sem contador forma loop infinito (poison message).
- Defina `prefetch`/concurrency. Sem limite, um consumidor lento acumula mensagens não confirmadas na memória.
- DLQ sem alerta e sem procedimento de reprocessamento é lixeira. Pergunte quem monitora.
- Ordem: a garantia de ordem vale por fila e consumidor único. Com N consumidores, o código assume desordem.

## 5. Consistência entre sistemas

- **Dual write**: escrita no banco seguida de publicação de evento ou chamada HTTP, sem atomicidade. Falha entre os dois deixa os sistemas divergentes. Correção: transactional outbox (grava evento na mesma transação, relay publica), ou CDC.
- **Saga**: cada passo de escrita tem compensação definida. O passo irreversível (cobrança, e-mail, certificado) vai por último.
- **Check-then-act**: leitura que decide e escrita separada. Correção: constraint unique, `INSERT ... ON CONFLICT`, `UPDATE ... WHERE estado = 'esperado'` com checagem de linhas afetadas, optimistic locking por `version`, lock advisory.
- **Leitura após escrita em réplica**: lê da réplica logo depois de gravar na primária e não enxerga o dado. Correção: ler da primária na janela, ou devolver o dado na própria escrita.
- **Cache e banco**: invalidar depois de gravar, com TTL como rede de segurança. Gravar no cache antes do commit expõe dado que pode sofrer rollback.

## 6. Proteção contra cascata

- **Circuit breaker**: abre após taxa de falha ou lentidão acima do limiar, falha rápido, testa meia-abertura. Aplique em dependência crítica, de latência variável, com volume relevante.
- **Bulkhead**: pool, semáforo ou fila separados por dependência. Uma dependência lenta não consome o pool de todas.
- **Load shedding e rate limit na entrada**: rejeite com 429/503 e `Retry-After` quando a fila interna passa do limite. Aceitar tudo enche a memória e derruba o processo.
- **Fila ilimitada** em memória (array, canal sem buffer máximo, `Promise` acumulada): vira OOM sob pico.
- **Stampede**: cache que expira junto para muitos clientes. Correção: jitter no TTL, single-flight, stale-while-revalidate. O desenho do cache é do review-queries; aqui entra o efeito de falha em cascata.

## 7. Degradação graciosa

- Classifique cada dependência de uma rota: essencial ou opcional.
- Opcional falhou: devolva o resto com marcador explícito (`degraded: ['recommendations']`) e métrica. Fallback silencioso mascara indisponibilidade.
- `stale-on-error`: sirva o último valor bom do cache quando a origem falha, com limite de idade.
- Fallback não pode ser mais perigoso que a falha. Permissão que falha aberta ("se o serviço de auth não responde, libera") é decisão de segurança e vira handoff.
- Todo fallback temporário ou mockado fica atrás de gate de ambiente explícito. Fallback fake que vai a produção é BLOCKER.

## 8. Erros — modelagem

- Hierarquia pequena: erro de domínio (esperado, 4xx, sem retry), erro de dependência (transitório, 5xx, com retry), erro de programação (bug, 500, alerta).
- Um ponto central converte erro em resposta (exception filter, error middleware, handler global).
- `cause` preservada em toda conversão.
- Mensagem ao usuário estável e sem detalhe interno. Detalhe técnico vai ao log com o correlation id.
- Código de erro estável (`ENROLLMENT_CLOSED`) para o cliente decidir. O desenho do shape do erro é do review-contratos.
- Resultado explícito (`Result`, union discriminada, retorno `(value, err)`) para falha esperada que o chamador deve tratar. Exceção para o inesperado.

## 9. Partida, parada e saúde

- Valide configuração e conectividade essencial no boot, com falha rápida e mensagem clara.
- `SIGTERM`: pare de aceitar trabalho novo, termine o em andamento até um prazo, feche conexões em ordem inversa à abertura, saia com código 0. O prazo fica abaixo do `terminationGracePeriodSeconds`.
- Consumidor de fila: cancele a assinatura antes de fechar o canal. Termine as mensagens em voo e só então confirme.
- Liveness responde "o processo trava?" e não consulta dependência. Readiness responde "posso receber tráfego?" e checa o que a rota essencial exige, com timeout curto e cache de poucos segundos.
- Startup probe separada quando o boot é lento. Evita matar o pod no aquecimento.
- Jobs agendados: lock distribuído ou unique para impedir execução concorrente de múltiplas réplicas. Execução tem timeout e é retomável.

## 10. Armadilhas de tratamento de erro

- `finally` com `return` ou `throw` sobrescreve o erro original.
- Erro lançado dentro do `catch` perde o primeiro se faltar `cause`.
- `Promise.race` com timeout que não cancela a operação original: o trabalho continua e consome recurso.
- `setTimeout` e `setInterval` com callback async sem catch.
- EventEmitter com `error` sem listener derruba o processo.
- Worker, stream ou child process sem handler de `error` e `close`.
- Exceção em callback de biblioteca que não propaga (ex.: handler de evento de terceiros) some silenciosamente.

## 11. Perguntas de verificação por chamada nova

1. Qual o timeout e de onde vem?
2. O que acontece se a resposta chegar depois do timeout?
3. Existe retry? Em qual camada? A operação é idempotente?
4. O que o chamador vê quando falha? Erro tipado ou valor "vazio"?
5. O que fica inconsistente se o processo cair entre esta linha e a próxima?
6. Qual recurso fica aberto no caminho de erro?
7. Quem é alertado quando falha de forma persistente?

Se o diff não responde a pergunta e o contexto também não, registre confiança media ou baixa e diga o que confirmaria.
