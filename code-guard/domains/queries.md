# Domínio: queries e performance de rota

- [QRY] Carregue relações em lote (include, join, `IN`). Nunca query dentro de loop sobre resultado. — origem: review-queries/QRY-DB-n-1
- [QRY] Toda listagem tem `take`/`limit`. Paginação de lista que cresce usa cursor, não `OFFSET` profundo. — origem: review-queries/paginacao
- [QRY] Chamada externa (HTTP, LLM) fica fora de transação de banco. — origem: review-queries/transacao-longa
- [QRY] Client de banco e pool são singletons. Nunca `new PrismaClient()` ou `new Pool()` por request. — origem: review-queries/pool
- [QRY] Nada síncrono e pesado no handler HTTP; PDF, relatório e lote vão para fila ou worker. — origem: review-queries/event-loop
- [QRY] Query nova em tabela grande tem índice que a atende (filtro e ordenação). — origem: review-queries/indice
- [QRY] Chamadas independentes vão com `Promise.all`. — origem: review-queries/QRY-HTTP-fan-out-sequencial
- [QRY] Escrita de muitos itens usa operação em lote. — origem: review-queries/escrita-em-loop
- [QRY] Cache tem TTL e chave com escopo de usuário quando o dado é do usuário. — origem: review-queries/cache
- [QRY] Sem `LIKE '%termo%'` ou função sobre coluna indexada em tabela grande; use busca textual ou índice funcional. — origem: review-queries/indice
