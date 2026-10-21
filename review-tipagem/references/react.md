# Tipagem em React (18, react-query v3, styled-components, react-router v6)

## Props e componentes

- Props em `interface`/`type` nomeado, sem `any`. `React.FC` não é obrigatório. Se usado, `children` não é implícito no React 18.
- Variantes mutuamente exclusivas como união discriminada:

```tsx
type Props =
  | { variant: 'link'; href: string; onClick?: never }
  | { variant: 'button'; onClick: () => void; href?: never };
```

  Sinal: três props opcionais (`href?`, `onClick?`, `to?`) que o componente trata com `if` em cadeia. Impacto: combinação inválida compila.
- Wrapper de elemento nativo: `ComponentPropsWithoutRef<'button'>` mais props próprias. `React.HTMLAttributes` sem o elemento perde atributos específicos.
- `forwardRef<HTMLButtonElement, Props>`: os dois genéricos na ordem (ref, props).
- Componente polimórfico (`as`): `ElementType` e `ComponentPropsWithoutRef<T>` com genérico. `as?: any` anula.
- Handlers: `React.ChangeEvent<HTMLInputElement>`, `React.MouseEvent<HTMLButtonElement>`, `React.FormEvent<HTMLFormElement>`. `(e: any)` é achado. `e.target as HTMLInputElement` é aceito. `e.currentTarget` já vem tipado e evita o cast.
- Render prop e `children` como função: tipar o argumento.
- `PropsWithChildren<Props>` para `children` explícito.
- `key` e `ref` não estão em `Props`.

## Hooks

- `useState<Foo>()` devolve `Foo | undefined`. `useState<Foo>({} as Foo)` mente. Use `useState<Foo | null>(null)` com tratamento de `null`, ou estado discriminado.
- `useState` com valor inicial vazio infere `never[]` para `[]`: `useState<Item[]>([])`.
- `useRef<T>(null)` devolve `RefObject<T>` (leitura). `useRef<T | null>(null)` devolve `MutableRefObject`. `useRef<number>()` devolve `MutableRefObject<number | undefined>`.
- `useReducer` com ação em união discriminada e `assertNever` no default do reducer.
- `useCallback`/`useMemo` herdam o tipo do retorno. Sinal: `useCallback((x: any) => ...)`.
- `useContext` com `createContext<Ctx | null>(null)` e hook que lança quando `null`. `createContext({} as Ctx)` é achado.
- Hook customizado que devolve tupla: `as const` no retorno, ou tipo de retorno explícito. Sem isso, o retorno vira `(A | B)[]`.
- `useEffect` async: o callback não pode ser `async` (devolve promise em vez de cleanup). O compilador avisa. O tema de effect é do review-front.

## react-query v3

- `useQuery<TQueryFnData, TError, TData, TQueryKey>`. Os genéricos importam quando há `select`. `useQuery<Foo>` com `queryFn` devolvendo `any` anula o genérico: tipe o retorno do `queryFn` ou do client.
- `TError` não informado é `unknown` no v3 e `Error` em versões antigas. Estreite antes de usar `error.message`.
- `data` é `TData | undefined`. Com `enabled: false` ou `isLoading`, não acesse sem guard. O estado `idle` do v3 mantém `isLoading: false` e `data: undefined`. Use o `status` como discriminador (`status === 'success'` estreita `data`).
- `useMutation<TData, TError, TVariables, TContext>`: `TVariables` não informado vira `void` e `mutate(payload)` não compila, ou vira `unknown`. Tipar `TVariables` com o tipo do payload.
- `queryClient.getQueryData<Foo>(key)` é um cast: devolve `Foo | undefined` sem verificação. Encapsule em helper por chave, e mantenha as chaves em factory tipada (`const keys = { enrollment: (id: string) => ['enrollment', id] as const }`).
- `setQueryData` com `updater` tipado e retorno compatível com a query.
- `queryKey` como array `as const` para inferência.
- Tipos de resposta do client: gerados ou `z.infer`. A validação em runtime é do review-contratos.

## styled-components

- Props de estilo tipadas no template: `styled.div<{ $active: boolean }>`. O prefixo `$` (transient prop) evita repassar ao DOM. Sem o genérico, `props.$active` é erro de tipo ou `any`.
- `DefaultTheme` aumentado por `declare module 'styled-components' { export interface DefaultTheme { ... } }`. Sem a declaração, `theme.colors.x` é erro ou `any`. Sinal: `(props: any) => props.theme.x`.
- `styled(Component)` exige que `Component` aceite `className`. Props do componente envolvido continuam tipadas.
- `css` helper com interpolação de função: tipar `css<{ $x: boolean }>`.
- `as` e `forwardedAs` perdem tipo sem genérico.

## react-router v6

- `useParams<{ enrollmentId: string }>()` devolve `Partial` (todo parâmetro é `string | undefined`). Sinal: `useParams() as { id: string }`. Correção: guard `if (!id) return <Navigate .../>` ou helper que lança.
- `useSearchParams` devolve `string | null`. Converta e valide números e enums.
- `useNavigate` com `state` livre: tipe o `state` e leia via `useLocation().state as State | null` encapsulado em hook com guard.
- `loader` e `action` (data routers): `LoaderFunctionArgs`. `useLoaderData()` devolve `unknown`. Cast `as Awaited<ReturnType<typeof loader>>` fica em um hook por rota.

## Eventos, DOM e refs

- `document.querySelector<HTMLInputElement>('...')` tipa e devolve `T | null`.
- `event.target` é `EventTarget`. Estreite com `instanceof` ou use `currentTarget`.
- Evento customizado: `CustomEvent<Detail>` com declaração em `WindowEventMap`.
- `window.postMessage` recebe `MessageEvent<unknown>`: estreite o `data`.

## Module Federation

- Remote importado com `lazy(() => import('remote/Foo'))` precisa de `declare module 'remote/Foo'` com o tipo das props. Sinal: `declare module 'remote/Foo';` sem corpo (tudo `any`). Correção: tipar as props, ou consumir o pacote de tipos do remote. O contrato host-remote é do review-contratos.
- `loadRemoteModule` genérico: `loadRemoteModule<{ default: ComponentType<Props> }>(...)`.

## Next (se `next` nas deps)

- `params` e `searchParams` de page: `Promise<...>` nas versões recentes (15+). Sinal: acesso síncrono sem `await`.
- `NextPage`/`Metadata` tipados. Server Action recebe `FormData`: parse com schema.
- Props passadas de Server para Client Component precisam ser serializáveis: tipo com função, `Date`, `Map` ou classe falha em runtime. A regra é do review-front.
