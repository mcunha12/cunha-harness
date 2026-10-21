# review-legibilidade — TypeScript e JavaScript

Tipagem em si (any, as, branded, generics) é de review-tipagem. Aqui entra a leitura do código.

## 1. Convenções de nome
- Variável e função: `camelCase`. Tipo, interface, classe, componente: `PascalCase`. Constante de módulo imutável: `UPPER_SNAKE_CASE` (`COMPLETION_THRESHOLD`). Enum: membro em `PascalCase` ou `UPPER_SNAKE` conforme o repo.
- Siga o padrão do repo para interface (`IUser` ou `User`) e para `type` vs `interface`. O repo vence.
- Booleano: `is/has/should/can/was`. Em props React, `isOpen`, `disabled` (atributo nativo) e `hasError` convivem.
- Handler interno `handleX`, prop de callback `onX`. Função assíncrona sem sufixo `Async`; o tipo `Promise` informa.
- Arquivo: nome do export principal (`CourseCard.tsx` exporta `CourseCard`). `index.ts` só reexporta.
- Parâmetro de tipo genérico: `T` para um só; nome descritivo (`TEntity`, `TResponse`) quando há 2+.
- Evite prefixo `get` em campo computado que não faz trabalho; `get` em função com IO engana. `fetch`/`load`/`find` dizem que há IO.

## 2. Idiomas que reduzem custo de leitura
```ts
// antes
const names = users.filter((u) => u.active).map((u) => u.name).filter((n) => n).map((n) => n.trim()).sort();
// depois: etapas nomeadas quando passam de 3
const activeUsers = users.filter((user) => user.active);
const trimmedNames = activeUsers.map((user) => user.name?.trim()).filter(Boolean);
const names = trimmedNames.sort();
```
- Optional chaining encadeado em 3+ níveis (`a?.b?.c?.d?.e`) revela modelo ruim ou falta de narrowing: função de acesso com nome.
- `??` e `||` com semântica diferente: `||` troca `0` e `''`. Reporte quando o valor pode ser `0` (nota 0, progresso 0). Esse bug é de legibilidade e correção; classifique MAJOR se o caller depende de `0`.
- Desestruturação com renome e default em parâmetro (`({ a: renamed = 5, ...rest })`) acima de 3 campos: parâmetro `props` e extrair no corpo.
- Parâmetro de objeto nomeado (`createCourse({ name, slug, isPublic })`) em função com 3+ parâmetros ou booleanos.
- `async` function que só repassa promise (`async () => await x`) pode devolver `x` direto. NIT.
- `.then` misturado com `await` na mesma função: escolha `await`.
- `for...of` sobre `Object.entries()` em vez de `Object.keys(...).forEach(k => obj[k])`.
- `switch` com `default` que lança erro e `never` é correto para exaustividade; custo de leitura baixo.
- Enum numérico com valor posicional (`status === 2`) exige constante nomeada; enum de string se lê melhor em log.

## 3. Sinais de code golf em TS/JS
- `!!x`, `+x`, `~~x`, `x | 0`: aceitos em código de biblioteca matemática. Em regra de negócio, `Boolean(x)`, `Number(x)`, `Math.trunc(x)`.
- `a && b || c` em lugar de ternário.
- Atribuição em condição (`if ((m = re.exec(s)))`) sem parênteses duplos e sem nome.
- Vírgula como operador, `void 0` em vez de `undefined`.
- Retorno de `arr.sort()` usado como se fosse cópia (`const sorted = list.sort()` muta `list`). Use `[...list].sort()` ou `toSorted()` (ES2023). Leitura enganosa e bug.
- Expressões com `reduce` que mutam o acumulador de modos diferentes por ramo.

## 4. Módulos
- `export default` anônimo (`export default () => ...`) perde nome em stack trace e em busca. Nomeie.
- Re-export e barrel com tema de review-modularidade. Reporte aqui só nome de arquivo enganoso.
- `import * as X` com 20 usos `X.foo` dispersos pode esconder as dependências reais. NIT.
- Extensões de protótipo globais do repo (`String.prototype.toDate`) são legítimas quando instaladas no entrypoint. Confirme antes de apontar.

## 5. Async e erros no ponto de leitura
- `try { ... } catch (e) { console.log(e) }` com 30 linhas no `try`: reduza ao trecho que falha.
- Função `async` sem `await` interno confunde: o leitor espera IO. Remover `async` quando só devolve valor.
- Promessa não aguardada (floating) é de review-resiliencia.
- Nome de erro: classe `EnrollmentNotFoundError` diz mais que `Error('not found')`.

## 6. Testes (nome apenas)
- Descrição de `it('...')` diz comportamento e condição ("retorna 409 quando a matrícula já existe"). `it('works')` e `it('test 1')` são MINOR. A estrutura do teste é de test-audit.
