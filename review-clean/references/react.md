# Clean em React

## Componentes (SRP)

- Sinal: componente com fetch, transformação de dados, estado de formulário e JSX de 150+ linhas. Impacto: teste exige servidor mockado e DOM, e a regra não se testa isolada.
- Correção: hook de dados (`useCourseData`), função pura de regra (`buildCourseSummary`), componente apresentacional que recebe props. O container liga os 3.
- Sinal: componente que decide regra de negócio (elegibilidade, preço) dentro do JSX. Correção: função pura em módulo de domínio, testada sem DOM.

## Props (ISP e long parameter list)

- Sinal: 10+ props, ou objeto inteiro (`user`) passado para um componente que usa 1 campo. Correção: passar só o campo, agrupar props por papel (`header`, `actions`), ou composição com `children` e slots.
- Sinal: props booleanas que alternam estrutura (`isEdit`, `isAdmin`, `isCompact`). Flag argument. Correção: componentes separados que compartilham primitivos.
- Sinal: `{...props}` repassado a 3 níveis. Correção: tipar o que cada nível consome.

## Efeitos colaterais

- Sinal: efeito durante o render (`setState`, mutação de ref, `track()`, escrita em `localStorage` no corpo do componente). Impacto: dispara a cada render e duplica em StrictMode. BLOCKER quando grava dado ou dispara evento de negócio.
- Sinal: `useMemo` ou `useState(initializer)` com efeito. Correção: `useEffect` ou handler de evento.
- Sinal: função `getX` de hook ou helper chamada no render que muta objeto do cache do react-query (`data.items.sort(...)`). Impacto: corrompe o cache compartilhado. Correção: `[...data.items].sort(...)` dentro de `useMemo`/`select`.
- Sinal: mutação de props ou de estado (`state.list.push(x); setState(state)`). Correção: novo array/objeto.

## Hooks

- Sinal: hook com 6+ valores de retorno desconexos (`{ data, isOpen, toggle, form, submit, errors, step }`). Divergent change. Correção: hooks menores por tema.
- Sinal: hook que dispara efeito de escrita ao ser chamado (`useTrackPageView` está certo, `useUser` que faz POST não). Nome com `use` e verbo de leitura não escreve.
- Sinal: hook que lê `window`, `document` e `localStorage` direto, sem seam. Correção: parâmetro injetável ou hook de infra único.
- Ordem das regras de hooks é verificada pelo linter. Aqui só se reporta o design.

## Estado e derivação

- Sinal: dois `useState` que precisam mudar juntos (`status`, `error`, `data`). Correção: `useReducer` com máquina de estado ou union discriminada (`{status:'error', error}`).
- Sinal: estado derivado guardado e sincronizado por efeito. O dono é review-front. Aqui só a refatoração de design quando houver SRP envolvido.

## Functional core em UI

- Camada pura: `domain/*.ts` com funções sem React.
- Camada de dados: hooks de query/mutation.
- Camada de apresentação: componentes sem fetch.
- Teste da camada pura com tabelas. Teste do componente com props fixas.

## Smells recorrentes

- Message chain: `props.course.modules[0].lessons[0].video.url` espalhado. Correção: seletor/mapper no hook.
- Data clumps: `(courseId, enrollmentId, packId)` passados por 6 componentes. Correção: objeto de contexto (`CourseRef`) ou Context quando o valor atravessa 3+ níveis.
- Speculative generality: `<DataTable columns renderRow renderHeader renderEmpty ...>` com um único uso. Correção: componente concreto.
- Dead code: props não lidas, estados sem leitura, componentes sem import. Verifique com `git grep` antes.
- Um componente por arquivo é convenção comum. Siga a convenção do repo (`CLAUDE.md`).

## Singletons e contexto

- Sinal: `let` de módulo guardando estado de UI compartilhado entre instâncias. Correção: Context, store, ou ref por instância.
- Sinal: Provider que cria objeto novo a cada render (`value={{ a, b }}`). O dono é review-front.
