# Domínio: observabilidade

- [OBS] Token, header `Authorization`, cookie e senha nunca vão para log, trace ou analytics. — origem: review-observabilidade/segredo-em-log
- [OBS] PII de usuário (documento, e-mail, nome com dado sensível) não entra em log de produção; use id interno ou redação. — origem: review-observabilidade/pii
- [OBS] Prompt de LLM com dado de usuário é redigido antes de ir para log. — origem: review-observabilidade/pii
- [OBS] Label de métrica tem cardinalidade baixa: nunca userId, e-mail ou URL com id. — origem: review-observabilidade/cardinalidade
- [OBS] Rota ou job novo de fluxo financeiro ou de matrícula nasce com métrica de erro, log de falha e alerta. — origem: review-observabilidade/rota-critica
- [OBS] Cliente HTTP e publisher de fila novos propagam `traceparent`. — origem: review-observabilidade/correlacao
- [OBS] Evento de analytics dispara uma vez por ação, com guard; nunca em `useEffect` sem controle. — origem: review-observabilidade/analytics
- [OBS] Chamada de LLM registra modelo, tokens e latência. — origem: review-observabilidade/llm
- [OBS] Ação sensível (alterar nota, cancelar matrícula, mudar permissão) grava audit log. — origem: review-observabilidade/audit-log
