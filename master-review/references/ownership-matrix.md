# Ownership matrix

Quando um tema cai na fronteira, o dono reporta e os outros só referenciam via `handoffs`.

| Tema na fronteira | Dono | Quem só referencia |
|---|---|---|
| Regra de negócio duplicada | review-dry | review-modularidade |
| Tipo redeclarado em vez de derivado | review-tipagem | review-dry |
| IDs intercambiáveis (branded types) | review-tipagem | review-clean |
| Value object / primitive obsession conceitual | review-clean | review-tipagem |
| Naming, complexidade cognitiva, fluxo | review-legibilidade | review-clean |
| SRP/smells em função/classe | review-clean | review-legibilidade |
| Fronteiras entre módulos, camadas e repos, DIP entre camadas, ciclos | review-modularidade | review-clean |
| Shotgun surgery | review-modularidade | review-dry |
| Shape de dados entre serviços, breaking changes, validação de entrada | review-contratos | review-tipagem |
| SQL injection, XSS, SSRF, authZ | review-seguranca | review-queries, review-front |
| Segredos no código/bundle | review-seguranca | review-observabilidade |
| PII em logs/telemetria | review-observabilidade | review-seguranca |
| Timeouts, retry, idempotência, erros engolidos | review-resiliencia | review-contratos, review-queries |
| N+1, índices, fan-out sequencial, cache | review-queries | review-front (fetch no client) |
| Re-render, bundle, Web Vitals, effects | review-front | review-legibilidade |
| Semântica, teclado, ARIA, contraste | review-a11y | review-front |
| Prompt injection, output do LLM, custo de tokens | review-ia | review-seguranca, review-observabilidade |
| Instrumentação de chamadas LLM (tokens, latência) | review-observabilidade | review-ia |
| DDL, locks, backfill, expand/contract | review-migrations | review-queries |
| Comentários | review-comentarios | todos |
| Testes | test-audit (existente) | todos |

Tema ausente da tabela: o agente cujo `description` cobre o tema de forma mais estreita é o dono. Empate: o orquestrador decide e registra.
