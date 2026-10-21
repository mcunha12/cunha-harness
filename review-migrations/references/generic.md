# Migrations: regras agnósticas de banco e ORM

## Modelo mental de deploy

Três fatos governam toda migration.
1. Código antigo e código novo servem tráfego ao mesmo tempo durante o deploy (rolling update, canary, blue/green com banco compartilhado). Duração típica: 1 a 15 minutos.
2. A migration roda antes (preDeployHook, job de release) ou depois (boot da app, passo manual) do código. Descubra qual. Migration que roda antes precisa ser compatível com o código antigo. Migration que roda depois precisa que o código novo tolere o schema antigo.
3. Rollback de código é rápido e rollback de dado não existe. Toda migration destrutiva precisa de backup verificado, e toda migration de expand precisa funcionar com o código da versão anterior.

Pergunta de revisão por statement: "se o código da versão anterior rodar contra este schema, o que quebra? Se o código novo rodar contra o schema anterior, o que quebra?"

## Tabela de compatibilidade

| Operação | Código antigo contra schema novo | Segurança |
|---|---|---|
| ADD COLUMN nullable | funciona | seguro |
| ADD COLUMN NOT NULL sem default | INSERT falha | expand em duas etapas |
| ADD COLUMN NOT NULL com default constante | funciona | seguro em PG ≥ 11 e MySQL 8 INSTANT |
| DROP COLUMN usada | SELECT/INSERT falham | contract em deploy posterior |
| RENAME COLUMN/TABLE | tudo falha | expand/contract |
| ALTER TYPE da coluna | cast/falha, rewrite | coluna nova + backfill |
| ADD INDEX | funciona | lock e duração por motor |
| DROP INDEX | funciona, queries podem ficar lentas | confirmar que nenhuma query usa |
| ADD CONSTRAINT (UNIQUE/CHECK/FK) | INSERT que viola falha | NOT VALID + VALIDATE, dedup prévio |
| SET NOT NULL | INSERT sem a coluna falha | backfill + código novo antes |
| ADD valor de ENUM | funciona se o código antigo não lê o valor | handoff contratos |
| DROP/RENAME valor de ENUM | quebra | recriar tipo em fases |
| ADD TABLE | funciona | seguro |
| DROP TABLE | tudo que usa falha | contract em deploy posterior |

## Plano em fases (template)

Use este formato no `fix` quando a mudança é incompatível numa só etapa.

```
Deploy 1 (expand): migration ADD COLUMN nova NULL. Código escreve nas duas colunas e lê da antiga.
Backfill: job em lotes de 5k, WHERE nova IS NULL, pausa de 200 ms, valida COUNT(*) WHERE nova IS NULL = 0.
Deploy 2: código lê da nova e continua escrevendo nas duas.
Deploy 3 (contract): código para de escrever na antiga. Migration DROP COLUMN antiga (após uma janela de rollback acordada).
```

Cada fase é reversível sem perda de dado até o contract.

## Backfill: contrato mínimo

- Roda fora da migration de schema (job, script, comando administrativo).
- Lotes de tamanho fixo, com limite superior de tempo por lote (alvo ≤ 1 s) e `COMMIT` por lote.
- Pausa entre lotes ou controle por lag de réplica. Em Postgres: `pg_stat_replication.replay_lag`. Em MySQL: `Seconds_Behind_Master`.
- Idempotente: o filtro (`WHERE col IS NULL` ou cursor por chave primária) permite reexecutar.
- Retomável: guarda o cursor (último id) ou usa o filtro.
- Ordena por chave indexada. `ORDER BY` sem índice reescaneia.
- Medido: loga linhas processadas e restantes.
- Validação final antes da constraint.
- Evite `UPDATE` sem `WHERE` em tabela grande: gera bloat, WAL e travas de linha longas.
- Backfill que lê da mesma tabela que atualiza usa `SKIP LOCKED` ou lotes por faixa de id para não competir com o tráfego.

## Reversibilidade

- Classifique: reversível sem perda (ADD COLUMN, ADD INDEX), reversível com perda dos dados novos (DROP da coluna recém criada), irreversível (DROP, TRUNCATE, UPDATE destrutivo, narrowing de tipo).
- Irreversível exige: snapshot/backup recente (PITR ou dump) com data no PR, e aprovação explícita do dono do dado.
- Migration sem `down` (Prisma, Flyway versioned) exige plano de rollback descrito no PR: SQL inverso ou roll forward.
- Down que reexecuta `DROP` em coluna com dados de produção perde dado. O `down` precisa avisar.

## Migration de dados

- SQL puro. Sem import de model da aplicação, sem chamada a serviço, sem rede.
- Declare as tabelas/colunas usadas dentro da migration. O model da aplicação muda e a migration histórica precisa continuar executável do zero.
- Determinismo: sem `now()`/`random()` no dado migrado quando a migration precisa produzir o mesmo resultado em ambientes diferentes.
- Dedup antes de unique. Documente qual registro vence.
- Dado pessoal copiado ou transformado: finalidade e retenção (handoff review-seguranca).
- Migration roda do zero em banco vazio (CI, ambiente novo, testes de integração). Dependência de dado pré-existente (`UPDATE ... WHERE id = 42`) quebra o replay.

## Seeds

- Seed de produção só com dado de referência, idempotente (`ON CONFLICT DO NOTHING`, `upsert`), com ids estáveis.
- Usuário admin, senha, token ou dado de teste em migration: BLOCKER.
- Seed fora do runner de migrations, por ambiente.

## Tempo e timezone

- Guarde instante em tipo com zona (`timestamptz`, `DATETIME` em UTC com convenção documentada). `timestamp` sem zona é aceitável para "hora de parede" (horário de aula local) e o nome da coluna deve dizer isso.
- Conversão de tipo de data sem `USING ... AT TIME ZONE` assume a zona da sessão.
- Default `now()` em coluna sem zona grava a hora local da sessão.
- Backfill de data com `CURRENT_DATE` varia com o fuso do servidor.

## Precisão e escala

- Dinheiro: `numeric(p,s)` ou inteiro em centavos. Nunca `float`.
- `int` (2^31) em tabela de evento/log/progresso: `bigint`. Mudar depois reescreve a tabela e quebra FKs.
- Strings: `text` (Postgres) ou `varchar(n)` com n justificado. Reduzir `n` falha com dado existente.
- Booleano tri-estado (`NULL`) é decisão consciente. `NOT NULL DEFAULT false` em coluna nova segue expand em duas fases quando o motor reescreve.

## Integridade

- A regra de negócio que o código garante e o banco pode garantir vai para o banco (`UNIQUE`, `FK`, `CHECK`, `NOT NULL`). Dois requests concorrentes burlam a checagem de aplicação.
- Constraint nova em tabela populada: valide dados antes (query de contagem de violações no PR).
- `ON DELETE CASCADE` em histórico, auditoria e dado financeiro: apagar o pai apaga o filho.
- Índice na coluna filha de FK. O `DELETE` no pai varre a filha sem ele.
- Nome explícito para constraint e índice. Nome gerado difere entre ambientes e dificulta `DROP`.

## Sinais de runner e fluxo

- Migration editada depois de aplicada em qualquer ambiente: checksum falha. Crie migration nova.
- Duas migrations paralelas na mesma base (heads múltiplos, números iguais): defina ordem e dependência.
- Migration que roda no boot da aplicação com várias réplicas: exige lock de migration (advisory lock) e aceita falha de boot em loop quando a migration falha.
- Migration com tempo > timeout do job de deploy: parcialmente aplicada. Cheque transacionalidade e idempotência.
- `IF NOT EXISTS` / `IF EXISTS` em tudo mascara drift entre ambientes. Use em migration manual idempotente e evite como padrão.

## Perguntas que o PR deve responder

Se o PR não responde e o diff não mostra, escreva a pergunta no `problem` e reduza a confiança.
1. Qual o volume da tabela e o tráfego de escrita?
2. Qual versão do banco?
3. Como e quando a migration roda no deploy?
4. Qual o plano de rollback?
5. Quais outros serviços leem ou escrevem essa tabela?
6. A mudança é compatível com o código da versão anterior?

## Severidade: calibragem do tema

- BLOCKER: perda de dado, indisponibilidade provável (lock exclusivo longo em tabela quente), quebra do código antigo durante o deploy, config destrutiva em produção.
- MAJOR: lock de escrita provável, backfill em transação única, falta de plano de rollback em operação destrutiva, migration acoplada a model.
- MINOR: tipo ou default subótimo sem risco imediato, down ausente em operação trivial.
- Volume desconhecido: um nível abaixo e `confidence: media`.
