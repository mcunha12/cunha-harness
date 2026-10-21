# review-front — TypeScript aplicado ao front

Só o que muda saúde de runtime do front. Tipagem em si (any, as, branded types) é de review-tipagem; registre em `handoffs`.

## 1. Props e componentes
- Sinal: props tipadas como `any`, `object` ou `Record<string, unknown>` em componente memoizado. Impacto: o compilador não pega prop trocada, e o `memo` não tem como ser verificado por tipo. Correção: tipo explícito por prop.
- Sinal: `React.FC` com `children` implícito em código novo. Correção: declarar `children?: ReactNode` quando aceita, e função normal.
- Sinal: union discriminada ignorada em estado de tela (`{ loading: boolean; error?: Error; data?: T }`). Impacto: estados impossíveis (`loading` e `data` juntos) renderizam errado. Correção: `{ status: 'loading' } | { status: 'error'; error: Error } | { status: 'success'; data: T }` e `switch` exaustivo. Com react-query v3, use `status` (`idle | loading | error | success`) e trate `idle`.
- Sinal: handler tipado `(e: any) => void`. Correção: `React.ChangeEvent<HTMLInputElement>` ou tipo do evento específico.

## 2. Fronteira de dados externos
- Sinal: `JSON.parse(x) as Foo`, `res.data as Foo`, `await res.json()` sem validação, em dado de `localStorage`, `postMessage`, URL, query string ou remote de MF. Impacto: dado fora do formato quebra o render com `undefined.x` em produção. Correção: parse com schema (`zod`) ou type guard, e try/catch com estado de erro.
- Sinal: `useParams()`/`useSearchParams()` usados como `string` garantida. Impacto: `undefined` em rota sem o param. Correção: narrow antes do uso e `enabled: !!id` na query.
- Sinal: `Object.keys(obj).map(k => obj[k])` com erro de índice silenciado por cast. Correção: `Object.entries` com tipo explícito.
- Sinal: indexação `list[0].name` sem `noUncheckedIndexedAccess`. Correção: optional chaining ou guarda.

## 3. Performance e tipos
- Sinal: enum regular (`enum`) importado em chunk inicial só para uma constante. Impacto: pequeno; reporte só se o repo prefere union de literais.
- Sinal: `import type` ausente em import só de tipo em repo com `isolatedModules`/`importsNotUsedAsValues`. Impacto: import de runtime que impede tree shaking e puxa módulo pesado. Correção: `import type`.
- Sinal: `export *` em barrel de módulo grande. Impacto: tree shaking falha com `sideEffects` ausente; ciclos. Dono do desenho de barrels: review-modularidade; reporte aqui só o custo de bundle medido.

## 4. Extensões de protótipo globais
Repos podem instalar extensões (`String.prototype.toDate`, `Array.prototype.first`) no entrypoint. Chamada que usa a extensão instalada é legítima. Confirme no entrypoint antes de apontar "método inexistente".

## 5. Config
- `strict: true` desligado ou `skipLibCheck` mudado no diff: handoff para review-tipagem.
- `target` baixo (ES5) em app que serve só navegadores modernos aumenta bundle com helpers e transpila `async`. Reporte com o delta de KB quando medível.
