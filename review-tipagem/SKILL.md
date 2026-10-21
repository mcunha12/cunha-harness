---
name: review-tipagem
description: Revisa o sistema de tipos num diff (TypeScript e Python) - afrouxamento de tsconfig, any explícito e implícito, `as` mentiroso, non-null assertion, @ts-ignore, modelagem de estados com unions discriminadas e exaustividade, branded types para IDs, tipos derivados em vez de redeclarados, generics ilegíveis, DTO class-validator divergente do tipo TS, e pyright/mypy strict em Python. Acionar com "revisa a tipagem desse PR", "tem any escondido?", `/review-tipagem`, ou via master-review. NAO cobre shape de dados entre serviços e validação de entrada em runtime (review-contratos), value object conceitual (review-clean), naming (review-legibilidade), nem erros de compilação que o tsc já reporta.
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-tipagem (prefixo TIP)

## Missão

Garantir que o sistema de tipos do diff diga a verdade sobre o runtime e torne estados inválidos impossíveis de construir. O agente acha os pontos onde o compilador foi silenciado (`any`, `as`, `!`, `@ts-ignore`), onde o tipo declarado diverge do dado real, onde a modelagem permite combinações ilegais e onde um tipo redeclarado vai envelhecer sozinho. Cada achado liga o furo ao bug que ele permite em produção.

## Escopo

Cada item segue o formato sinal no código, impacto, correção.

### 1. Configuração do compilador (TIP-CFG)

- `tsconfig` do diff com `strict: false`, `strictNullChecks: false`, `noImplicitAny: false`, `strictFunctionTypes: false`, `useUnknownInCatchVariables: false`. Impacto: classes inteiras de bug voltam a passar. Correção: reverter, ou isolar o trecho legado com `// @ts-expect-error` e prazo.
- Flags que o repo não liga e deveria: `noUncheckedIndexedAccess` (arr[i] e Record podem ser undefined), `exactOptionalPropertyTypes` (`?: T` difere de `T | undefined`), `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noImplicitReturns`, `noPropertyAccessFromIndexSignature`, `verbatimModuleSyntax` ou `isolatedModules`. Reporte a ausência como MINOR se o diff toca o `tsconfig` ou introduz código que a flag pegaria. Não exija ativação em massa num repo com milhares de erros: proponha ativação por diretório com `tsconfig` estendido.
- `skipLibCheck: true` é prática comum e não é achado. `include`/`exclude` que tira `src` do check é achado.
- `lib`/`target` incompatíveis com o runtime declarado em `.nvmrc`/`engines` (usar `Array.prototype.toSorted` com Node 18, `Object.groupBy` com Node 20).
- ESLint com `@typescript-eslint/no-explicit-any`, `no-non-null-assertion`, `ban-ts-comment`, `no-unsafe-*` desligados ou com `eslint-disable` novo no diff.
- Python: `pyright`/`mypy` com `strict` removido, `ignore_missing_imports = true` global, `# type: ignore` sem código.

### 2. Furos do sistema de tipos (TIP-HOL)

- `any` explícito: `: any`, `as any`, `<any>`, `Array<any>`, `Record<string, any>`, `Promise<any>`. Impacto: o `any` contamina cada valor que toca e desliga a checagem ao longo da cadeia. Correção: tipo real, `unknown` com narrowing, ou genérico.
- `any` implícito que passa pelo compilador: `JSON.parse()` (retorna `any`), `res.json()` (retorna `Promise<any>`), `axios.get(url)` sem genérico, `catch (e)` com `useUnknownInCatchVariables` desligado, `Object.entries` com valor `any`, `.filter(Boolean)` sem type guard, `fs.readFileSync(...).toString()` passado a `JSON.parse`, resposta de `fetch` em `.then(r => r.json())`, `event.target.value` em handlers com cast. Correção: `unknown` mais parse com schema (a validação é do review-contratos, o tipo é daqui).
- `as` mentiroso: `x as Foo` onde `x` não tem garantia de ser `Foo`. Sinais: `as unknown as Foo`, `as Foo` sobre `{}` vazio (`const r = {} as Foo`), `as` de supertipo para subtipo sem checagem, `as` em retorno de função para "fazer compilar". Impacto: o erro vira `TypeError` em runtime, longe do cast. Correção: `satisfies` quando a intenção é checar sem alargar, narrowing por type guard, ou construir o valor completo.
- `as const` é legítimo. `as const satisfies T` é a forma preferida para tabela de configuração.
- Non-null assertion `!`: `map.get(k)!`, `ref.current!`, `arr.find(...)!`, `process.env.X!`. Impacto: `undefined` em runtime com mensagem inútil. Correção: guard com erro explícito (`if (!v) throw new Error('...')`), ou função `invariant`. `process.env.X!` é tratado na validação de config no boot (review-resiliencia).
- `@ts-ignore`: troque por `@ts-expect-error` com motivo em uma linha (`// @ts-expect-error lib X tipa errado, issue #123`). `@ts-expect-error` avisa quando o erro desaparece, `@ts-ignore` fica para sempre. `@ts-nocheck` em arquivo novo é MAJOR.
- Type predicate sem checagem real: `function isFoo(x: unknown): x is Foo { return true }` ou checa só um campo de cinco. Impacto: o predicado é um cast disfarçado. Correção: checagem completa, ou schema (`Schema.safeParse(x).success`).
- Assertion function (`asserts x is Foo`) com corpo que não lança.
- Overload com implementação que aceita `any` e assinaturas públicas contraditórias.
- `Function`, `Object`, `{}` como tipo. `{}` aceita qualquer valor não nulo. Correção: `(...args: never[]) => unknown`, `object`, `Record<string, unknown>`.
- `unknown` convertido de volta com `as` no mesmo escopo. O `unknown` perde a função.
- Declaração `declare module 'x'` com `any` ou `declare global` alargando tipo de lib sem necessidade.

### 3. Modelagem (TIP-MOD)

- Estados ilegais representáveis: `{ loading: boolean; error?: Error; data?: Foo }` permite `loading: true` com `data`. Correção: union discriminada `{ status: 'idle' } | { status: 'loading' } | { status: 'error'; error: Error } | { status: 'success'; data: Foo }`.
- Vários booleanos que formam uma máquina de estados implícita (`isPaid`, `isCancelled`, `isRefunded`). Correção: um campo `status` com union de literais.
- Campos opcionais que só existem juntos (`startedAt?`, `endedAt?`). Correção: um objeto opcional `period?: { startedAt; endedAt }`, ou union por estado.
- Exaustividade: `switch` sobre union sem `default: assertNever(x)` quando o código precisa cobrir todos os casos. Impacto: valor novo na union é ignorado em silêncio. Correção: `function assertNever(x: never): never { throw new Error(...) }`. Para enum que vem da rede, o `default` degrada em vez de lançar (contrato é do review-contratos).
- `Record<Status, T>` como mapa exaustivo: valor novo em `Status` força o compilador a pedir a entrada. `Record<string, T>` não força.
- Branded types para IDs e unidades intercambiáveis: `type UserId = string & { readonly __brand: 'UserId' }`. Sinal: função com dois parâmetros `string` que representam entidades diferentes (`enroll(userId: string, courseId: string)`) e chamada com argumentos trocados. `TCourse` com `id` e `packId` ambos `string` é o exemplo clássico. Impacto: bug de ordem sem erro de compilação. Correção: brand mais construtor único que valida (`toCourseId(s)`). Reporte como MINOR, ou MAJOR quando já existe um bug comprovado de troca. Value object com regra de negócio (CPF, dinheiro) é do review-clean.
- `readonly` e `as const`: parâmetro de array ou objeto que a função não muta e aceita `T[]` mutável. `ReadonlyArray<T>`/`readonly T[]` em API exportada. Constante de configuração sem `as const`, perdendo os literais.
- Union de literais ou const object em vez de `enum`: `enum` numérico aceita qualquer número (antes do TS 5.0), gera código de runtime, e `const enum` quebra com `isolatedModules`. Correção: `const Status = { A: 'A', B: 'B' } as const; type Status = typeof Status[keyof typeof Status]`. Enum de string existente no repo segue o padrão local.
- Retorno explícito em função exportada de módulo público: a inferência vaza tipo interno e muda a API sem aviso quando o corpo muda. Em função local, a inferência basta.
- `Record<string, T>` indexado sem tratar `undefined` (sem `noUncheckedIndexedAccess`). Impacto: `map[key].campo` lança para chave ausente. Correção: `Map<string, T>` com `.get`, ou checagem.
- `Object.keys(obj)` devolve `string[]`, e o cast `as (keyof T)[]` esconde chaves extras em runtime. `Object.entries` perde o tipo da chave. Correção: helper tipado `typedKeys` com comentário, ou iterar sobre a tupla `as const` fonte.
- `new Map(Object.values(x as const).map(...))` herda chaves literais e `.get(string)` falha no tipo. Correção: `new Map<string, string>(...)` e nunca `as never`.
- `Partial<T>` onde o dado é "T completo ou nada". `Partial` deixa passar objeto vazio. Correção: `Required`, ou union.
- Optional chaining e `??` em valor que o tipo declara não nulo. O tipo ou o código mentem. Corrija o tipo, não o código, quando o runtime realmente pode ser nulo.
- Função que retorna `T | null | undefined` sem diferença semântica entre os dois. Escolha um.
- Arrays heterogêneos que deveriam ser tupla (`[number, string]` retornado como `(number | string)[]`).
- Parâmetros booleanos posicionais ou `options` com flags que combinam mal: modelar com union.
- Tipos de função `Promise<void>` passados onde o chamador espera `void` e ignora a promise (floating promise é do review-resiliencia).

### 4. Derivação em vez de redeclaração (TIP-DER)

- Interface que repete campos de outra (DTO, schema zod, tipo gerado, retorno de função, props de componente). Impacto: campo novo na origem não chega à cópia, sem erro. Correção: `Pick`, `Omit`, `Partial`, `Required`, `ReturnType<typeof fn>`, `Awaited<ReturnType<typeof fn>>`, `Parameters<typeof fn>`, `z.infer<typeof Schema>`, `typeof obj[number]`, `keyof typeof obj`, `React.ComponentProps<typeof X>`, tipo gerado do OpenAPI.
- Union de literais escrita à mão que duplica as chaves de um objeto ou o array fonte (`type Role = 'a' | 'b'` ao lado de `const ROLES = ['a','b']`). Correção: `const ROLES = [...] as const; type Role = typeof ROLES[number]`.
- Tipo declarado na camada de API e redeclarado no hook e no componente. Uma fonte, as outras importam.
- Regra de dono: tipo redeclarado é do review-tipagem. A regra de negócio duplicada em si é do review-dry.

### 5. Excesso de tipo (TIP-EXC)

- Tipos condicionais, `infer`, mapped types e template literal types aninhados em 3 níveis ou mais que o time não lê. Impacto: erro de compilador de 40 linhas e ninguém mantém. Correção: tipo concreto, overload, ou função com retorno explícito.
- Generic com parâmetro usado uma vez (`function f<T>(x: T): void`). O generic não relaciona nada. Correção: remova.
- Generic sem `extends` que depois recebe cast interno.
- Generic com default `any`.
- Tipo recursivo sem necessidade de profundidade arbitrária.
- Parâmetro de tipo nomeado `T`, `U`, `V` em tipo com quatro parâmetros. Nomes descritivos (`TItem`, `TKey`).
- Uso de `infer` para extrair o que `Awaited`, `ReturnType` ou `Parameters` já entregam.
- `satisfies` onde a anotação direta basta, e anotação direta onde `satisfies` preserva o literal que o código precisa.

### 6. NestJS e DTO (TIP-NST)

- DTO com `class-validator` divergente do tipo TS do mesmo campo: `foo?: string` sem `@IsOptional()`, `foo: string` com `@IsOptional()`, `@IsString()` em `number`, `@IsEnum` com enum TS diferente do tipo. Impacto: o tipo diz uma coisa e a validação aceita outra. O risco de contrato (payload aceito) é do review-contratos. O alinhamento tipo-decorator é daqui.
- `strictPropertyInitialization` desligado e DTO com `!:`. O padrão de DTO usa `!:` por convenção do Nest. Não é achado.
- `@Body() dto: CreateDto` onde `CreateDto` é `type`/`interface`. O decorator perde metadado. Correção: `class`.
- Provider injetado por token string sem tipo (`@Inject('X') private x: any`). Correção: `InjectionToken<T>` ou classe abstrata.
- `ConfigService.get('X')` sem genérico retorna `any`. Correção: `get<string>('X', { infer: true })` com `ConfigService<Env, true>` ou `ConfigType`.
- Repositório ou service que devolve `Promise<any>`.

### 7. React (TIP-RCT)

- Props sem tipo, `React.FC` com `children` implícito (React 18 removeu), `any` em handler (`onChange={(e: any) => ...}`). Correção: `React.ChangeEvent<HTMLInputElement>`.
- `useState<Foo>()` sem valor inicial: o tipo vira `Foo | undefined`. `useState<Foo>({} as Foo)` mente. Correção: `useState<Foo | null>(null)` com tratamento.
- `useRef<HTMLDivElement>(null)` versus `useRef<HTMLDivElement>()`: o primeiro é RefObject somente leitura.
- Context criado com `createContext<Ctx>({} as Ctx)`. Impacto: consumidor fora do provider recebe objeto vazio e quebra longe. Correção: `createContext<Ctx | null>(null)` e hook `useCtx` que lança.
- Props polimórficas e `as` prop com `any`. Correção: genérico com `ElementType`.
- `styled-components` com props sem tipo (`styled.div<{ $active: boolean }>`). Sem genérico, o acesso a `props.$active` vira `any` ou erro.
- Tipos de query do react-query v3: `useQuery<TData, TError>` com `TError` não informado vira `unknown`. `useQuery<Foo>(...)` com resposta `any` no `queryFn` anula o genérico.
- Discriminated union em props para variantes mutuamente exclusivas, em vez de três props opcionais.

### 8. Prisma e SQL tipado (TIP-ORM)

- Resultado de `$queryRaw` tipado por genérico (`$queryRaw<Foo[]>`) sem garantia. Impacto: o genérico é cast. Colunas `bigint`, `numeric` e `timestamp` chegam como `bigint`, `Decimal` e `Date`. Correção: schema de parse na saída, ou `Prisma.sql` com `select` tipado.
- `Prisma.<Model>GetPayload` e `Prisma.validator` em vez de interface manual para retorno de `include`/`select`.
- `Prisma.JsonValue` usado com cast para tipo de domínio. Impacto: JSON do banco não tem garantia. Correção: parse com schema.
- `as unknown as` sobre resultado de ORM.

### 9. Python (TIP-PY)

- `Any` explícito ou implícito (parâmetro sem anotação, retorno sem anotação em função pública), `cast(...)` sem checagem, `# type: ignore` sem código de erro (`# type: ignore[arg-type]`) e sem motivo.
- `Optional[X]` usado sem narrowing (`x.attr` onde `x` pode ser `None`).
- `dict` cru onde há forma conhecida: `TypedDict` (só checagem estática), `dataclass` (sem validação), `Pydantic` (validação em runtime na borda). Escolha pela origem do dado: borda externa usa Pydantic, estrutura interna usa dataclass ou TypedDict.
- `Protocol` para contrato estrutural em vez de herança só para tipar. `Literal` e `Enum` para valores fechados, `NewType` para IDs intercambiáveis, `assert_never` para exaustividade em `match`, `TypeVar` com `bound=`, `Self`, `ParamSpec` em decorators (decorator que apaga a assinatura com `Callable[..., Any]`).
- `list` e `dict` mutáveis como default de parâmetro (bug, e o tipo não avisa). `Sequence`/`Mapping` em parâmetros de leitura.

## Fora de escopo e dono

| Tema | Dono |
|---|---|
| Shape entre serviços, breaking change, validação de entrada em runtime | review-contratos |
| Value object conceitual, primitive obsession de regra de negócio | review-clean |
| Regra de negócio duplicada | review-dry |
| Naming, complexidade cognitiva | review-legibilidade |
| Fronteira entre módulos e camadas | review-modularidade |
| Config validada no boot, floating promise, erro engolido | review-resiliencia |
| Segurança de `eval`, `dangerouslySetInnerHTML` | review-seguranca |
| Erro de compilação que o `tsc` já emite | não reportar |

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack conforme `review-rules.md`. Leia `references/generic.md` sempre. Leia o reference da tecnologia que existir neste diretório e bater com a stack: `typescript.md`, `react.md`, `nestjs.md`, `prisma-postgres.md`, `python.md`. Registre os lidos em `stack_references_loaded`.
3. Obtenha o diff. Se o orquestrador enviou um context packet, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`). `--path` restringe os arquivos.
4. Leia o `tsconfig` efetivo (com `extends`) e a config de lint. Registre as flags ligadas. A severidade de cada furo depende delas: `!` com `noUncheckedIndexedAccess` ligado e `arr[0]!` tem justificativa diferente de `map.get(k)!`.
5. Rode as ferramentas determinísticas disponíveis (seção própria). Use o resultado como insumo.
6. Procure no diff, por padrão: `any`, ` as `, `!.`, `!)`, `!;`, `@ts-`, `eslint-disable`, `JSON.parse`, `.json()`, `catch (`, `Record<string`, `Object.keys`, `enum `, `: Function`, `{} as`, `<any>`. Todo hit tem de ser aberto no contexto antes de virar achado.
7. Para cada candidato, leia o caller e o callee. Verifique se o valor tem garantia por outro lado (guard anterior, schema a montante, tipo estreitado pelo compilador).
8. Classifique pela rubrica abaixo e pela global. BLOCKER com confiança baixa vira MAJOR.
9. Emita no formato de `output-contract.md`: bloco JSON primeiro, markdown depois. `agent` vale `review-tipagem`, ids `TIP-001` em diante, no máximo ~15 achados. Agrupe ocorrências repetidas do mesmo padrão num achado só, com a lista de locais em `problem`.

Standalone: ao final, mostre o markdown. Não altere código.

## Rubrica de severidade do tema

**BLOCKER**
- Cast ou `any` que esconde divergência já comprovada com o runtime, e o dado errado causa perda de dado ou resposta incorreta a usuário (por exemplo `as Foo` sobre resposta de API cujo campo mudou no mesmo diff).
- `strict` desligado no `tsconfig` de pacote publicado ou de app inteira, sem plano.

**MAJOR**
- `any` ou `as` na fronteira de I/O (`res.json() as T`, `JSON.parse() as T`, `catch (e: any)` acessando `e.response.data`).
- `@ts-nocheck` ou `@ts-ignore` sem motivo em código de regra de negócio.
- Modelo de estado com booleanos que permite combinação ilegal, usado em fluxo de pagamento, matrícula, nota ou progresso.
- Type predicate que retorna `true` sem checagem.
- `createContext({} as Ctx)` em provider usado por muitas telas.

**MINOR**
- `!` em valor que o código acabou de checar em outra linha, mas o compilador não rastreia.
- Interface redeclarada que espelha um DTO ou tipo gerado.
- ID `string` intercambiável em função com dois IDs de entidades diferentes, sem bug comprovado.
- Retorno implícito em função exportada de módulo público.
- `Partial<T>` onde `T` completo é o contrato.

**NIT**
- `type` versus `interface` onde o repo não padroniza.
- `Array<T>` versus `T[]`.
- Nome de parâmetro de tipo `T`.

## Heurísticas anti-falso-positivo

- Arquivo de teste, mock, fixture, story e script: `any` e `as` são aceitos. Reporte só se vazar para código de produção.
- `as const`, `as const satisfies`, e `as unknown as X` em teste de tipo (`expectTypeOf`, `tsd`) são legítimos.
- `!` depois de guard no mesmo escopo que o compilador não estreita (callback, closure, `Array.prototype.find` seguido de `if`) é MINOR no máximo. Se o valor foi checado três linhas acima, sugira atribuir à `const` local e deixar o narrowing agir, sem escalar.
- DTO de Nest com `prop!: string` é a convenção do framework.
- `any` em assinatura de callback genérica de lib (`(...args: any[]) => any` em `Function` wrappers e utility types) é aceito: `never[]` e `unknown` quebram a variância.
- `@ts-expect-error` com motivo e link está correto.
- Cast de `Object.keys` com `typedKeys` encapsulado e comentado é correto.
- Tipo gerado (`*.generated.ts`, `openapi.d.ts`, `prisma/client`) não é revisado. O achado vai para a fonte.
- Padrão local vence: se o repo usa `enum` em 200 lugares, enum novo segue o padrão.
- Legado: reporte só o que o diff introduziu ou tocou. O restante vai para `preexisting_debt`.
- Não reporte o que `tsc` ou ESLint do repo já bloqueia no CI.
- `unknown` + narrowing com `typeof`/`in`/`instanceof` é o padrão desejado.
- `Record<string, unknown>` em borda que ainda não parseou é correto.

## Ferramentas determinísticas opcionais

Rode só se instaladas. Nunca instale. A saída é insumo.

- `tsc`: checagem `ls node_modules/.bin/tsc`. Execução `npx --no-install tsc --noEmit -p tsconfig.json`. Para checar uma flag nova sem alterar o repo: `npx --no-install tsc --noEmit -p tsconfig.json --noUncheckedIndexedAccess` e conte erros só nos arquivos do diff.
- ESLint com regras de tipo: checagem `ls node_modules/.bin/eslint`. Execução `npx --no-install eslint <arquivos do diff>` com a config do repo. Regras relevantes: `@typescript-eslint/no-explicit-any`, `no-unsafe-assignment`, `no-unsafe-member-access`, `no-unsafe-return`, `no-non-null-assertion`, `ban-ts-comment`, `switch-exhaustiveness-check`.
- `type-coverage`: checagem `ls node_modules/.bin/type-coverage`. Execução `npx --no-install type-coverage --detail --strict`.
- Python: `pyright` (`command -v pyright`; `pyright --outputjson <arquivos>`), `mypy` (`command -v mypy`; `mypy --strict <arquivos>`).

## Exemplos

### Achado 1

```json
{
  "id": "TIP-001",
  "agent": "review-tipagem",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "TIP-HOL",
  "location": { "repo": "web-aluno", "file": "src/api/use-get-enrollments.ts", "lines": "18-24" },
  "evidence": "const { data } = await api.get('/enrollments');\nreturn data.items as Enrollment[];",
  "problem": "axios.get sem genérico devolve data: any, e o cast `as Enrollment[]` afirma o shape sem verificar. Se o BFF devolver items: null (ocorre para aluno sem matrícula ativa, ver testes do BFF), o código quebra em `.map` na tela, longe do cast. O compilador não avisa.",
  "fix": "const EnrollmentsSchema = z.object({ items: z.array(EnrollmentSchema) });\nconst { data } = await api.get<unknown>('/enrollments');\nreturn EnrollmentsSchema.parse(data).items;\n// e exporte `type Enrollment = z.infer<typeof EnrollmentSchema>` no lugar da interface manual",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["typescript-eslint no-unsafe-return"],
  "introduced_by_diff": true
}
```

### Achado 2

```json
{
  "id": "TIP-002",
  "agent": "review-tipagem",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "TIP-MOD",
  "location": { "repo": "web-aluno", "file": "src/pages/Certificate/useCertificate.ts", "lines": "9-14" },
  "evidence": "type State = { isLoading: boolean; isError: boolean; pdfUrl?: string };",
  "problem": "O tipo permite isLoading true com isError true e pdfUrl preenchido. O componente testa `isError` antes de `pdfUrl`, então um estado inconsistente mostra o erro com o PDF carregado. Três campos geram 8 combinações para 4 estados reais.",
  "fix": "type State =\n  | { status: 'loading' }\n  | { status: 'error' }\n  | { status: 'ready'; pdfUrl: string };\n// no componente, `switch (state.status)` com `default: assertNever(state)`",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["make illegal states unrepresentable"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

O diff adiciona em `CreateEnrollmentDto` a linha `courseId!: string;` com `@IsUUID()`. Parece non-null assertion perigosa. Não se reporta: o Nest instancia o DTO por reflexão (`class-transformer`), o `!:` é a convenção do framework com `strictPropertyInitialization` ligado, e o `@IsUUID()` valida o valor em runtime antes do handler. O tipo e o decorator estão alinhados.
