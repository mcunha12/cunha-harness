# review-legibilidade — React, JSX e hooks

Render, performance e effects são de review-front. Aqui entra a leitura do componente.

## 1. Tamanho e forma do componente
- Componente com 150+ linhas de JSX num único `return` perde o mapa. Extraia subcomponentes nomeados pelo conceito (`CourseHeader`, `LessonList`). Uma função de render interna chamada como `{renderRow()}` é aceitável; componente definido dentro do render é defeito de front (remount).
- Um componente por arquivo, quando o repo adota. Em arquivo novo ou tocado, a regra vale; arquivos legados que já violam ficam como estão.
- Arquivo `index.tsx` com vários componentes: nome do arquivo não diz o conteúdo. Extraia.

## 2. Ordem no corpo do componente
Quando o repo usa a convenção, siga:
1. hooks de estado e referência (`useState`, `useRef`, `useMemo`, `useCallback`, hooks de query);
2. consts derivadas;
3. handlers;
4. effects, se o repo os põe depois;
5. `return`.
Exceção: const lida dentro de hook anterior (inicializador eager de `useState`, deps de `useMemo`/`useCallback`) vem antes dele. Fora de ordem causa `ReferenceError` de TDZ. Confirme a direção da dependência antes de pedir reordenação.

## 3. JSX legível
- Ternário aninhado em JSX: variável antes do `return`, ou componente, ou early return.
```tsx
// antes
return loading ? <Spinner /> : error ? <Error /> : data.length ? <List data={data} /> : <Empty />;
// depois
if (isLoading) return <Spinner />;
if (error) return <ErrorState error={error} />;
if (data.length === 0) return <EmptyState />;
return <List data={data} />;
```
- `cond && <X/>` encadeado com 3+ condições: variável `shouldShowBanner`.
- `list.length && <X/>` renderiza `0`. Use `list.length > 0 &&`. Bug e leitura.
- `.map` com bloco de 10+ linhas no JSX: extraia o item como componente.
- Props espalhadas (`{...props}`) em muitos níveis escondem o contrato. Repasse as props usadas, ou tipo nomeado.
- Prop com 8+ campos passados a um componente: agrupe em objeto de domínio ou divida o componente.
- Prop booleana nomeada `flag`/`mode`: `isCompact`, `variant="compact"`.
- Valor de estilo inline com lógica: extraia para `styled-component` com prop transiente (`$isActive`) ou função de estilo nomeada.

## 4. Hooks customizados
- Nome `useX` diz o conceito (`useCourseProgress`). `useData`, `useHelper`, `useCommon` não dizem.
- O retorno é um objeto nomeado (`{ progress, isLoading }`) quando tem 3+ valores; tupla quando são 2 (par estado/setter).
- Hook que faz fetch, transforma, formata e escuta evento: 4 hooks nomeados.
- Callback com mais de 10 linhas dentro de `useEffect`/`useCallback`: extraia função nomeada. A função nomeada vira o comentário do que o effect faz.
- Effect com comentário de motivo (`// sincroniza com document.title`) é bom. Effect de 40 linhas sem nome: extraia.

## 5. Nomes em React
- Componente: `PascalCase` por conceito de UI/domínio (`EnrollmentCard`). `Container`, `Wrapper`, `Component`, `Page2`, `NewX` não dizem.
- Handler `handleSubmit`, prop `onSubmit`. Prop `handleX` vinda de fora ou handler `onX` interno: inconsistência.
- Estado e setter em par (`[isOpen, setIsOpen]`). `[open, setOpened]` ou `[state, setThing]`: nome que não casa.
- Context e hook: `CourseContext` e `useCourse`. Provider em `CourseProvider`.
- Evento: `event`/`e` em handler curto; tipo explícito (`React.ChangeEvent<HTMLInputElement>`).
- Arquivos de teste e estilo vizinhos com o mesmo nome base (`CourseCard.test.tsx`, `CourseCard.styles.ts` se o repo adota).

## 6. styled-components e estilo
- Nome do styled component diz o papel (`Title`, `ProgressTrack`, `ActionBar`), não a tag (`Div`, `StyledDiv`, `Wrapper2`).
- Interpolação com lógica condicional de 3+ ramos: função de estilo nomeada ou `variant` mapeado.
```tsx
const variantStyles = { primary: css`...`, ghost: css`...` };
const Button = styled.button<{ $variant: keyof typeof variantStyles }>`${(p) => variantStyles[p.$variant]}`;
```
- Valor de design repetido literal (`#1a73e8`, `16px`) no lugar do token: legibilidade e DRY. Token do tema diz o papel. Contraste e a11y são de review-a11y.
- Seletor aninhado em 4+ níveis: achate.

## 7. Dicionário e textos
- String visível ao usuário no `dictionary.json` do repo quando o repo adota; placeholder `{{var}}` com `.replace()` conforme o padrão local. Texto solto no JSX em repo que usa dicionário diverge do padrão local: MINOR. Módulos com cópia em `*.constants.ts` locais (exceção aceita do repo) ficam como estão.
- Chave do dicionário nomeia o lugar e o papel (`classroom.comments.emptyState`), sem número.

## 8. Next.js
- `page.tsx`/`layout.tsx` com lógica de negócio de 100+ linhas: extraia para função/serviço nomeado.
- Arquivo especial (`loading.tsx`, `error.tsx`, `not-found.tsx`) nomeia o componente exportado de forma legível.
- Rotas dinâmicas `[id]`: o nome do segmento diz o conceito (`[courseSlug]`, não `[id]` quando há mais de um id na URL).
