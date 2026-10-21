# DRY em Prisma, SQL e Postgres

## Prisma

- Sinal: o mesmo `select`/`include` em 3+ chamadas (`findMany`, `findUnique`, `findFirst`).
- Correção: `Prisma.validator<Prisma.XSelect>()({...})` ou `satisfies Prisma.XSelect` exportado, mais `Prisma.XGetPayload<{ select: typeof xSelect }>` para o tipo. O tipo de retorno deriva do `select`.
- Sinal: filtro de soft delete ou tenant repetido nas chamadas. Correção: `$extends` com `query` que injeta o filtro, ou método de repository com o `where` base. Uma cópia sem o filtro é MAJOR ou BLOCKER conforme o dado exposto.
- Sinal: lógica de `upsert` com a mesma chave composta escrita em 3 services. Correção: método de repository nomeado.
- Sinal: `PrismaClient` instanciado em mais de um módulo. Duplica conexões. O dono do tema é review-queries. Aqui só se referencia.

## Schema versus código

- Sinal: enum no `schema.prisma` e union de strings escrito à mão no código. Correção: importe o enum do `@prisma/client`, ou derive o union dele.
- Sinal: valor default de coluna (`@default(7)`) e a mesma constante no código. A regra tem 2 fontes. Correção: o banco guarda o default estrutural, o domínio guarda a regra de negócio. Escolha um dono e cite no código.
- Sinal: CHECK constraint no banco e a mesma validação no service com limite diferente. Reporte a divergência.

## SQL e views

- Sinal: o mesmo `CASE WHEN` de classificação (status de matrícula, faixa de nota) em 3+ queries SQL ou views.
- Impacto: relatórios com números diferentes para a mesma métrica.
- Correção: view ou função SQL (coluna gerada, `GENERATED ALWAYS AS ... STORED`) com a regra. Consumidores leem da view. Mudar a view exige avaliar dependentes.
- Sinal: query bruta duplicada entre o app e um job de relatório. Correção: view materializada ou função compartilhada, com ordem de migração (review-migrations).

## Migrations

- Sinal: o mesmo bloco de backfill ou a mesma lista de valores em 2 migrations. Aceitável: migrations são históricas e imutáveis. Não reporte duplicação entre migrations já aplicadas.

## Anti-DRY

- Sinal: repository genérico `BaseRepository<T>` com `find(options: any)` que repassa `where` livre. Perde tipagem do Prisma e esconde os filtros obrigatórios.
- Correção: repositories por agregado, com métodos nomeados por caso de uso.
