# Contratos em React e Module Federation

## Consumo de API no cliente

- Sinal: hook do react-query com `queryFn: async () => (await api.get<Foo>(url)).data` sem parse. Impacto: o tipo `Foo` é afirmação. Campo faltando vira `undefined` renderizado como vazio, ou `TypeError` em `.map`. Correção: `FooSchema.parse(data)` no `queryFn`, ou no `select` quando a transformação é de apresentação.
- Sinal: `select`/mapper no hook acessando `data.items.map` sem tratar `items` ausente ou `null`. Impacto: tela branca quando o BFF devolve `null` em vez de `[]`. Correção: `data.items ?? []` com a decisão de contrato registrada (a API devolve `[]`, e o client só protege contra evolução).
- Sinal: campo opcional no tipo e usado como obrigatório (`course.tags.length`). Impacto: `TypeError` quando a API omite. Correção: tratar a ausência, ou corrigir o contrato.
- Sinal: `useQuery` com `enabled: false` e componente que lê `data` como se existisse. Status `idle` no react-query v3 devolve `data: undefined`, `isLoading: false`. O tema de estado é do review-front.
- Sinal: tipo de response do hook diverge do tipo gerado ou do DTO do BFF (mesmo nome, campos diferentes). Impacto: drift.
- Sinal: mutation com payload montado a mão e enviado com campo que o servidor ignora (whitelist) ou rejeita (`forbidNonWhitelisted`). Impacto: 400 em produção, campo perdido sem erro. Correção: tipo do payload derivado do DTO ou schema compartilhado.
- Sinal: conversão manual de `snake_case` para `camelCase` espalhada em componentes. Correção: um mapper na camada de API.
- Sinal: erro da API lido como `error.response.data.message`. Impacto: o shape de erro muda (string, array, objeto) e o componente mostra `[object Object]`. Correção: um normalizador de erro tipado na camada de API.
- Sinal: ramo `switch` sobre `status` da API sem `default`. Impacto: valor novo deixa a UI sem estado. Correção: `default` com fallback neutro e log.

## Props de componente como contrato

- Componente exportado de pacote, design system ou remote é API pública. Remover ou renomear prop, estreitar tipo ou tornar obrigatória é breaking change. Para componente interno de app único, o compilador pega e o achado não se aplica.
- Sinal: prop opcional vira obrigatória em componente de biblioteca compartilhada. Correção: default no componente.
- Sinal: valor novo em prop de union (`variant`) é compatível para o consumidor, e a remoção de valor quebra.
- Sinal: `children` com contrato implícito de shape (render prop com novos argumentos). Adicionar argumento ao final é compatível.
- Alteração em componente do design system externo pertence ao repo do design system. O MR do app não altera o componente.

## Module Federation

- Contrato host para remote: nome do módulo exposto (`./Component`), props, eventos (callbacks), contexto compartilhado, versões de singletons (`react`, `react-dom`, `styled-components`).
- Sinal: o host muda nome, tipo ou shape de prop enviada ao remote. Impacto: o remote carrega ao vivo, então o remote em produção recebe a prop nova no mesmo instante em que o host sobe. Ordem correta: remote tolerante aos dois shapes em produção, depois o host. Correção: o MR do remote entra antes, e o MR do host referencia o do remote.
- Sinal: o remote muda uma prop que o host em produção já envia (`{ userId }` para `{ courseId }`). Impacto: host antigo envia `userId`, o remote lê `courseId` e recebe `undefined`. Correção: o remote aceita as duas props na janela de migração.
- Sinal: `exposes` renomeado ou removido no `webpack.config`/`module-federation.config`. Impacto: o host falha em `loadRemoteModule` com erro de chunk. Correção: manter o nome antigo como re-export.
- Sinal: `shared` com `singleton: true` e `requiredVersion` alterados. Impacto: duas cópias do React ou versão incompatível, erro de hooks. Versão fixada de propósito num singleton não é achado. Reporte só a mudança sem justificativa.
- Sinal: tipos do remote declarados à mão no host (`declare module 'remote/Foo'`). Impacto: drift. Correção: pacote de tipos publicado pelo remote ou geração com `@module-federation/typescript`.
- Sinal: remote sem valor default para prop opcional e sem tratamento de prop ausente. Impacto: o host antigo quebra o remote.
- Sinal: componente de remote sem `LABErrorBoundary` ou equivalente no host. Contrato de falha: o remote pode estar fora do ar. A ausência de boundary é do review-front e do review-resiliencia. Cite como handoff.
- Sinal: `window.postMessage`, `CustomEvent` ou `localStorage` como canal host-remote. Shape do payload documentado e validado no receptor.

## WebView e app nativo

- Sinal: a web app abre dentro de WebView de um app nativo e a mudança altera query string, `postMessage`, bridge JS ou cookie esperado pelo app. Impacto: o app publicado nas lojas não atualiza no mesmo ritmo da web. Correção: manter compatibilidade com a versão mínima suportada do app.

## Rotas de front como contrato

- Sinal: path de rota do react-router alterado (`/curso/:id/:slug` para `/cursos/:id`). Impacto: links em e-mail, push, deep link do app, QR code e favoritos quebram. Correção: redirect da rota antiga.
- Sinal: nome de query param lido pelo app e gerado por outro serviço (e-mail, notificação). Mesma regra.
- Chaves de analytics e `localStorage`/`sessionStorage` lidas por outro app são contrato. Renomear exige leitura dupla na janela de migração.
