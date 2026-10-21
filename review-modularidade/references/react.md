# Modularidade em React, Module Federation e Next

## Estrutura de código de UI

- Sinal: componente de página importando componente interno de outra página (`pages/A/components/Card` usado em `pages/B`). Correção: promover para `components/` compartilhado ou para a API pública da feature.
- Sinal: `components/` genérico importando de `pages/` ou de contexto de feature. Seta invertida: o genérico passa a depender da feature. Correção: receber dado por props.
- Sinal: componente de apresentação importando hook de dados e contexto de domínio. Correção: container/hook na borda, props no componente.
- Sinal: hook de feature importado por 6+ features, e o diff muda sua assinatura. Ca alto. Correção: manter a assinatura e adicionar variante, ou migrar os consumidores no mesmo PR.
- Sinal: `utils/` e `helpers/` globais acumulando função de uma feature. Correção: colocar junto da feature.

## Camadas na UI

Ordem típica e permitida: pages → features/containers → components (UI) → hooks de infra → api client. Seta ao contrário é achado.

- Sinal: `api/` (client, queries) importando componente ou contexto de UI. Correção: o client recebe dados por parâmetro.
- Sinal: query hooks de react-query chamando `navigate`/`toast`. Efeito de UI dentro da camada de dados. Correção: o componente trata `onSuccess`/`onError` via `mutate(…, { onSuccess })`.
- Sinal: regra de negócio em componente quando o BFF/serviço dono já entrega o campo. Dono do tema regra duplicada: review-dry.

## Context e providers

- Sinal: Provider novo que importa de features para montar valor (dependência do Provider raiz em feature). O Provider raiz só conhece infra. Correção: provider da feature montado na rota da feature.
- Hierarquia de providers do repo é contrato de ordem. Um consumidor abaixo do provider que ele precisa. Confirme na raiz (`providers/index.tsx`).
- Componente fora da árvore de `RouterProvider` (chat widget, overlay global) usando `useNavigate`/`useLocation` quebra. Correção: singleton do router conforme o padrão do repo.

## Module Federation (Webpack 5)

Leia `webpack.config.*`: `ModuleFederationPlugin` (`name`, `exposes`, `remotes`, `shared`).

- Contrato: tudo em `exposes` é API pública. Props do módulo exposto, eventos que ele emite e dados que ele lê são o contrato. Alterar shape (renomear prop, trocar `{ userId }` por `{ courseId }`) quebra o par no deploy.
- Ordem de deploy: o remote vai para produção antes do host, porque o host carrega o remote ao vivo. O diff do host que muda a prop enviada exige o MR do remote já em produção. Sem a ordem no PR: MAJOR. Remote mudado para exigir prop nova obrigatória sem o host enviar ainda: BLOCKER. Remote que remove prop que o host ainda envia: tolerável se o remote ignora a prop extra. Compatibilidade nos dois sentidos durante a janela de deploy. Detalhes de shape de payload pertencem a review-contratos.
- `shared`: `react`, `react-dom`, `styled-components` e libs com contexto (react-router, react-query) como `singleton: true` com `requiredVersion` fixada. `singleton: false` ou versão fora do range duplica o runtime (hooks quebram, `Invalid hook call`, tema perdido). Siga o que o repo fixou, e não aponte como dependência desatualizada versão fixada de propósito.
- Fault isolation: remote carregado por `loadRemoteModule`/`React.lazy` precisa de boundary (`ErrorBoundary` + `Suspense`). A convenção do repo está no `CLAUDE.md` (ex.: `LABErrorBoundary` em dois níveis: página e wrapper do remote). Remoção de boundary sem justificativa no PR: MAJOR. Boundary reservado a MFE: componente de módulo comum (modal) não ganha boundary acima, conforme convenção do repo.
- Padrão de carga: `lazy()` criado uma vez no escopo do módulo, props por parâmetro. `lazy()` dentro de render ou `useMemo` com dependência instável recria o componente e remonta o remote a cada render. Desvio justificado (remote exige `dataSource` montado pelo host) é aceito.
- Host importando código do remote por caminho relativo, ou remote importando do host: quebra o isolamento. Correção: declarar em `exposes`/`remotes`.
- Tipos do remote: `declare module 'remote/X'` escrito à mão no host diverge. Correção: tipos publicados pelo remote, ou arquivo de declaração com origem citada.
- Estado compartilhado entre host e remote por global de `window`: acoplamento implícito. Correção: props, eventos tipados ou store exposto.
- Mesma dependência pesada duplicada entre remotes por falta de `shared`: dono do tema bundle é review-front. Aqui só o contrato de `shared`.

## Next.js (se `next` estiver nas deps)

- Fronteira server/client: `'use client'` no topo de módulo que importa código de servidor (`fs`, ORM, segredos) quebra o bundle ou vaza dado. Módulo de servidor importado por componente cliente: use `server-only` (se disponível) para travar.
- Route handlers e Server Actions com regra de negócio direta: mover para service/use case importado pela rota.
- Camadas: `app/` (rotas) importa de `features/` e `lib/`. `lib/` não importa de `app/`.
- Barrel com `'use client'` e componentes de servidor no mesmo arquivo: fronteira ambígua.

## Estado compartilhado entre features

- Store global (Context, Zustand, Redux) com slices de várias features e acesso cruzado direto. Correção: seletores e ações públicas por slice.
- Cache do react-query: `queryKey` de uma feature lida por outra por string. Correção: factory de keys exportada pela feature dona.
