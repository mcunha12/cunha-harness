# review-a11y — React 18, JSX, styled-components, react-router v6, Module Federation, design system externo

## 1. JSX: props e erros comuns
- `className` e `htmlFor` (não `class`/`for`). `htmlFor` ausente em `<label>` com `<input>` irmão perde a associação.
- `aria-*` em kebab-case no JSX (`aria-label`). `ariaLabel` não existe.
- Valor booleano de ARIA vira string: `aria-expanded={isOpen}` renderiza `"true"/"false"`. `aria-expanded={undefined}` remove o atributo; para widget que expande o estado `false` precisa aparecer.
- `tabIndex` com `I` maiúsculo. `tabindex` minúsculo no JSX é ignorado.
- `onClick` em `<div>`: exige `role`, `tabIndex={0}` e `onKeyDown`. Troque por `<button type="button">`.
- `<button>` dentro de `<form>` sem `type` envia o form. Declare `type="button"` nos que não enviam.
- `autoFocus` em carregamento de página muda o foco sem ação do usuário. Aceitável em dialog e campo de busca aberto por ação.
- `dangerouslySetInnerHTML`: exija revisão de headings, `alt` e links do HTML. XSS é de review-seguranca.
- Fragment vs `div` wrapper dentro de `<ul>`/`<table>`/`<dl>` quebra a árvore de acessibilidade. Use Fragment com `key`.
- `<img>` sem `alt` é erro; `<Image>` do Next também exige `alt`.

## 2. IDs únicos: `useId`
```tsx
function Field({ label, error, ...props }: FieldProps) {
  const id = useId();
  const errId = `${id}-err`;
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <input id={id} aria-invalid={!!error} aria-describedby={error ? errId : undefined} {...props} />
      {error && <p id={errId}>{error}</p>}
    </>
  );
}
```
Sinal de defeito: `id="email"` fixo em componente reusado em duas instâncias; `htmlFor` apontando para id que não existe no mesmo render.

## 3. Foco programático
- Gestão de foco usa `ref` + `useEffect`, nunca `document.getElementById(...).focus()`.
- Abrir dialog: foco no título (`tabIndex={-1}`) ou no primeiro controle; fechar: devolver ao disparador guardado em `useRef`.
```tsx
const triggerRef = useRef<HTMLElement | null>(null);
const open = () => { triggerRef.current = document.activeElement as HTMLElement; setOpen(true); };
const close = () => { setOpen(false); triggerRef.current?.focus(); };
```
- Sinal de defeito: modal de `<div>` com `position: fixed` e nenhum desses elementos. Correção: `<dialog>` nativo, ou Radix/Reach/react-aria/Headless UI (trap, Escape, `aria-modal`, scroll lock já incluídos).
- Portal (`createPortal`) para modal move o DOM para fora do container; o resto da app precisa de `inert`/`aria-hidden` enquanto aberto. Bibliotecas tratam; modal manual não trata.
- Erro de submit: mova o foco ao primeiro campo inválido:
```tsx
const firstInvalid = formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
firstInvalid?.focus();
```
- Lista com item removido: foco vai ao próximo item ou ao título; sem isso cai no `body`.

## 4. SPA e react-router v6
- Troca de rota não recarrega a página. O leitor de tela não anuncia. Padrão mínimo:
```tsx
function RouteAnnouncer() {
  const { pathname } = useLocation();
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => { headingRef.current?.focus(); }, [pathname]);
  return null;
}
// cada página: <h1 ref={headingRef} tabIndex={-1}>Título</h1>
// ou região <div role="status" aria-live="polite" className="sr-only">{titulo}</div>
```
- Atualize `document.title` por rota (`useEffect`, `react-helmet`). Título igual em toda rota falha 2.4.2.
- Link para âncora (`#main`) em SPA com `BrowserRouter` precisa de `<a href="#main">` que funciona sem interceptar a navegação do router. Teste o skip link no layout.
- `<Link>` renderiza `<a href>`: correto. `<div onClick={() => navigate(...)}>` não renderiza link. Troque por `<Link>`.
- `<NavLink>` marca `aria-current="page"` automaticamente na rota ativa. Menu feito à mão replica `aria-current`.
- Redirect com `<Navigate>` após ação deve manter o contexto anunciado (toast `role="status"`).
- Guard de rota que redireciona sem aviso muda a página sem explicação. Em fluxos longos, informe o motivo.

## 5. Regiões vivas em React
```tsx
// sinal de defeito: região criada junto com o texto
{message && <div role="status">{message}</div>}
// correção: região montada antes, texto muda dentro
<div role="status" aria-live="polite" aria-atomic="true">{message}</div>
```
- `role="alert"` para erro que exige ação imediata. `role="status"` para sucesso, contador, progresso.
- Toast que some em menos de 5 s ou com ação (Desfazer) falha 2.2.1; pause no hover e no foco, e deixe a ação alcançável por teclado.
- Biblioteca de toast (react-toastify, sonner, notistack) já inclui regiões vivas; confira a config `role` e `ariaLive`.
- Skeleton/spinner: `aria-busy="true"` na região e `<span className="sr-only">Carregando…</span>` ou `role="status"`.
- Contador ao vivo de resultados ("12 cursos encontrados") em `role="status"`.

## 6. Formulários com react-hook-form / Formik
- Mensagem de erro dinâmica: `aria-invalid` + `aria-describedby` apontando para o id da mensagem; mensagem montada junto do campo.
- `register` e `Controller` preservam o `ref`; `Controller` com componente do DS precisa repassar `ref`/`id`/`aria-*` ao `<input>` real.
- `errors` do `formState` devolve nome do campo; use texto humano. `shouldFocusError` do RHF (padrão `true`) já foca o primeiro erro: não desligue sem substituto.
- `mode: 'onChange'` anuncia erro a cada tecla ao leitor de tela se há região viva por campo. Prefira `onBlur`/`onSubmit` com resumo.
- Campo composto (data com três inputs, telefone com DDD) em `<fieldset><legend>`.
- `disabled` durante submit: mantenha o foco no botão com `aria-disabled="true"` e `aria-busy`, em vez de `disabled` que derruba o foco.

## 7. styled-components e CSS-in-JS
- `outline: none` dentro de componente estilizado: procure `&:focus-visible` irmão. Sem ele, MAJOR.
```tsx
const Btn = styled.button`
  &:focus-visible { outline: 2px solid ${(p) => p.theme.colors.focus}; outline-offset: 2px; }
`;
```
- Troca de tag com `as` muda a semântica (`as="div"` num botão estilizado remove o `button`). Em `styled.div` com `onClick`, use `as="button"` ou crie `styled.button`.
- Props de estilo transientes `$prop` evitam atributo estranho no DOM; atributo inválido com nome parecido com ARIA (`aria-foo`) polui a árvore.
- `${media}` com `hover` e sem `focus` no mesmo seletor revela estado só em hover.
- Token de cor do tema usado em texto: calcule contraste com fundo do mesmo tema. Tema escuro e claro são dois pares.
- `@media (prefers-reduced-motion: reduce) { animation: none; transition: none; }` em `keyframes` e transições do componente.
- `font-size: 12px` fixo em texto de conteúdo. Converta para `rem` quando o repo usa `rem`.

## 8. Module Federation e remotes
- O remote entrega a própria árvore. O host fornece a landmark e o heading da página; o remote não duplica `<main>` nem `<h1>`. Dois `<main>` na página é defeito do contrato host/remote.
- O fallback do error boundary de um remote (`LABErrorBoundary`) tem texto legível e botão "Tentar novamente" focável. Um fallback só com ícone falha o nome acessível.
- O estado de carregamento do `Suspense` é anunciado (`role="status"`).
- Foco ao montar o remote: o remote não rouba foco no mount. Se abre um overlay, devolve o foco ao fechar.
- Estilos globais do remote (`outline: none` em `*`) vazam para o host. Procure reset global no CSS do remote.

## 9. Design system externo
- Abra o componente no `node_modules` ou na doc do DS antes de reportar. O DS pode entregar role, foco e `aria-*`.
- Props de a11y do componente (`aria-label`, `title`, `hideCloseButton`) existem para uso. Preencha no consumidor.
- Defeito no componente do DS: handoff `{"to": "repo do design system", ...}` com o critério violado. Sem patch local, sem `!important` sobre `outline` do DS.
- `Tag`/`Chip` interativo sem prop de forma: o contorno por `variant="custom"` com `div` próprio exige `role`, `aria-*` e teclado. Para grupo de opções, `role="radiogroup"` ou `"group"` no container e roving tabindex (um tab stop, setas navegam). Sem isso, MAJOR.
- Ícone de fechar do `Sheet`/`Modal` escondido por CSS e não pela prop correta (`hideCloseButton`) remove só o visual e mantém o botão no teclado.

## 10. Next.js (só se `next` nas deps)
- `next/link` renderiza `<a>`. `next/image` exige `alt`.
- `app/` com `layout.tsx`: um `<main>` por layout; o título por `metadata`/`generateMetadata`.
- Anúncio de rota: o Next injeta `route announcer` (`next-route-announcer`) que lê o `<title>`/`<h1>`. Título duplicado entre rotas anula o anúncio.
- Streaming com `loading.tsx`: skeleton com `role="status"` e texto.

## 11. Testes de a11y em Jest e Testing Library
- Consultas por papel (`getByRole('button', { name: 'Fechar' })`) validam nome acessível no teste. Teste que usa `getByTestId` para botão não prova nome acessível.
- `jest-axe`: `expect(await axe(container)).toHaveNoViolations()` em componente isolado. Cobertura de regras que dependem de CSS (contraste) é fraca em jsdom.
- Qualidade do teste é de test-audit. Sugira em `handoffs` apenas.
