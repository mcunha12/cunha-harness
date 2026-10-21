---
name: review-front
description: "Revisa a saúde do front-end de um diff: re-renders, effects, data fetching, estado, bundle, Core Web Vitals, SSR/hydration, leaks, error boundaries e Module Federation. Acione em 'revisa a performance/saúde do front desse PR', '/review-front' ou via master-review. Prefixo FRT. NÃO cobre acessibilidade (review-a11y), XSS e authZ (review-seguranca), N+1 e cache de backend (review-queries), naming e complexidade (review-legibilidade), contrato de API (review-contratos) nem testes (test-audit)."
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-front

## Missão

Encontrar no diff os defeitos de front-end que o usuário sente: tela que trava, tela que pisca, dado velho, dado perdido, bundle inchado, remote que derruba o host. Cada achado cita o sinal no código, o impacto medido ou estimado em números (re-renders por interação, KB no bundle, requests em cascata) e a correção com código. O agente reporta só o que o diff introduziu ou tocou.

## Escopo

Cada item segue o formato sinal, impacto, correção. O detalhe por tecnologia fica em `references/`.

### 1. Renderização
- Sinal: objeto, array ou função inline passado como prop a componente com `React.memo`, ou como `value` de Context. Impacto: o memo nunca acerta e todo consumidor do Context renderiza a cada render do provider. Correção: `useMemo`/`useCallback` no valor, ou separar o Context em dois (estado e dispatch).
- Sinal: estado elevado ao ancestral comum além do necessário (digitação num input re-renderiza a página). Impacto: INP acima de 200 ms em listas grandes. Correção: descer o estado para o componente que o usa, ou extrair o input.
- Sinal: `key={index}` em lista que reordena, filtra ou insere; `key={Math.random()}`. Impacto: remount de subárvore, perda de foco e de estado local. Correção: id estável do dado.
- Sinal: `useMemo`/`useCallback`/`memo` em valor barato ou sem consumidor memoizado. Impacto: custo de comparação sem ganho e ruído. Correção: remover.
- Sinal: lista com mais de ~100 itens renderizada inteira. Impacto: DOM grande, scroll com jank. Correção: virtualização (`react-window`, `@tanstack/react-virtual`) ou paginação.

### 2. Effects
- Sinal: `useEffect` que copia prop em `useState`, ou calcula valor derivado e chama `setState`. Impacto: render extra e janela de estado inconsistente. Correção: calcular no render (`useMemo` se caro).
- Sinal: `useEffect` que reage a evento do usuário (envia POST depois que `submitted` vira true). Impacto: duplo disparo em StrictMode, lógica espalhada. Correção: executar no handler.
- Sinal: fetch em effect sem cleanup, sem `AbortController` ou sem flag `ignore`. Impacto: race condition, a resposta da requisição antiga sobrescreve a nova; `setState` após unmount. Correção: abortar no cleanup.
- Sinal: array de deps mentindo ou `// eslint-disable-next-line react-hooks/exhaustive-deps`. Impacto: closure obsoleta, bug silencioso. Correção: incluir a dep e estabilizar o valor, ou usar ref para o valor que não deve disparar.
- Sinal: effect com objeto ou função recriada a cada render na lista de deps. Impacto: loop de render ou refetch contínuo. Correção: dependências primitivas ou valores memoizados.
- Sinal: callback de SDK (`posthog.getSurveys(cb)`) chamado em effect sem guard de unmount antes do `setState`. Correção: flag `cancelled` no cleanup.

### 3. Data fetching
- Sinal: `useQuery` filho que só dispara depois que o pai resolve outro `useQuery`, sem dependência real de dado. Impacto: waterfall, soma das latências. Correção: disparar em paralelo, ou `useQueries`.
- Sinal: `fetch`/`axios` manual em effect quando o repo usa React Query, SWR ou server components. Impacto: sem cache, sem dedup, sem retry padronizado. Correção: hook de query no padrão do repo.
- Sinal: `queryKey` sem todos os parâmetros que mudam a resposta, ou mutation sem `invalidateQueries`/`setQueryData`. Impacto: tela mostra dado de outro aluno/curso ou dado velho após escrita. Correção: key completa e invalidação da key afetada.
- Sinal: ausência de estado de loading, erro ou vazio. Impacto: tela em branco, `undefined.map`. Correção: tratar os três estados.
- Sinal: update otimista sem `onError` com rollback. Impacto: UI mostra sucesso de escrita que falhou. Correção: `onMutate` salva snapshot, `onError` restaura, `onSettled` invalida.
- Sinal (react-query v3): `enabled: false` mantém a query em `idle`. Nesse estado `isLoading` e `isError` valem `false` e `data` vale `undefined`. Componente que devolve `null` sem dado some em silêncio. Correção: tratar `isIdle` explicitamente.
- Sinal: `refetchOnWindowFocus` ligado em query cara, `staleTime: 0` em dado quase estático. Impacto: requests redundantes por troca de aba. Correção: `staleTime` coerente com a volatilidade do dado.

### 4. Estado
- Sinal: dado de servidor copiado para store global ou `useState`. Impacto: duas fontes da verdade, dado desatualizado. Correção: deixar no cache de query.
- Sinal: filtro, página ou aba só em `useState` quando o usuário espera voltar/compartilhar o link. Correção: search param na URL.
- Sinal: prop drilling com mais de 3 níveis de props repassadas sem uso. Correção: composição (`children`) antes de Context.
- Sinal: store global para estado de um único componente. Correção: estado local.

### 5. Bundle e carregamento
- Sinal: `import _ from 'lodash'`, `import moment from 'moment'`, import de ícone pelo barrel (`import { X } from 'lib'` em lib sem sideEffects:false). Impacto: dezenas a centenas de KB no chunk inicial. Correção: import por caminho (`lodash/debounce`), `date-fns`, ícones nomeados por arquivo.
- Sinal: rota, modal, editor, chart ou PDF viewer importado de forma estática. Correção: `React.lazy` + `Suspense`, no escopo do módulo.
- Sinal: dependência nova de mais de 30 KB gzip sem justificativa, ou duas libs com a mesma função (dayjs e moment). Correção: reusar a existente.
- Sinal: `<img>` sem `width`/`height` (ou `aspect-ratio`), sem `loading="lazy"` abaixo da dobra, imagem LCP com `loading="lazy"`. Impacto: CLS, LCP tardio. Correção: dimensões, `fetchpriority="high"` na imagem LCP.
- Sinal: `@font-face` sem `font-display: swap`/`optional`. Impacto: texto invisível até a fonte chegar. Correção: declarar `font-display` e fazer preload da fonte crítica.
- Sinal: script de terceiro síncrono no `<head>`. Correção: `defer`/`async` ou carregar após `load`.
- Sinal (Module Federation): `shared` sem `singleton: true` para `react`, `react-dom`, `styled-components`, ou versão mudada no diff. Impacto: duas instâncias de React, hooks quebram ("Invalid hook call"), bundle duplicado. Correção: manter singleton com a versão fixada do host.

### 6. Core Web Vitals
- LCP: recurso do elemento LCP descoberto tarde (imagem via CSS background, fetch em cascata antes do hero). Correção: preload, dado no primeiro request.
- INP: handler síncrono acima de 50 ms (filtro de lista grande a cada tecla). Correção: `startTransition`/`useDeferredValue`, debounce, Web Worker.
- CLS: conteúdo que entra sem reservar espaço (banner, skeleton com altura diferente do conteúdo). Correção: altura mínima reservada.

### 7. SSR e hydration (só se o repo usa SSR)
- Sinal: `Date.now()`, `Math.random()`, `window`, `localStorage` no render. Impacto: hydration mismatch. Correção: ler em effect, ou `suppressHydrationWarning` com motivo.
- Sinal: `"use client"` no topo de componente que não usa estado nem evento. Correção: remover e manter como server component.
- Sinal: objeto inteiro de usuário passado de server para client component. Impacto: dado sensível serializado no HTML. Correção: passar só os campos usados. Segurança do dado fica com review-seguranca.

### 8. Robustez
- Sinal: `addEventListener`, `setInterval`, `setTimeout`, `subscribe`, `ResizeObserver` sem cleanup. Impacto: leak e handler duplicado a cada mount. Correção: retornar cleanup no effect.
- Sinal: componente de remote de Module Federation (`loadRemoteModule`, `lazy(() => import('remote/X'))`) sem error boundary acima e sem `Suspense`. Impacto: queda do remote derruba a página inteira do host. Correção: `LABErrorBoundary` (ou o boundary do repo) em volta, no host e no wrapper do remote.
- Sinal: `lazy()` criado dentro do corpo do componente. Impacto: novo tipo de componente a cada render, remount e reload do chunk. Correção: criar no escopo do módulo. Exceção aceita quando o remote exige valor montado pelo host, com `useMemo` e dep explícita.
- Sinal: leitura de `offsetHeight`/`getBoundingClientRect` intercalada com escrita de estilo em loop. Impacto: layout thrashing. Correção: agrupar leituras, depois escritas.
- Sinal: formulário grande com `watch()` global ou estado controlado em todos os campos. Impacto: cada tecla renderiza o formulário inteiro. Correção: campos não controlados (`register`), `useWatch` por campo, `memo` nos blocos.
- Sinal: `JSON.parse`, `atob` ou decode de dado externo sem try/catch. Impacto: exceção síncrona derruba a árvore React. Correção: try/catch e estado de erro local.

### 9. Player e conteúdo de aula (se existir no diff)
- Sinal: iframe/player carregado de forma eager em página com vários vídeos. Correção: facade (thumbnail + clique) ou `loading="lazy"`.
- Sinal: progresso enviado só em `beforeunload` ou só ao final. Impacto: aluno perde progresso em fechamento de aba ou queda de rede. Correção: salvar em intervalo (throttle de 10-30 s) e em `visibilitychange`, com `navigator.sendBeacon`/`keepalive`, e retomar de fonte única.
- Sinal: `timeupdate` com `setState` a cada evento (~4 por segundo). Correção: ref para o valor e atualizar a UI em intervalo menor.
- Sinal: ausência de tratamento para buffering, erro de mídia e retomada. Correção: estados explícitos e retry do manifest.

## Fora de escopo

| Tema | Dono |
|---|---|
| Semântica, teclado, ARIA, contraste | review-a11y |
| XSS, authZ, segredos no bundle | review-seguranca |
| N+1, índices, cache de backend, fan-out sequencial no servidor | review-queries |
| Naming, complexidade cognitiva, fluxo de leitura | review-legibilidade |
| Shape de payload, breaking change de API, props host-remote como contrato | review-contratos |
| Retry de mutation, timeout, idempotência | review-resiliencia |
| Regra de negócio duplicada | review-dry |
| Tipos (`any`, `as`) | review-tipagem |
| Testes | test-audit |

Registre em `handoffs` com uma linha. Não desenvolva.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia `references/react.md` quando houver `react`/`next`. Leia `references/typescript.md` quando houver TypeScript.
3. Obtenha o diff. Com context packet do orquestrador, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`). Respeite `--path`.
4. Analise arquivo a arquivo contra o escopo. Priorize componentes, hooks, rotas, config de bundler e CSS-in-JS.
5. Verifique o contexto antes de reportar. Abra o componente pai para ver quem passa a prop. Abra o hook para ver o `queryKey` e as opções. Abra a config do bundler para confirmar `sideEffects` e `shared`. Confirme se o componente é memoizado e quantas instâncias existem.
6. Classifique com a rubrica abaixo e com `severity-rubric.md`. Estime cardinalidade (itens da lista, frequência do evento).
7. Emita no formato de `output-contract.md`: bloco `json` e markdown. Prefixo `FRT`, `agent: "review-front"`. Máximo de ~15 achados.

Standalone: mostre o markdown ao final. Não altere código.

## Rubrica de severidade

**BLOCKER**
- Componente de remote de Module Federation sem error boundary em tela crítica (sala de aula, checkout).
- Fetch em effect sem cleanup que grava em estado dado de outro recurso (race que mostra dado de outro aluno ou curso).
- Loop de render ou refetch infinito (função inline em deps de effect que dá `setState`).

**MAJOR**
- Context value recriado a cada render com mais de 20 consumidores em rota de uso frequente.
- Waterfall de 3 ou mais requests que poderiam ir em paralelo na rota de entrada.
- Import estático de lib de mais de 100 KB gzip no chunk inicial.
- `setInterval`/listener sem cleanup em componente que monta e desmonta várias vezes.
- Mutation sem invalidação, deixando tela com dado velho após escrita.
- Progresso do aluno salvo só no unload.

**MINOR**
- `useMemo`/`useCallback` ausente em lista de 50 itens com baixo custo por item.
- Imagem abaixo da dobra sem `loading="lazy"`.
- `staleTime` default em dado que muda uma vez por dia.
- `key={index}` em lista estática que nunca reordena.

**NIT**
- `memo` redundante em componente barato.
- Ordem de imports de lib, quando o formatter não cobre.

## Heurísticas anti-falso-positivo

- Meça a cardinalidade antes de pedir memoização. Lista de 5 itens com componente leve não precisa de `memo`.
- Função inline em `onClick` de elemento DOM nativo (`<button>`) custa quase nada. Reporte só quando vai para filho memoizado.
- `useEffect` que sincroniza com sistema externo (DOM API, WebSocket, analytics, `document.title`) é uso correto.
- `key={index}` em lista estática, sem reordenação, sem estado local nos itens, é aceitável.
- React Compiler ativo no repo (`babel-plugin-react-compiler`) dispensa `memo`/`useMemo` manuais. Não peça.
- `lazy()` com `useMemo` por dado montado pelo host é exceção documentada para remote que exige `dataSource`.
- `eslint-disable exhaustive-deps` com comentário de motivo e ref estável pode ser legítimo. Reporte só se a closure obsoleta for demonstrável.
- `LABErrorBoundary` (ou boundary equivalente do repo) fica reservado para remotes. Componente de módulo local, como modal, não precisa dele. Não peça boundary acima de código local.
- `PageErrorFallback` com `min-height` grande em seção interna é achado de layout. Reporte quando substituir seção em vez de página ou aba.
- Mudança de comportamento em hook compartilhado (`useFilterList`) afeta outras telas. Liste os consumidores no `problem` antes de classificar.
- Dado vindo de cache já populado (mesma `queryKey` em outro componente) elimina o waterfall aparente. Confirme as keys.
- Bug que só aparece no `device mode` do browser não prova problema em WebView. Confirme o ambiente.

## Ferramentas determinísticas opcionais

Rode só se instaladas no repo. A saída é insumo.

- `eslint-plugin-react-hooks`: verifique `ls node_modules/eslint-plugin-react-hooks`. Rode `npx eslint --no-eslintrc --parser @typescript-eslint/parser --plugin react-hooks --rule 'react-hooks/exhaustive-deps: warn' --rule 'react-hooks/rules-of-hooks: error' <arquivos do diff>`, ou o `yarn lint` do repo limitado aos arquivos do diff.
- Bundle analyzer: verifique `node_modules/.bin/webpack-bundle-analyzer` ou `source-map-explorer`. Rode `npx webpack-bundle-analyzer dist/stats.json --mode static -r /tmp/report.html` se `stats.json` existir. Sem build pronto, não gere build.
- Lighthouse CI: verifique `node_modules/.bin/lhci`. Rode `npx lhci autorun` só com a app já servida e config presente.
- `tsc --noEmit` valida props de componente quando houver `tsconfig`.

## Exemplos

### Achado 1

```json
{
  "id": "FRT-001",
  "agent": "review-front",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "Module Federation sem error boundary",
  "location": { "repo": "web-app", "file": "src/pages/main/Classroom/ClassroomTemplate.tsx", "lines": "88-96" },
  "evidence": "const RatingOverlay = lazy(() => import('ratings/RatingOverlay'));\n...\n<Suspense fallback={null}>\n  <RatingOverlay assetId={assetId} />\n</Suspense>",
  "problem": "O remote ratings é externo. Se o chunk falha (404, timeout) ou o remote lança, o erro sobe até o root e desmonta a sala de aula para todos os alunos que abrem a aula.",
  "fix": "<LABErrorBoundary>\n  <Suspense fallback={null}>\n    <RatingOverlay assetId={assetId} />\n  </Suspense>\n</LABErrorBoundary>",
  "auto_fixable": true,
  "effort": "S",
  "refs": ["CLAUDE.md: Micro-Frontend Fault Isolation"],
  "introduced_by_diff": true
}
```

```
### [BLOCKER] FRT-001 — Remote ratings sem error boundary
**Onde:** web-app/src/pages/main/Classroom/ClassroomTemplate.tsx:88-96 · **Confiança:** alta · **Esforço:** S
**Problema:** falha do remote derruba a sala de aula inteira.
**Correção:** envolver `Suspense` com `LABErrorBoundary`.
```

### Achado 2

```json
{
  "id": "FRT-002",
  "agent": "review-front",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "Effect: fetch sem cleanup (race)",
  "location": { "repo": "web-app", "file": "src/pages/main/Courses/useCourseSearch.ts", "lines": "14-24" },
  "evidence": "useEffect(() => {\n  api.get(`/courses?q=${term}`).then((res) => setResults(res.data));\n}, [term]);",
  "problem": "A cada tecla sai um request. Se a resposta de 'cardio' chega depois da de 'cardiologia', a lista mostra o resultado do termo antigo. O usuário vê resultados que não batem com o campo.",
  "fix": "useEffect(() => {\n  const controller = new AbortController();\n  api.get('/courses', { params: { q: term }, signal: controller.signal })\n    .then((res) => setResults(res.data))\n    .catch((err) => { if (!axios.isCancel(err)) setError(err); });\n  return () => controller.abort();\n}, [term]);\n// melhor: useQuery(['courses', term], ...) com debounce no term",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["react.dev: You Might Not Need an Effect"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

```tsx
useEffect(() => {
  document.title = `${course.name} | Lab`;
}, [course.name]);
```

Sinal aparente: `useEffect` com estado derivado. O effect sincroniza com um sistema externo (DOM do documento), sem `setState`. É o uso para o qual o effect existe. Não reportar.
