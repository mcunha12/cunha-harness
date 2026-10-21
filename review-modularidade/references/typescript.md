# Modularidade em TypeScript

## Resolução de módulos e paths

- Sinal: alias novo em `tsconfig.paths` sem espelho no bundler/jest (`moduleNameMapper`, `resolve.alias`). Impacto: compila e quebra em runtime ou teste.
- Sinal: import relativo subindo 3+ níveis (`../../../other-feature/x`). Impacto: atravessa fronteira de feature sem alias de API pública. Correção: alias por módulo (`@/enrollment`) apontando para o `index.ts`.
- Sinal: workspace importando outro por caminho de arquivo (`../../packages/ui/src/x`). Correção: pacote com `exports` e import pelo nome.

## Package exports

- `package.json` com `exports` define a API pública. Import de subcaminho fora de `exports` falha em Node ESM e em bundlers modernos. Sem `exports`, todo arquivo do pacote vira público, e o deep import funciona por acidente.
- Sinal: pacote interno sem `exports`, consumidor com `@org/pkg/dist/...`. Correção: `exports` explícito com os pontos de entrada.
- Sinal: pacote com `"sideEffects"` ausente, em lib com barrel: tree shaking falha. Dono: review-front. Aqui só a fronteira.

## Barrels e ciclos em TS

- `export * from './x'` e `export { x } from './x'` funcionam como barrel. `import type`/`export type` somem em compilação, e ciclos só de tipo são inofensivos em runtime. Confirme que o import não carrega valor.
- Sinal: `isolatedModules` com reexport de tipo sem `export type` (erro de TS1205). O compilador já pega.
- Ciclo clássico: `types.ts` importa de `constants.ts` que importa de `types.ts`. Correção: tipo e constante em arquivos separados sem aresta de volta.
- `enum` e `class` em ciclo são os que quebram em runtime (TDZ, `undefined` em `extends`).

## Injeção sem container

- Raiz de composição manual: `const repo = createRepo(db); const svc = createService({ repo, clock })`. Aceite como DIP quando as dependências chegam por parâmetro.
- Sinal: `import { db } from './db'` dentro de função de domínio. Violação de fronteira. Correção: receber o repository por parâmetro.

## Domínio sem vendor

- Sinal: `import type { Prisma } from '@prisma/client'` em arquivo de regra. Fronteira vazada. Em repo CRUD que adota Prisma como modelo de dados, o padrão local decide: reportar só quando a regra de negócio se escreve em termos de `Prisma.*Input`.
- Sinal: `AxiosError` capturado e inspecionado fora do adapter (`err.response?.status === 404` na regra). Correção: o adapter traduz para erro de domínio (`NotFoundError`).
- Sinal: tipos de `openai`/`@google/genai` em assinatura de service de domínio. Correção: port `LlmClient` com tipos próprios.

## Estado de módulo

- `export const store = ...` mutável e `export let`: acoplamento oculto entre quem importa. Correção: factory, ou estado atrás de função.
- Efeitos no topo: veja `generic.md`. Em ESM, o efeito roda uma vez por grafo, e em testes (`jest.isolateModules`) roda de novo.

## Ferramentas

- `tsc --noEmit` não detecta ciclo. Use madge ou depcruise.
- `knip` aponta export sem consumo e arquivo órfão.
- `eslint-plugin-import` regra `import/no-cycle` e `import/no-internal-modules` cobrem ciclo e deep import. Confirme se estão ligadas na config do repo antes de reportar o que elas já pegam.
