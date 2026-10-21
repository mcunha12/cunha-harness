# Comentários em TypeScript, JavaScript e JSX

## Sintaxe e extração

- `//` linha. `/* */` bloco. `/** */` JSDoc/TSDoc. JSX: `{/* ... */}` dentro de filho, `// ...` dentro de atributos multi-linha e fora do retorno.
- Em JSX, comentário `{/* ... */}` de uma linha é one-liner. Várias linhas seguem a regra.
- Comentário em template literal e em string (`'// não é comentário'`) não é comentário. Use o parser (ou o diff com contexto) para distinguir. URL `https://` e regex `/\/\//` contêm `//` sem ser comentário.
- Comentário em arquivo `.d.ts` escrito à mão (declaração de lib): TSDoc é consumido pelo IDE do consumidor. Aplique a regra e condense em uma linha com o contrato essencial.

## Diretivas a preservar (lista TS/JS)

- TypeScript: `// @ts-expect-error`, `// @ts-ignore`, `// @ts-nocheck`, `// @ts-check`, `/// <reference types|path|lib="..." />`.
- ESLint: `/* eslint-disable ... */`, `/* eslint-enable */`, `// eslint-disable-line`, `// eslint-disable-next-line`, `/* eslint rule: "off" */`, `/* global x */`, `/* exported */`.
- Prettier: `// prettier-ignore`, `{/* prettier-ignore */}`.
- Cobertura: `/* istanbul ignore next|if|else */`, `/* c8 ignore next|start|stop */`, `/* v8 ignore */`.
- Bundler: `/* webpackChunkName: "x" */`, `/* webpackPrefetch: true */`, `/* webpackIgnore: true */`, `/* @vite-ignore */`, `/* #__PURE__ */`, `/* @__PURE__ */`, `/* @__NO_SIDE_EFFECTS__ */`.
- Outros: `// @flow`, `/** @jsx h */`, `/** @jsxImportSource ... */`, `// @refresh reset`, `/* @vitest-environment jsdom */`, `/** @jest-environment jsdom */`, `// @ts-nocheck` em arquivo gerado.
- Decorators de documentação consumidos pelo Nest Swagger plugin: o plugin lê JSDoc de propriedades de DTO (`introspectComments: true` em `nest-cli.json`). Se ativo, o comentário vira `description` no OpenAPI: mantenha um one-liner por propriedade.

## Motivo obrigatório em supressões

- `@ts-expect-error` sem motivo: adicione o motivo na mesma linha (`// @ts-expect-error lib X sem tipo para v4`).
- `@ts-ignore`: handoff para review-tipagem (troca por `@ts-expect-error` é decisão deles). Aqui adicione o motivo, se faltar.
- `eslint-disable-next-line regra`: acrescente `-- motivo` no mesmo comentário (`// eslint-disable-next-line react-hooks/exhaustive-deps -- roda só no mount`). Sintaxe `-- descrição` é oficial do ESLint ≥ 7.
- `eslint-disable` de arquivo inteiro no topo, sem motivo: MAJOR. Ele esconde regras inteiras. Handoff para o dono da regra desligada (review-front para `react-hooks`, review-tipagem para `no-explicit-any`).
- `as unknown as X`, `!` e cast mentiroso: handoff para review-tipagem. Um one-liner com o porquê pode acompanhar a correção.

## JSDoc/TSDoc

- Regra do time: one-liner. `/** Retorna o total em centavos. */` é válido. Multi-linha com `@param`/`@returns` sai.
- Em TypeScript os tipos já estão na assinatura. `@param {string} id`, `@returns {Promise<User>}` e `@type` repetem o tipo: remova.
- `@param id - id do aluno` onde o nome já diz: remova.
- Mantenha: `@deprecated motivo e alternativa` (uma linha), `@internal`, `@see` quando é o porquê, `@throws` quando o erro não é evidente e relevante ao chamador. Em uma linha: `/** @deprecated use getCursos(). Remover em 2.0 */`.
- Em arquivo `.js` com `checkJs` ou `// @ts-check`, JSDoc é o sistema de tipos. Preserve `@type`, `@param {T}`, `@typedef`, `@template`.
- Componente React: o `react-docgen`/Storybook lê JSDoc de props. Se o repo gera docs de componente (cheque `*.stories.*`, `docgen`), mantenha um one-liner por prop. Sem docgen, props autoexplicativas ficam sem comentário.
- Hook e util exportados: um one-liner com o porquê ou unidade. Sem o que fazer, o nome diz.

## Padrões comuns de ruído em TS/JS

- `// eslint-disable-next-line @typescript-eslint/no-explicit-any` sem motivo ao lado de `any` novo: o achado é do review-tipagem. Aqui, só o motivo.
- `// @ts-ignore` coladas em sequência.
- `// TODO: tipar` sem ticket.
- `// props`, `// state`, `// render`, `// handlers`, `// effects`, `// hooks`: rótulos de seção em componente. Remova (NIT). Em componente grande, handoff para review-clean/review-modularidade.
- `// useEffect para carregar dados`: repete o código. Remova.
- `// eslint-disable-next-line react-hooks/exhaustive-deps` repetido várias vezes no mesmo arquivo: cada um pede motivo, e o conjunto é sinal para review-front.
- `console.log` comentado (`// console.log(x)`): código comentado.
- `// @ts-expect-error` em teste para exercitar tipo inválido: legítimo, mantenha. O motivo é "teste de entrada inválida" e pode ser implícito pelo nome do teste.
- `/* eslint-disable */` em arquivo de teste gerado ou fixture: preserve.

## Padrões de adição de alto valor em stacks TS/React/Nest

- Query key do react-query com argumento posicional: `// A key inclui userId: cache por usuário`.
- `enabled: false` em `useQuery` v3: `// idle com enabled=false: isLoading=false e data=undefined`.
- Hook de ordem sensível (`useMemo` com dependência que não é óbvia): `// deps sem o objeto de filtro: o hash é o único gatilho`.
- Nest: `// Ordem: guard de auth antes do guard de roles`, `// Sem await de propósito: fire and forget`, `// Raw body necessário para assinatura do webhook`.
- Prisma: `// updateMany evita TOCTOU: o dono entra no where`, `// Sem include: select explícito evita vazar cpf`.
- Module Federation: `// Remote deve estar em produção antes do host (contrato de props)`.
- Constante de regra copiada de outro serviço: `// Espelha pos-api: CLINICAL_PRACTICE_REQUIRED_MINUTES` (a duplicação em si é do review-dry).
- Unidade em timeout/TTL/limite: `// ms`, `// segundos`, `// bytes`.
- Regex: `// CPF com ou sem pontuação`.
- Flag de feature com valor default relevante: `// Default false: lançamento gradual no Unleash`.

## Falsos positivos frequentes

- URL com `//` dentro de string, regex ou template.
- `/** @type {import('...').Config} */` em `*.config.js`: tipagem consumida pelo editor e pelo `checkJs`.
- `/* eslint-disable no-console */` com motivo implícito em script de CLI. Mantenha. Peça motivo só se o arquivo é de produção.
- `// @ts-expect-error` em teste de tipo (`expectTypeOf`, `tsd`): é a asserção.
- JSX `{/* TODO(ABC-123) ... */}` com dono: mantenha.
- Cabeçalhos de licença `/*! ... */` e `@preserve`: o minificador mantém por contrato.
