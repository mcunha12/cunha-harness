# Domínio: migrations

- [MIG] Nunca `synchronize: true`, `db push` ou `migrate reset` em produção ou script de deploy. — origem: review-migrations/orm
- [MIG] Expand/contract: adicione o novo, migre o código, remova o antigo em outro deploy. Nunca `DROP` ou rename no mesmo PR que deixa de usar o objeto. — origem: review-migrations/expand-contract-rename
- [MIG] `ALTER COLUMN TYPE` e `SET NOT NULL` em tabela grande seguem o caminho sem lock longo (coluna nova + backfill + CHECK NOT VALID + VALIDATE). — origem: review-migrations/lock
- [MIG] Migration de dados tem `WHERE` verificável, roda em lote e tem plano de volta. — origem: review-migrations/migracao-de-dados
- [MIG] `CREATE INDEX CONCURRENTLY` em tabela com escrita contínua (fora de transação). — origem: review-migrations/lock-create-index-sem-concurrently
- [MIG] FK e CHECK em tabela grande entram com `NOT VALID` e são validados depois. — origem: review-migrations/constraint
- [MIG] DDL com lock exclusivo define `lock_timeout`. — origem: review-migrations/lock-timeout
- [MIG] Migration não importa models da aplicação; usa SQL ou o schema da própria migration. — origem: review-migrations/acoplamento
- [MIG] Migration destrutiva vem com plano de rollback escrito. Seed de admin ou senha nunca vai em migration de produção. — origem: review-migrations/rollback
