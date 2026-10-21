# Resiliência — React (react-query v3, react-router v6, Module Federation)

Carregue quando `react`/`react-dom` está nas deps. Next.js: veja a seção final.

## Error boundaries

- Boundary captura erro de render, lifecycle e constructor dos filhos. Não captura erro em event handler, em `setTimeout`, em promise nem em SSR. Para esses, trate no ponto ou rele com `setState(() => { throw e })`.
- Remote do Module Federation (`loadRemoteModule`, `React.lazy(() => import('remote/X'))`) sem boundary: remote fora do ar ou com versão incompatível derruba o host inteiro. Exija boundary em dois níveis: na página host e no wrapper do remote. Remover boundary existente exige justificativa no MR.
- Boundary com `Suspense` dentro dele (`<Boundary><Suspense>...`): a falha do `import()` do chunk lança no render e o boundary pega.
- Boundary sem `reset`: o usuário fica preso no fallback. Exija botão de nova tentativa e `resetKeys` (rota, id) ou `useQueryErrorResetBoundary` do react-query.
- Fallback de página inteira (altura de tela cheia) dentro de seção pequena: degrada o resto da tela. Use fallback compacto dentro de widget e fallback de página só na rota. Siga o componente de fallback já existente no repo.
- Boundary em componente de módulo simples (modal, tooltip): se o repo reserva boundary para MFE, respeite a convenção.
- Boundary que só chama `console.error` sem enviar ao monitoramento: erro invisível em produção. Handler `onError`/`componentDidCatch` reporta ao Sentry ou equivalente (instrumentação detalhada é do review-observabilidade).

## react-query v3

- `useMutation` com `retry` > 0 sobre operação não idempotente. O default da mutation é 0, e `defaultOptions.mutations.retry` global mudaria isso. Verifique o `QueryClient`.
- `useQuery` com `retry` default 3 e `retryDelay` exponencial: em erro 4xx (404, 403) repete sem necessidade e atrasa o estado de erro em ~7 s. Correção: `retry: (count, err) => !isClientError(err) && count < 2`.
- `enabled: false`: status `idle`, `isLoading` e `isError` valem `false`, `data` é `undefined`. Componente que retorna `null` sem dado some em silêncio. Trate `idle` explicitamente.
- `isError` e `error` ignorados: a tela mostra "vazio" quando falhou. Exija ramo de erro com ação (tentar de novo via `refetch`).
- `onError` em `useQuery` v3 dispara por observer: com N componentes montados, N toasts. Prefira um handler global no `QueryCache`.
- `onSuccess`/`onError` do `useMutation` sem `onSettled` para limpar estado: loading eterno em erro.
- `useErrorBoundary: true` nas queries que devem cair no boundary. Sem a flag, o erro não chega lá.
- Mutation otimista (`onMutate`) sem `onError` com rollback via contexto e `onSettled` com `invalidateQueries`: a UI fica com dado falso após falha.
- `refetchOnWindowFocus` com mutation em andamento ou formulário editado: refetch sobrescreve o estado local.
- `staleTime: 0` com erro em refetch de fundo: o v3 mantém `data` antigo e marca `isError`. Mostrar só o erro apaga conteúdo válido. Decida se exibe o stale com aviso.

## Efeitos e async

- `useEffect` com `fetch` e `setState` sem cleanup: resposta tardia após unmount ou após troca de parâmetro sobrescreve estado novo (race). Correção: `AbortController` e flag de cancelamento no cleanup. Detalhe de ciclo de effect é do review-front; aqui entra a falha silenciosa e o estado inconsistente.
- Callback de SDK (`posthog.getSurveys(cb)`, `navigator.geolocation`, `IntersectionObserver`) que chama `setState` após unmount: guard de montagem.
- `async` handler de submit sem `try/catch`: o `await` rejeitado vira unhandled rejection e o botão fica travado em `loading`. Correção: `try/finally` para resetar o estado e mostrar erro local.
- Duplo clique em mutation: sem `isLoading` desabilitando o botão ou sem idempotency key, dispara duas escritas.
- `JSON.parse`, `atob`, `new URL(...)`, `decodeURIComponent` sobre dado de URL, storage ou resposta: try/catch com estado de erro local. `atob` inválido lança síncrono e derruba a árvore sem boundary.
- `localStorage`/`sessionStorage` podem lançar (modo privado, cota): envolva em try/catch e renderize sem eles.
- `Promise.all` de múltiplas queries no loader: uma falha esconde as demais. Avalie `allSettled`.

## react-router v6

- `errorElement` ausente na rota: erro de loader ou render cai no fallback padrão do router ("Unexpected Application Error!"). Defina `errorElement` na raiz e em rotas com loader.
- `loader` que lança `Response` (404) vs `Error`: use `isRouteErrorResponse` para distinguir.
- `navigate` dentro de `useEffect` com guard de feature flag antes de ela estar pronta redireciona errado. Aguarde a readiness e redirecione de forma síncrona.

## Rede no cliente

- `axios`/`fetch` sem `timeout`: a UI fica em loading para sempre numa rede ruim. Defina no client compartilhado.
- Interceptor de refresh de token sem controle de concorrência: N requests 401 disparam N refreshes; um deles invalida os outros. Correção: promise única de refresh compartilhada e fila das requests pendentes. Sem teto, loop infinito de 401 → refresh → 401.
- Offline/`navigator.onLine`: operações de escrita sem feedback quando a rede cai. Tela deve mostrar estado e permitir nova tentativa.
- Upload e progresso de aula: perda de progresso em falha. Grave o progresso de forma resiliente (retry limitado com backoff, `navigator.sendBeacon` no `pagehide`, fila local) e confira o resultado.

## Estado de erro e UX

- Erro engolido em `catch` com `console.log` e sem mudança de UI.
- Mensagem técnica (`err.message`, stack) exibida ao usuário. Use texto do dicionário de i18n do repo.
- Loading infinito: todo estado de carga tem saída (erro, timeout, vazio).
- Skeleton que nunca resolve quando `data` é `undefined` por `idle`.

## Next.js (se `next` nas deps)

- `error.tsx` e `global-error.tsx` por segmento; `not-found.tsx`. `error.tsx` precisa ser Client Component e oferecer `reset`.
- Server Action e Route Handler: `try/catch` com retorno de erro serializável. Exceção não tratada vira 500 sem contexto para o formulário.
- `fetch` em Server Component sem `signal`/timeout trava a renderização do segmento. Combine com `Suspense` e `error.tsx`.
- `redirect()` e `notFound()` lançam por design: não os envolva em `catch` genérico.

## Correção típica

```tsx
<LABErrorBoundary resetKeys={[userId]} fallback={<WidgetFallback />}>
  <Suspense fallback={<Skeleton />}>
    <RemoteWidget userId={userId} />
  </Suspense>
</LABErrorBoundary>
```

```ts
const { data, isError, isLoading, isIdle, refetch } = useQuery(['x', id], fetchX, {
  enabled: Boolean(id),
  retry: (n, err) => n < 2 && !isClientError(err),
  useErrorBoundary: false,
});
if (isIdle) return null; // consumidor decide: placeholder, não vazio silencioso
if (isError) return <InlineError onRetry={refetch} />;
```
