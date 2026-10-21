# DRY em React

## Hooks de fetch repetidos

- Sinal: 3+ hooks `useGetX` com o mesmo `useQuery`, mesma `queryKey` montada à mão, mesmo `select`, mesmo tratamento de erro.
- Impacto: chave de cache escrita à mão em 2 lugares. Um typo gera cache separado e refetch duplicado. A invalidação deixa de achar a query.
- Correção: factory de `queryKeys` por recurso (`courseKeys.detail(id)`) e hook único. Com react-query v3, cada hook mantém `enabled` próprio.

## Lógica de domínio dentro de componentes

- Sinal: o mesmo `useMemo` com a fórmula de progresso, prazo ou elegibilidade em 2+ componentes. Cálculo no componente que o BFF já devolve pronto.
- Impacto: telas mostram valores diferentes para o mesmo aluno.
- Correção: função pura em `helpers`/`domain`, ou hook `useCourseProgress`. Se o servidor já entrega o campo, remova o cálculo local.

## Componentes copiados

- Sinal: dois componentes com a mesma estrutura de JSX e estilos, diferindo em texto ou ícone. Modais com o mesmo esqueleto (título, corpo, rodapé com 2 botões).
- Correção: componente com props de dados (`title`, `icon`, `actions`) e `children`. Evite props que trocam estrutura (`variant` com 4 layouts): são componentes distintos.

## Anti-DRY em componentes

- Sinal: componente `<Card>` com `isCompact`, `withImage`, `showFooter`, `forAdmin` e 6 ramos de JSX. Cada nova tela adiciona uma flag.
- Correção: composição (`<Card><Card.Header/>...</Card>`) ou componentes separados que compartilham primitivos pequenos.
- Sinal: HOC ou render prop criado para reaproveitar 5 linhas.

## Estilos (styled-components)

- Sinal: o mesmo bloco de CSS (media query, truncamento de texto, foco visível) repetido em 4+ styled components. Breakpoints como literais (`@media (max-width: 768px)`) em vários arquivos.
- Correção: `css` helper compartilhado, mixin, token de tema (`theme.breakpoints.md`). Respeite o design system do repo: valor visual que existe como token do DS se consome do token, nunca se redeclara. Componente do DS com defeito se corrige no repo do DS.

## Strings de interface

- Sinal: a mesma mensagem de UI escrita em 2+ componentes, ou texto que o repo mantém em dicionário (`dictionary.json`, i18n) escrito inline.
- Correção: chave no dicionário. Interpolação por placeholder no padrão do repo.

## Analytics e flags

- Sinal: nome de evento (`track('click_cta_matricula')`) e chave de feature flag em strings soltas, repetidas.
- Impacto: typo gera evento órfão no dashboard ou flag sempre desligada.
- Correção: módulo `events.ts` e `flags.ts` com constantes `as const`. Atributos fixos de um componente montado em 2 rotas descrevem o fluxo, e o dispositivo vem de outro sinal.

## Module Federation

- Sinal: o tipo das props do remote copiado no host, ou o shape de dados do remote duplicado nos dois repos.
- Correção: o contrato de props fica em um tipo publicado pelo remote (ou em pacote de tipos). Sem pacote, cite a fonte no tipo local. Ordem de deploy é de review-contratos.
