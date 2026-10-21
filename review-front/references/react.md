# review-front — React 18, react-query v3, styled-components, react-router v6, Module Federation, Next

## 1. Render e memoização

### Context value instável
```tsx
// sinal
<ThemeCtx.Provider value={{ theme, toggle }}>{children}</ThemeCtx.Provider>
```
Impacto: o objeto novo a cada render do provider re-renderiza todo consumidor. Correção:
```tsx
const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);
```
Quando o Context mistura dado que muda (estado) e dado estável (dispatch), divida em dois Contexts.

### Props instáveis para memo
- `memo(Child)` recebendo `style={{...}}`, `options={[...]}`, `onChange={() => ...}` anula o memo. Estabilize com `useMemo`/`useCallback` ou mova a constante para fora do componente.
- Constante literal que nunca muda vai para o escopo do módulo, sem hook.
- `useCallback` cujo consumidor não é memoizado nem dep de effect não ganha nada. Remover é MINOR no máximo.

### Estado no lugar errado
- Estado que só um filho usa e vive no pai faz o pai e todos os irmãos renderizarem. Desça o estado.
- Componente com `children` estáveis passados de fora não re-renderiza os `children` quando o estado interno muda. Use esse padrão antes de `memo`.

### Key
- Key por índice em lista editável, reordenável ou com inputs. Correção: id do dado.
- `key` em Fragment de `map` ausente gera warning e reconciliação ruim.
- `key` para forçar reset de estado (`<Form key={courseId}/>`) é uso correto.

### Listas grandes
- Mais de ~100 linhas com componente não trivial: virtualização. Mais de 1 000 sem virtualização é MAJOR.
- `React.memo` na linha com `useCallback` nos handlers por id (um handler recebendo o id) evita criar closure por linha.

## 2. Effects ("You Might Not Need an Effect")

| Sinal | Correção |
|---|---|
| `useEffect(() => setX(f(props)), [props])` | `const x = f(props)` ou `useMemo` |
| `useEffect(() => { if (data) onDone(data) }, [data])` | chamar `onDone` onde o dado é produzido |
| `useEffect(() => { setPage(0) }, [filter])` | resetar no handler do filtro, ou `key` |
| `useEffect(() => { post(); }, [submitted])` | executar no handler de submit |
| fetch em effect | hook de query do repo, ou cleanup com `AbortController` |

Regras do StrictMode (React 18 dev): o effect monta, desmonta e monta de novo. Effect que dispara analytics, POST ou contador sem guard duplica. Correção: mover para handler, ou guard idempotente no servidor.

### Ref de disparo único sobre duas fontes assíncronas
Sinal: `const fired = useRef(false)` que dispara quando o primeiro dado chega, com o segundo dado ainda `undefined`. Impacto: o POST sai com id `undefined` e nunca corrige. Correção: dois refs, um para "disparou" e outro para "disparou com ids completos"; o segundo dispara a correção quando os ids chegam.

### Callback de SDK em effect
```tsx
useEffect(() => {
  let cancelled = false;
  posthog.getSurveys((surveys) => { if (!cancelled) setSurveys(surveys); });
  return () => { cancelled = true; };
}, []);
```
Sem a flag, `setState` roda após unmount.

### Dismiss animado com timers
Sinal: callback de `close`/`dismiss` que limpa timers rastreados e agenda um `setTimeout` próprio de conclusão. Impacto: dois gatilhos coincidentes (clique e timeout) disparam a conclusão duas vezes. Correção: um único ponto de conclusão idempotente, com ref `completed`.

### Deps
- `eslint-disable react-hooks/exhaustive-deps` sem comentário de motivo: MINOR. Com closure obsoleta demonstrável: MAJOR.
- Objeto/array/função nas deps recriados a cada render causa loop quando o effect faz `setState`. Estabilize.
- Valor que deve ler o último estado sem re-disparar: `useRef` atualizado em effect, ou o padrão `useEffectEvent` quando disponível na versão.

## 3. react-query v3

- Chave: `['course', courseId, enrollmentId]` inclui todo parâmetro que muda a resposta. Falta de parâmetro mostra dado de outra entidade.
- `enabled: false` (ou `enabled: !!id` com id vazio) deixa a query em `idle`. `isLoading` e `isError` valem `false`, `data` vale `undefined`. Componente `if (!data) return null` some em silêncio. Correção: tratar `isIdle`, ou renderizar skeleton quando `!enabled`.
- `isLoading` na v3 vale `true` só no primeiro carregamento sem dado. Para refetch use `isFetching`.
- `useQuery` dependente (`enabled: !!user`) cria waterfall legítimo. Waterfall sem dependência de dado é o defeito: dispare em paralelo.
- Mutation: `onSuccess` invalida a key afetada (`queryClient.invalidateQueries(['courses'])`). Escrita sem invalidação deixa a tela velha.
- Update otimista:
```tsx
onMutate: async (next) => {
  await queryClient.cancelQueries(key);
  const prev = queryClient.getQueryData(key);
  queryClient.setQueryData(key, next);
  return { prev };
},
onError: (_e, _v, ctx) => queryClient.setQueryData(key, ctx?.prev),
onSettled: () => queryClient.invalidateQueries(key),
```
Sem `onError` com rollback, a UI mantém o dado da escrita falha.
- `retry` default da v3 é 3 em queries. Mutation sem retry por padrão. Mutation não idempotente com `retry` ligado duplica efeito (dono: review-resiliencia).
- `select` com função inline recalcula a cada render. Memoize com `useCallback` quando custoso.
- `initialData` sem `staleTime` dispara refetch imediato. Combine com `staleTime`.
- `keepPreviousData: true` em paginação evita flicker. Sem ele a tabela pisca ao mudar de página: MINOR.
- `refetchOnWindowFocus` default `true`: em query cara e estável, defina `staleTime` alto.
- `useQueries` para lista dinâmica, em vez de hook em loop (quebra regras de hooks).

## 4. Suspense, lazy e Module Federation

- `lazy()` criado no escopo do módulo, uma vez. `lazy()` no corpo do componente gera tipo novo a cada render e remonta o filho.
- Exceção: remote que exige valor montado pelo host (`dataSource`). Crie com `useMemo` por dep explícita e documente.
- Todo remote (`loadRemoteModule`, `import('remote/X')`) fica dentro de boundary de erro + `Suspense`, no nível da página e no wrapper do componente remoto.
- Não remova boundary de integração com remote sem equivalente. Remoção exige justificativa explícita no MR. É BLOCKER em tela crítica.
- Boundary de remote não vai em componente local (modal, card). Reservado para MF.
- `shared` do `ModuleFederationPlugin`: `react`, `react-dom`, `styled-components` com `singleton: true` e `requiredVersion` fixo. Alteração de versão ou `singleton` no diff exige confirmação de que host e remotes alinham.
- Mudança de props que o host envia ao remote é contrato: o remote precisa ir à produção antes do host (dono: review-contratos; registre em `handoffs`).
- `Suspense` sem `fallback` útil em rota inteira gera tela em branco durante o chunk load. Use skeleton do layout.
- `startTransition` em navegação pesada evita fallback do Suspense já exibido.

## 5. react-router v6
- `useNavigate` dentro de effect para redirecionar guard de rota causa flash de conteúdo protegido. Guard que depende de flag assíncrona (Unleash) espera `flagsReady` e redireciona de forma síncrona com `<Navigate replace />`.
- `loader`/`lazy` de rota com `createBrowserRouter` buscam dado antes do render e evitam waterfall pai-filho. Fetch em effect de rota filha serializa.
- Componente montado em duas rotas (`/curso/:id/chat` e `/modular/:id/chat`) mantém estado entre rotas quando o elemento é o mesmo na mesma posição. Use `key` para forçar reset.
- `useSearchParams` para filtro e paginação. Estado local perde ao voltar.
- `useLocation` e `useNavigate` fora de `RouterProvider` lançam erro (widget global fora do router). Use a instância do router.
- Anúncio de rota para leitor de tela e foco: dono é review-a11y.

## 6. styled-components v5

### Props transientes
```tsx
// sinal: prop de estilo vaza para o DOM
const Box = styled.div<{ active: boolean }>`color: ${(p) => (p.active ? 'red' : 'inherit')};`;
// correção
const Box = styled.div<{ $active: boolean }>`color: ${(p) => (p.$active ? 'red' : 'inherit')};`;
```
Impacto: `active` chega no DOM como atributo, gera warning "React does not recognize the prop" ou atributo inválido no HTML. Prefixe com `$` em toda prop que só estiliza.

### Estilo dinâmico por valor contínuo
```tsx
// sinal: gera uma classe CSS nova por valor (progresso 0..100, posição)
const Bar = styled.div<{ $w: number }>`width: ${(p) => p.$w}%;`;
// correção
const Bar = styled.div.attrs<{ $w: number }>((p) => ({ style: { width: `${p.$w}%` } }))``;
```
Impacto: 101 classes injetadas no `<style>`, recálculo de estilo a cada tick (barra de progresso de vídeo, drag). Use `attrs` com `style`, ou CSS variable.

### Componente criado dentro do render
Sinal: `const Wrapper = styled.div\`\`` dentro do corpo de componente, ou `styled(Comp)` dentro do render. Impacto: tipo novo a cada render, remount da subárvore e perda de estado/foco. Correção: escopo do módulo.

### Outros
- `css` helper e interpolação de função em CSS com muitos consumidores: custo proporcional às instâncias. Em lista de 500 itens, prefira classe estática com variável.
- `createGlobalStyle` com função de props recalcula o `<style>` global a cada mudança de props.
- Singleton: `styled-components` duplicado (duas versões no bundle) quebra `ThemeProvider` e injeta estilos duas vezes. Confirme `shared.singleton` em MF e `resolutions` no `package.json`.
- Componente do design system externo não recebe patch local. Defeito do DS vira issue no repo do DS.
- `styled(Comp)` exige que `Comp` repasse `className`. Sem isso o estilo não aplica.
- Tema acessado por `props.theme.x` em muitos nós causa re-render por troca de tema. Aceitável; reporte só em lista grande.

## 7. Formulários
- `react-hook-form`: `watch()` sem argumento re-renderiza o form em cada tecla. Use `useWatch({ name })` no componente que precisa, `register` para campos não controlados, `Controller` só quando necessário.
- Formik com `validateOnChange` em form de 30+ campos custa por tecla. Reduza para `onBlur`.
- Campo controlado em `<input value=...>` com estado no pai de tela grande: isole em componente.

## 8. Next.js (só se `next` nas deps)
- Server Components por padrão. `"use client"` no topo só quando há estado, efeito ou handler. `"use client"` em layout inteiro por causa de um botão arrasta toda a subárvore para o bundle do cliente. Extraia o botão.
- Dado sensível passado de server para client component é serializado no payload RSC (visível). Passe só os campos usados.
- `fetch` no server com `cache: 'no-store'` em dado estático perde o cache. `revalidate` coerente com a volatilidade.
- `next/image` com `width`/`height` ou `fill` + `sizes`. Imagem LCP com `priority`.
- `next/font` em vez de `<link>` de fonte externa evita CLS e request extra.
- `useSearchParams` em client component sem `Suspense` quebra o build estático da rota.
- Hydration mismatch: `Date`, `Math.random`, `window`, `localStorage` no render inicial. Leia em effect ou marque `suppressHydrationWarning` com motivo.
- Waterfall no server: `await a; await b;` independentes. Use `Promise.all`.

## 9. Armadilhas de lógica de render
- `cond && <X/>` com `cond` numérico (`list.length && ...`) renderiza `0`. Correção: `list.length > 0 &&`.
- Condição de paginação do tipo `!isMobile && !isTablet && list.length > PAGE_SIZE` falha no desktop com lista pequena. Bug relatado como "só mobile" costuma valer para todo caso que cai no `else`. Teste a tabela de verdade completa.
- Componente que devolve `null` quando `data` é `undefined` mascara estados `idle` e erro.
- Estado em `useState(initialFromProps)` ignora mudança posterior da prop. Use `key` ou derive.
