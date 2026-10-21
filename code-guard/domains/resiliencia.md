# Domínio: resiliência

- [RES] Todo catch relança o erro ou registra com contexto e decide o fallback de forma explícita. Nunca devolva `[]` ou `null` que a UI mostra como "sem dados". — origem: review-resiliencia/catch-engolido
- [RES] Toda promise em handler tem `await` ou `.catch`. Nada de floating promise. — origem: review-resiliencia/floating-promise
- [RES] Chamada HTTP a serviço externo tem timeout explícito. — origem: review-resiliencia/timeout
- [RES] Retry só em operação idempotente, com backoff, jitter e teto. POST de cobrança ou criação leva idempotency key. — origem: review-resiliencia/retry
- [RES] Consumidor de fila separa erro permanente de transitório; erro permanente vai para DLQ, sem requeue infinito. — origem: review-resiliencia/dlq
- [RES] Banco e evento no mesmo fluxo crítico usam outbox; nunca dual write. — origem: review-resiliencia/dual-write
- [RES] Recurso disputado (vaga, quota) tem unique constraint ou lock; nunca só check-then-act. — origem: review-resiliencia/concorrencia
