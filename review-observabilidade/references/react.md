# Observabilidade — React (front-end)

Carregue quando `react`/`react-dom` está nas deps. Next.js: veja a seção final.

## Analytics de produto (PostHog, Mixpanel, GA)

- **Disparo em `useEffect` sem guard.** Sinal: `useEffect(() => { track('x_viewed', {...}) }, [data])` com `data` instável (objeto recriado a cada render), ou deps vazias sob `StrictMode`. Impacto: 2× em dev por design e N× em produção por remontagem, mudança de referência ou refetch. O funil infla. Correção:

```tsx
const fired = useRef(false);
useEffect(() => {
  if (fired.current || !courseId) return;
  fired.current = true;
  track('course_viewed', { courseId });
}, [courseId]);
```

- **Ref booleano único sobre duas fontes assíncronas.** Sinal: `fired.current = true` ao primeiro dado que chega, com o segundo (ids) ainda `undefined`. Impacto: evento sai com `undefined` e nunca é corrigido. Correção: dois refs, um para "disparou" e um para "disparou com ids completos"; dispare quando todos os campos existem.
- **Evento em handler, não em render.** Evento de ação (`clicou`, `enviou`) vai no handler. Evento de visualização vai em effect com guard ou em `IntersectionObserver` com disparo único.
- **Componente reutilizado em rotas diferentes com atributo fixo.** Propriedade constante (`platform: 'web'`, `flow: 'support'`) em componente montado em duas rotas descreve só um contexto. O atributo deve vir do contexto real (rota, props) e não identifica o dispositivo.
- **Propriedades com PII**: e-mail, nome, CPF em `track`/`identify`/`people.set`. Use id interno.
- **Nome de evento** fora do padrão do repo, string solta em vez de constante do catálogo. Exija constante ou tipo `AnalyticsEvent`.
- **Evento disparado antes da identidade pronta** (usuário anônimo → identificado): `identify` antes do primeiro `track` do fluxo; sem isso o funil quebra em dois usuários.
- **Super properties** com valor desatualizado após troca de contexto (curso, matrícula).
- **Eventos de alta frequência** (scroll, `timeupdate` de vídeo, digitação): throttle ou agregação. Para player: marcos (25/50/75/100%), não cada tick.
- **Consentimento**: `posthog.opt_out_capturing()` respeitado; `autocapture` capturando texto de inputs sensíveis (`ph-no-capture`, `maskAllInputs`).
- **Session replay**: `maskAllInputs: true` e `maskTextSelector`; bloqueie áreas com dado clínico, nota, dado pessoal.
- **Callback de SDK** (`posthog.getSurveys(cb)`, `onFeatureFlags`) que chama `setState` após unmount: guard.
- **Survey por posição** (`questions[0]`): confira por tipo ou texto; a survey muda fora do repo.

## Monitoramento de erro no front

- **Error boundary sem reporte.** O boundary renderiza fallback e não chama `Sentry.captureException`/`componentDidCatch` com `componentStack`. Erro de produção fica invisível. Correção: `onError={(error, info) => Sentry.captureException(error, { contexts: { react: { componentStack: info.componentStack } } })}`.
- **Remote do Module Federation com falha** (chunk não carrega): capture com tag `remote` e `scope` para saber qual MFE caiu.
- **`window.onerror`/`unhandledrejection`**: Sentry os cobre com o integration padrão. Confira se `Sentry.init` roda cedo e se `dsn` e `environment` vêm de `window.env`.
- **Source maps**: o build gera (`devtool: 'hidden-source-map'`), o CI envia (`sentry-cli sourcemaps upload` ou plugin) e o `release` do SDK é igual ao do upload. Source maps servidos publicamente expõem o código-fonte; prefira `hidden` + upload (dono do tema de exposição: review-seguranca).
- **Erros ruidosos** ignorados por `ignoreErrors`: `ResizeObserver loop limit exceeded`, extensões de browser, `ChunkLoadError` tratado por retry, `AbortError`, 401 de sessão expirada.
- **PII no evento**: `sendDefaultPii: false`; breadcrumbs de `console` e `fetch` com URL e corpo: `beforeBreadcrumb` para limpar. Replay com máscara.
- **Contexto de usuário**: `Sentry.setUser({ id })` ao logar e `setUser(null)` ao sair. Sem limpar, erros do próximo usuário do mesmo browser aparecem com o id errado.
- **Contexto de negócio**: `setTag('courseId' | 'enrollmentId' | 'route')` com baixa cardinalidade.
- **`tracesSampleRate`** para Web Vitals e navegação: valor explícito e baixo em produção.
- **react-query**: handler global em `QueryCache({ onError })` e `MutationCache({ onError })` para reportar uma vez e com a chave da query. `onError` por hook duplica por observer. Erros 4xx esperados ficam fora.

## Web Vitals e métricas de UX

- Coletar LCP, INP, CLS (`web-vitals`: `onLCP`, `onINP`, `onCLS`) e enviar com a rota templatizada e a versão do build. Sem coleta, regressão de performance não aparece. A análise de causa é do review-front; aqui entra a existência do sinal.
- `navigator.sendBeacon` para enviar no `pagehide` (fetch é cancelado).
- Marcos de negócio do front (tempo até o player tocar, falha de carregamento do vídeo, buffering): evento com duração e resultado.
- Erro de carregamento de mídia (`<video onError>`) reportado com tipo do erro e id do conteúdo, sem URL assinada (contém token).

## Logs no cliente

- `console.log` de depuração esquecido no diff: remova. O `console` do navegador vai para o replay e para breadcrumbs do Sentry.
- `console.log(user)`, `console.log(token)`, `console.log(response)`: expõe dado em qualquer máquina compartilhada e vira breadcrumb. Remova.
- Logging condicional por ambiente: use o gate já adotado no repo (`window.env.ENVIRONMENT === 'prod'`). Gate diferente em cada arquivo é inconsistência.
- Logger de cliente que envia ao backend: limite de taxa e de tamanho, sem PII, sem laço de retry (log de falha de log).

## Contexto e correlação

- Requests do front enviam `x-request-id` ou `traceparent` quando o repo usa tracing no browser (`@opentelemetry/instrumentation-fetch` / `xml-http-request`). Sem isso, o trace começa no gateway e o tempo do cliente fica fora.
- `propagateTraceHeaderCorsUrls` ou lista equivalente: o header `traceparent` só vai para origens permitidas. Para terceiros, nunca (vaza id de trace e dispara preflight CORS).
- Erro de API exibido ao usuário com o `requestId` (código de suporte) facilita a correlação. Se o backend devolve, mostre.

## Next.js (se `next` nas deps)

- `instrumentation.ts` (`register()`) para OTel/Sentry server-side. Sentry com `@sentry/nextjs` e `withSentryConfig` para source maps.
- Server Action e Route Handler: log estruturado com `requestId`, e captura de erro com `Sentry.captureException`; `error.tsx` recebe `error.digest`, que correlaciona com o log do servidor. Exiba o `digest` ao usuário no fallback.
- Variáveis `NEXT_PUBLIC_*` de DSN são públicas por natureza. Chave de servidor não pode ir para elas (review-seguranca).
- Evento de analytics em Server Component executa no servidor: use o SDK server-side e evite duplicar com o do cliente.

## Sinais de alerta rápidos

- `track(` dentro de corpo de componente (render) fora de effect ou handler.
- `useEffect(() => { track(...) })` sem array de deps.
- `posthog.identify(user.email)`.
- `catch (e) { console.log(e) }` em fluxo crítico: falha vira invisível em produção.
- `Sentry.captureException` dentro de `useEffect` de componente renderizado em lista: N reportes.
