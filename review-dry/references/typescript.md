# DRY em TypeScript

## Unions, enums e constantes

- Sinal: `type Status = 'draft' | 'published'` declarado em 2 arquivos, ou um array `['draft','published']` ao lado de um union equivalente.
- Impacto: valor novo entra em um e não no outro. O `switch` exaustivo não protege entre declarações separadas.
- Correção: `const STATUSES = ['draft', 'published'] as const; type Status = typeof STATUSES[number];` e todos importam. Para validação em runtime, `z.enum(STATUSES)`.

## Tipos duplicados à mão

- Sinal: interface do mesmo recurso escrita no consumidor, quase igual à do produtor.
- Dono: tipo redeclarado em vez de derivado é de review-tipagem. Aqui reporte quando a cópia carrega regra (campos obrigatórios, limites, valores permitidos) que diverge. O restante vira handoff.

## Schemas zod

- Sinal: `z.object({...})` repetido para criar e atualizar com os mesmos campos; schema de formulário e schema de DTO paralelos.
- Correção: `base.extend({...})`, `base.partial()`, `base.pick({...})`, `base.omit({...})`. Um refinement de regra de negócio (`.refine`) fica no schema base.
- Sinal: regex de validação (e-mail, CPF, telefone) copiada em 3 arquivos. Correção: validador único exportado e testado.

## Funções puras de domínio

- Sinal: `calculateProgress`, `isEligible`, `computeDeadline` reimplementados com nomes diferentes (`getProgress`, `progressOf`). A busca por nome falha. Busque pela fórmula (`/ total`, `* 100`, `Math.round`).
- Correção: módulo de domínio com função pura e testes. Importado por quem precisa.

## Mappers e transformações

- Sinal: `.map((x) => ({ id: x.id, name: x.name, ... }))` idêntico em 2+ pontos; conversão snake_case para camelCase manual repetida.
- Correção: função `toX` nomeada, ao lado do tipo dono. Conversão de casing em massa pede função genérica única na borda (axios interceptor ou adapter), nunca campo a campo.

## Tipos utilitários e genéricos

- Sinal anti-DRY: genérico condicional (`T extends ... ? ... : ...`) criado para unificar 2 interfaces que divergem em 40% dos campos.
- Impacto: erros de tipo ilegíveis, custo de manutenção maior que a duplicação.
- Correção: duas interfaces explícitas com um `Pick` do núcleo comum.

## Barrel e re-exports

- Sinal: o mesmo helper reexportado por 2 barrels com nomes diferentes, e callers que importam dos dois caminhos.
- Correção: um caminho canônico. Fronteira de módulo é de review-modularidade.

## Armadilhas

- `Object.values(CONST)` e `Object.keys` para derivar listas: derive de uma só fonte, mas não duplique a tipagem. O tipo de `Map` criado de `Object.values(x as const)` herda chaves literais. Declare `new Map<string, string>(...)`. Reporte como cópia de forma quando o mapa repete o conteúdo de uma tabela existente.
- `enum` do TS e union de strings coexistindo para o mesmo conceito: escolha um.
