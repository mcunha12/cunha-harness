# Migrations em Python (Alembic, Django, SQLAlchemy)

## Alembic

- **Autogenerate sem revisão.** `alembic revision --autogenerate` compara o metadata com o banco e erra: não detecta rename (gera `drop_column` + `add_column`: perde dado), ignora mudança de `server_default` sem `compare_server_default=True`, ignora enum e CHECK em vários casos, gera `drop_table` para tabela que o metadata não importa, traz diferenças alheias ao PR. Leia o script gerado linha a linha.
- **Rename.** Troque `drop_column`+`add_column` por `op.alter_column('t', 'velho', new_column_name='novo')` e use expand/contract quando há tráfego.
- **`downgrade()`.** Vazio (`pass`) ou que não desfaz o `upgrade()`. Exija o inverso, ou um `raise NotImplementedError("irreversível: ...")` explícito em migration destrutiva.
- **Heads múltiplas.** Dois PRs criam revisões com o mesmo `down_revision`: `alembic heads` mostra mais de uma. Correção: `alembic merge` e uma ordem decidida. Verifique `down_revision` do arquivo novo contra a head da base.
- **Transação e CONCURRENTLY.** O Alembic envolve em transação (Postgres, DDL transacional). `CREATE INDEX CONCURRENTLY` exige `with op.get_context().autocommit_block():` e `postgresql_concurrently=True` em `op.create_index`. Sem isso, falha em runtime. `transaction_per_migration = true` isola cada revisão.
- **Locks.** `op.add_column(... nullable=False)` sem `server_default` em tabela com dados falha. `op.alter_column(type_=...)` reescreve. `op.create_foreign_key` e `op.create_check_constraint` sem `postgresql_not_valid=True` varrem a tabela: use `op.execute("ALTER TABLE ... NOT VALID")` e `VALIDATE`. `op.execute("SET lock_timeout = '3s'")` no começo.
- **Backfill.** `op.execute("UPDATE ...")` na mesma revisão do DDL: transação única. Mova para script/job em lotes. Em dados pequenos e controlados, aceitável com `WHERE`.
- **Imports de model.** `from app.models import X` dentro da migration acopla o histórico ao código atual. Declare `sa.table('x', sa.column('id'), ...)` inline e use `op.bulk_insert` ou `op.execute(sa.update(...))`.
- **Enum.** `op.execute("ALTER TYPE ... ADD VALUE 'x'")` precisa de `autocommit_block()` em PG < 12 e o uso do valor só após commit. `sa.Enum(..., name=...)` com `create_type`: `downgrade` precisa dropar o tipo (`DROP TYPE`).
- **Online e offline.** `alembic upgrade head --sql` gera SQL sem executar. A migration que usa `op.get_bind()` para ler dados não funciona em modo offline. Aceitável quando o time só roda online, mas anote.
- **`env.py`.** `compare_type=True` e `compare_server_default=True` revelam mais drift. Alteração em `env.py` que afeta `target_metadata` altera o autogenerate: revise.
- **Convenção de nomes** (`naming_convention` no `MetaData`): sem ela, constraints ganham nomes aleatórios e `drop_constraint` precisa do nome real.
- **Concorrência de execução.** `alembic upgrade head` no boot de N réplicas sem lock: use job único ou advisory lock.

## Django

- **`makemigrations` automático.** Revise `RemoveField`, `RenameField` (o Django pergunta, mas `RemoveField` + `AddField` aparece quando o prompt é respondido "não"), `AlterField` (tipo, null, default).
- **Lock e rewrite.** `AddField` com `default=` e `null=False` em Postgres ≥ 11: instantâneo para default constante. Default callable (`default=uuid.uuid4`, `timezone.now`) calcula um único valor para todas as linhas no momento da migration e grava constante: o dado difere do esperado e o `db_default` (Django 5) é o modo certo para default de banco. `AlterField` de tipo reescreve. `AddIndex` sem concurrency bloqueia escrita.
- **Índice concorrente.** `django.contrib.postgres.operations.AddIndexConcurrently` / `RemoveIndexConcurrently` com `atomic = False` na classe `Migration`. `AddConstraintNotValid` e `ValidateConstraint` para CHECK/FK sem lock longo.
- **`RunPython`.** Sem `reverse_code` (ou `migrations.RunPython.noop` quando válido) impede `migrate app 0003` para trás. Use `apps.get_model('app', 'Model')` (model histórico). `from app.models import X` quebra quando o model mudar. Backfill dentro de `RunPython` roda em transação única (`atomic = True`): para tabela grande, `atomic = False` e lotes com `.iterator(chunk_size=...)`/`bulk_update(batch_size=...)`.
- **`RunSQL`.** Sem `reverse_sql`. SQL com `CONCURRENTLY` exige `atomic = False`.
- **`SeparateDatabaseAndState`.** Usado para renomear sem tocar o banco ou para tirar do estado sem dropar. Revise com cuidado: estado e banco divergem de propósito.
- **Squash e dependências.** `dependencies` e `replaces` corretos. Conflito `0004_a` e `0004_b` de dois PRs: `makemigrations --merge`.
- **Migration em app de terceiros** (`dependencies = [('auth', '__latest__')]`): trava atualização.
- **`CharField(max_length)` menor.** Falha com dado existente.
- **`ForeignKey` com `on_delete=CASCADE` em histórico.** Confirme a intenção.
- **`unique=True` em coluna populada.** Falha se houver duplicata: dedup antes.
- **`managed = False`** e views/tabelas externas: o Django não cria nem remove.
- **Comandos úteis.** `python manage.py sqlmigrate app 0005` mostra o SQL que roda. `makemigrations --check --dry-run` falha quando o model diverge das migrations (drift).

## SQLAlchemy (fora do Alembic)

- `Base.metadata.create_all(engine)` em produção ou no boot da app: cria tabelas ausentes e não altera as existentes. Substitui migration e esconde drift. MAJOR.
- `drop_all()` em código que roda fora de teste: BLOCKER.
- `engine.execute(text(f"..."))` com f-string em migration: SQL injection e acoplamento. Parâmetros nomeados.
- Sessão e transação: `with engine.begin()` por migration.
- Modelo declarativo importado dentro de revisões antigas: acopla ao código atual.

## Dados, tempo, tipos

- `sa.DateTime()` sem `timezone=True` (Alembic/SQLAlchemy) gera `timestamp without time zone`. Para instante, `sa.DateTime(timezone=True)`. Django: `USE_TZ = True` com `DateTimeField` gera `timestamptz` em Postgres.
- `sa.Float` para dinheiro: `sa.Numeric(12, 2)` ou inteiro em centavos.
- `sa.Integer` em PK de tabela de alto crescimento: `BigInteger`.
- `server_default=sa.func.now()` e `default=datetime.utcnow` (do Python): o primeiro vale para insert por SQL, o segundo só para ORM.
- `server_default='false'` em booleano: use `sa.false()` / `sa.text('false')` (string `'0'`/`'false'` varia por dialeto).

## Falsos positivos frequentes

- `downgrade` ausente em projeto que declara política de roll forward documentada.
- `autogenerate` em migration que o autor revisou e editou (o script não tem os padrões de drop+add).
- `op.add_column(... nullable=True)`: seguro.
- `RunPython` pequeno em tabela de domínio (dezenas de linhas) em transação única.
- `AddIndex` comum em tabela criada na mesma migration.
- `default=` Python em `AddField` quando o objetivo é um valor constante e a tabela é pequena.
