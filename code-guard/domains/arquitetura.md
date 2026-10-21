# Domínio: arquitetura

- [ARQ] Nada de cron em processo, lock em memória ou cache local sem invalidação para recurso compartilhado: o código roda em várias réplicas. — origem: review-arquitetura/escalabilidade
- [ARQ] Estrutura que cresce com usuários ou dados tem limite: paginação, lote ou processamento assíncrono. — origem: review-arquitetura/escalabilidade
- [ARQ] Problema que o repo já resolve usa o mesmo mecanismo (client, config, erro, paginação, fila, estado). — origem: review-arquitetura/conformidade
- [ARQ] Dependência ou padrão novo entra com ADR curto: por que, alternativas, equivalente que já existe no repo. — origem: review-arquitetura/dependencia-nova
- [ARQ] Desenho do tamanho do requisito: sem abstração genérica para um único uso, sem configuração para variação que ninguém pediu. — origem: review-arquitetura/tamanho-da-solucao
- [ARQ] Job e processamento em lote dimensionados para o volume que a spec prevê. — origem: review-arquitetura/escalabilidade
