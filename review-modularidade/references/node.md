# Modularidade em Node HTTP (express, fastify, koa)

## Camadas sem framework de DI

- Sinal: handler de rota (`app.get('/x', async (req, res) => { ... })`) com query, regra e resposta no mesmo corpo. Correção: handler fino (`parse → service → respond`), service sem `req`/`res`, repository com o acesso a dados.
- Sinal: `req`, `res`, `ctx` ou `reply` passados para função de domínio. Correção: extrair os valores no handler e passar tipos de domínio.
- Sinal: `req.user`/`req.tenant` lidos fundo na regra. Correção: parâmetro explícito (`actor`, `tenantId`).
- Sinal: erro de domínio traduzido para status HTTP dentro do service (`res.status(404)`). Correção: o service lança erro de domínio, e o middleware de erro traduz.

## Middlewares e plugins

- Ordem de registro é contrato. Middleware que depende de `req.user` precisa vir depois da autenticação. Sinal: rota registrada antes do middleware de auth/validação.
- Plugin fastify com `fastify-plugin` expõe decorators ao escopo pai. Sem `fastify-plugin`, o encapsulamento esconde o decorator. Sinal: decorator usado fora do escopo que o registrou.
- Sinal: middleware global que contém regra de negócio de uma única rota. Correção: no escopo da rota.
- Sinal: estado de request em variável de módulo (`let currentUser`). BLOCKER: vaza entre requests concorrentes. Correção: `req`-scoped, `AsyncLocalStorage`.

## Composição

- Raiz de composição única (`server.ts`/`app.ts`) cria cliente de banco, repositories, services e rotas, e passa por parâmetro.
- Sinal: `import { db } from '../db'` espalhado, com o client criado no import. Efeito no import. Correção: `createApp({ db })`.
- Sinal: `require` condicional ou dinâmico para fugir de ciclo. Correção: extração.
- Teste que sobe o `listen` na importação do app: separe `buildApp()` de `listen()`.

## Módulos e pacotes

- ESM vs CJS misturados (`require` em pacote `"type": "module"`): fronteira de formato. Correção: um formato por pacote, ou `exports` condicional.
- `index.js` com `module.exports = { ...require('./a'), ...require('./b') }`: barrel com ciclo provável.
- Dependência de produção importada de `devDependencies`: quebra no deploy. Confirme em `package.json`.
- Monorepo: import de outro pacote por caminho relativo. Correção: pacote declarado em `dependencies`/workspace com `exports`.

## Roteamento e features

- Sinal: arquivo `routes.ts` único com 40+ rotas de 6 domínios. Correção: router por feature, montado na raiz.
- Sinal: rota que chama diretamente o handler de outra rota (`require('./other').handler(req, res)`). Correção: extrair o service comum.
