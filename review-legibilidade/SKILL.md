---
name: review-legibilidade
description: "Revisa legibilidade e manutenção humana de um diff: naming (nome que mente, linguagem ubíqua, booleanos, verbos), complexidade cognitiva, aninhamento, ternários aninhados, booleanos complexos, ordem de leitura (step-down), magic numbers, code golf, regex sem nome e consistência com o estilo local. Acione em 'revisa a legibilidade desse PR', 'esse código está fácil de ler?', '/review-legibilidade' ou via master-review. Prefixo LEG. NÃO cobre SRP e smells de função (review-clean), duplicação (review-dry), fronteiras de módulo (review-modularidade), tipos (review-tipagem), comentários (review-comentarios) nem o que o formatter resolve."
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-legibilidade

## Missão

Medir quanto custa para um dev novo entender o diff. O teste final: alguém sem contexto do ticket lê a mudança e explica o que ela faz e por quê em 5 minutos. Cada achado cita o trecho, o custo de leitura (nome que engana, caminho de execução que exige guardar 4 condições na cabeça, ordem que obriga a ler de baixo para cima) e a reescrita concreta. O agente reporta só o que o diff introduziu ou tocou, e nunca o que o formatter resolve.

## Escopo

Cada item segue o formato sinal, impacto, correção. O detalhe por tecnologia fica em `references/`.

### 1. Naming
- Sinal: nome que descreve uma coisa e o código faz outra (`getUser` que cria o usuário quando não existe, `isValid` que também persiste, `list` que devolve um Map, `enrollment` que guarda uma turma). Impacto: o leitor confia no nome e escreve código errado em cima. Severidade MAJOR. Correção: renomear para o que o código faz, ou separar a função.
- Sinal: nome genérico (`data`, `info`, `item`, `obj`, `temp`, `result`, `res`, `val`, `manager`, `handler`, `helper`, `util`, `process`, `handle`, `doStuff`) quando há nome melhor no domínio. Correção: nome do conceito (`enrollmentsByCourse`, `expiredCertificates`, `applyEarlyBirdDiscount`). `data` em fronteira de resposta HTTP (`response.data`) e `handle` em convenção do framework (`handleSubmit` de RHF) ficam aceitos.
- Sinal: booleano sem prefixo de predicado (`active`, `loading`, `permission`, `flag`, `status` com true/false). Correção: `isActive`, `isLoading`, `hasPermission`, `canEdit`, `shouldRetry`. Booleano negado no nome (`isNotEnabled`, `disableX`) induz dupla negação. Correção: nome positivo.
- Sinal: função sem verbo (`user()`, `enrollment()`), ou verbo que não diz o efeito (`handleData`, `doProcess`, `manage`). Correção: `fetchUser`, `buildEnrollment`, `cancelEnrollment`. Getter puro usa substantivo ou `get`; função com efeito usa verbo de ação.
- Sinal: abreviação obscura (`enr`, `crs`, `usr`, `cfg`, `mgr`, `tmp`, `idx`, `n`, `cb`). Aceitas as convencionais do ecossistema (`i`, `id`, `url`, `req`, `res`, `err`, `ctx`, `props`, `ref`, `e` em handler curto). Correção: palavra inteira.
- Sinal: vocabulário do domínio inconsistente no mesmo diff ou entre diff e repo (`student`/`aluno`/`user` para a mesma entidade, `class`/`turma`/`group`, `subscription`/`matrícula`/`enrollment`, `schedule`/`cronograma`/`timeline`). Impacto: o leitor suspeita de dois conceitos onde há um. Correção: usar o termo que o repo já usa (grep dos nomes existentes), um termo por conceito.
- Sinal: nome de tipo/interface/arquivo diferente do conteúdo (arquivo `utils.ts` com regra de negócio, `types.ts` com constante, `index.tsx` com 4 componentes). Correção: nome do conteúdo.
- Sinal: nome com tipo embutido sem necessidade (`userArray`, `nameString`, `IUser` em repo que não usa prefixo `I`). Correção: seguir o padrão do repo.
- Sinal: nome longo demais que repete o contexto (`course.courseName`, `user.userEmail`). Correção: `course.name`.
- Sinal: unidade ausente em número (`timeout = 30`, `duration`, `price`, `size`). Correção: `timeoutMs`, `durationSeconds`, `priceInCents`, `sizeBytes`, ou tipo com unidade.
- Sinal: nome de callback/evento inconsistente (`onClick` prop passada como `handleClick`, `onX` em handler interno). Convenção React: prop `onX`, handler interno `handleX`.

### 2. Complexidade
- Complexidade cognitiva (SonarSource) acima de ~15 por função: cada `if`, `else if`, `else`, `switch`, `for`, `while`, `catch`, operador ternário, sequência de `&&`/`||` de tipo diferente soma 1, e soma a mais o nível de aninhamento. Impacto: cada ponto de decisão cresce o número de caminhos a lembrar. Correção: guard clauses, extrair função com nome, tabela de lookup.
- Sinal: aninhamento acima de 3 níveis.
```ts
// antes
if (user) { if (user.enrollment) { if (user.enrollment.active) { return grant(); } } }
// depois
if (!user?.enrollment?.active) return deny();
return grant();
```
- Sinal: ternário aninhado.
```ts
// antes
const label = a ? 'x' : b ? 'y' : c ? 'z' : 'w';
// depois
function resolveLabel(): string {
  if (a) return 'x';
  if (b) return 'y';
  if (c) return 'z';
  return 'w';
}
```
Um ternário simples fica. JSX com ternário aninhado vira variável ou componente.
- Sinal: expressão booleana com 3 ou mais operandos misturados (`a && !b || c && d`). Correção: variáveis explicativas.
```ts
const isEligible = enrollment.active && !enrollment.suspended;
const hasOverride = user.isAdmin || user.hasWaiver;
if (isEligible || hasOverride) { ... }
```
- Sinal: dupla negação ou negação em condição (`if (!isNotReady)`, `!!x === false`, `if (!list.length === 0)`). Correção: condição afirmativa, ou inverter o `if`/`else`.
- Sinal: `else` depois de `return`/`throw`. Correção: remover o `else`.
- Sinal: `switch` com fall-through implícito, ou `switch(true)` com condições longas. Correção: `if` em cadeia ou mapa de estratégias.
- Sinal: loop com `break`/`continue` em 3+ pontos. Correção: extrair predicado ou usar `find`/`some`/`every`.
- Sinal: cadeia de `.map().filter().reduce()` de 4 ou mais passos, com callbacks de várias linhas. Impacto: o leitor tem de simular o dado em cada passo. Correção: variáveis intermediárias com nome, ou um `for...of` de 6 linhas. `reduce` que monta objeto de lookup com lógica condicional vira loop.
- Sinal: função com mais de ~40 linhas e mais de um nível de abstração. O tamanho funciona como sinal. O dono de SRP é review-clean; aqui reporte só o custo de leitura.
- Sinal: lista de parâmetros posicionais com booleanos (`render(true, false, true)`). Custo de leitura no ponto de chamada. Correção: objeto nomeado. O dono do smell "flag argument" é review-clean; reporte aqui só a ilegibilidade do call site.

### 3. Fluxo de leitura
- Step-down rule: a função de alto nível vem primeiro e as de detalhe abaixo, na ordem em que são chamadas. Sinal: helper de detalhe no topo e a função principal escondida no fim. Correção: reordenar.
- Colocalização: constante, tipo e helper usados por um único consumidor ficam no arquivo dele, perto do uso. Sinal: `constants.ts` com 40 valores usados em lugares distintos. Correção: mover para o consumidor.
- Sinal: variável declarada longe do primeiro uso (30 linhas acima). Correção: declarar perto do uso.
- Sinal: efeito colateral escondido no meio de uma sequência de cálculo. Correção: mover para o início ou fim e nomear. O dono do side effect em função com cara de pura é review-clean.
- Sinal: arquivo de 400+ linhas novo, ou com 6+ responsabilidades por seção. Tamanho é sinal de legibilidade: o leitor perde o mapa. Correção: separar por conceito. Uma função/componente por arquivo, quando o repo adota. Dono da fronteira de módulo: review-modularidade.
- Sinal: early return ausente em função com pré-condições, empilhando condições no fim. Correção: guard clauses no topo, caminho feliz sem indentação.
- Sinal: caminho feliz e de erro intercalados em blocos de `try` enormes. Correção: `try` envolvendo só a chamada que pode falhar.
- Sinal: estado temporário mutado por 10+ linhas (`let result = ...; result = ...; result = ...`). Correção: pipeline de `const` nomeados.
- Sinal: ordem de campos e métodos aleatória na classe. Ordem local do repo manda; sem padrão, públicos antes de privados, construtor antes de métodos.
- Ordem no corpo de componente React, quando o repo adota: bloco de hooks (`useState`, `useMemo`, `useRef`, `useCallback`) primeiro, consts derivadas depois. Exceção: const lida por um hook anterior vem antes do hook, senão dá erro de TDZ. Confira a dependência antes de pedir reordenação.

### 4. Clareza
- Sinal: magic number ou string no meio da lógica (`if (progress >= 0.85)`, `setTimeout(fn, 86400000)`, `status === 3`). Correção: constante nomeada com unidade (`COMPLETION_THRESHOLD = 0.85`, `ONE_DAY_MS`). Se a mesma constante aparece em 2+ lugares, o dono é review-dry; aqui reporte uma ocorrência isolada.
- Sinal: code golf (`+!!x`, `~~n`, `x && y || z`, `a ? true : false`, `!!(a && b)` sem necessidade, `arr.length && ...`, bit tricks sem comentário, encadeamento de `?.` e `??` de 4 níveis). Correção: forma direta (`Boolean(x)`, `Math.trunc(n)`, `x ? y : z`, `a`).
- Sinal: regex longa sem nome e sem explicação. Correção: constante com nome (`const BRAZILIAN_CPF_PATTERN = /.../`), partes compostas, ou função `isValidCpf`. Um one-liner de comentário sobre a intenção fica.
- Sinal: callback aninhado em callback, `.then().then().then()` com lógica, promise misturada com `await` no mesmo bloco. Correção: `async/await` linear.
- Sinal: desestruturação profunda em parâmetro (`({ a: { b: { c } } }) =>`) ou com default complexo. Correção: parâmetro simples e extrair no corpo.
- Sinal: lógica espalhada em template literal ou JSX com `&&` encadeado, `map` com `if` dentro e `switch` inline. Correção: variável ou componente nomeado antes do `return`.
- Sinal: comentário que explica o que o código faz por falta de nome (`// loop pelos alunos ativos`). Correção: renomear e extrair; handoff para review-comentarios para remover.
- Sinal: código morto, bloco comentado, flag permanentemente `false`, parâmetro nunca lido. Impacto: o leitor gasta tempo para descobrir que não roda. Correção: remover. Variável não usada em TS é regra de lint do repo; reporte só com regra desligada.
- Sinal: `any`-like `data: Record<string, unknown>` repassado por 4 funções, sem nome do domínio. Correção: tipo nomeado. Dono do tipo: review-tipagem; aqui só a perda de significado.
- Sinal: string de domínio em PT-BR e inglês misturados no mesmo identificador (`getTurmaById`, `matriculaStatus`). Correção: seguir a língua do repo. Termos do domínio já fixados no repo (turma, matrícula, cronograma) permanecem no idioma do repo.
- Sinal: negação em nome de função de predicado (`isNotExpired`). Correção: `isExpired` e inverter no uso.

### 5. Consistência com o estilo local
- Sinal: arquivo novo que usa padrão diferente do vizinho sem motivo (classe vs função, `async/await` vs `.then`, `interface` vs `type`, nomes camelCase vs snake_case, `default export` vs nomeado). Impacto: o leitor reaprende a convenção em cada arquivo. Correção: seguir o padrão local. Respeite `CLAUDE.md`, ESLint e o estilo dominante do diretório, mesmo discordando.
- Sinal: um conceito com duas formas de escrever no mesmo diff (`fetchX` e `getX` para o mesmo tipo de operação). Correção: uma.
- Sinal: i18n do repo (`dictionary.json`) ignorado com string solta na UI. Dono do critério: convenção do repo; reporte como MINOR.
- Sinal: formatação que o Prettier/ESLint resolve (aspas, vírgula, indentação, ordem de imports com plugin). Não reporte.

### 6. Teste final dos 5 minutos
Para cada arquivo novo ou reescrito, responda em silêncio: o que faz, por que existe, o que muda se eu mudar X? Se a resposta exige abrir 3 arquivos para entender um nome, o nome é o achado. Se exige simular mais de 4 condições, a condição é o achado.

## Fora de escopo

| Tema | Dono |
|---|---|
| SRP, long method por responsabilidade, feature envy, flag argument como smell | review-clean |
| Magic value repetido em 2+ lugares, copy-paste | review-dry |
| Fronteiras entre módulos, camadas, ciclos, barrels | review-modularidade |
| Tipos, `any`, `as`, tipo redeclarado | review-tipagem |
| Comentários (remover, condensar, adicionar) | review-comentarios |
| Re-render, effects, bundle | review-front |
| Formatação resolvida por Prettier/ESLint | ninguém (ferramenta) |
| Testes (nomes de teste e estrutura) | test-audit |

Registre em `handoffs` com uma linha. Não desenvolva.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia `typescript.md` (TypeScript), `react.md` (React/Next), `nestjs.md` (NestJS), `python.md` (Python) quando a stack bater.
3. Obtenha o diff. Com context packet do orquestrador, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`). Respeite `--path`.
4. Leia o estilo local. Abra 2 arquivos vizinhos, o `CLAUDE.md`, `.eslintrc*`/`eslint.config.*`, `.prettierrc*`, `tsconfig`. Anote vocabulário do domínio (nomes de entidades) e convenções (idioma dos identificadores, `I` em interfaces, exports).
5. Analise o diff por função e por componente. Calcule a complexidade cognitiva de cada função grande do diff e conte aninhamento.
6. Verifique o contexto. Abra o caller para ver como o nome é usado, e a definição para ver o que o nome promete. Nome que mente só se confirma lendo o corpo e os usos. Procure o termo do domínio com `grep -rn` nos arquivos existentes antes de propor um renome.
7. Classifique com a rubrica abaixo. Em renomes, proponha o nome concreto e liste os usos afetados no `fix`.
8. Emita no formato de `output-contract.md`. Prefixo `LEG`, `agent: "review-legibilidade"`. Máximo de ~15 achados, agrupe nomes ruins do mesmo tipo num achado só, com a lista das ocorrências no `problem`.

Standalone: mostre o markdown ao final. Não altere código.

## Rubrica de severidade

**BLOCKER**
- Reservado. Legibilidade sozinha não bloqueia merge. Use só quando o nome que mente inverte o comportamento esperado em fluxo de dinheiro, permissão ou dado de aluno (por exemplo `canAccess` que devolve `true` quando o acesso é negado) e o caller depende do nome. Sem essa condição, no máximo MAJOR.

**MAJOR**
- Nome que mente: `getX` com efeito colateral, `isX` que persiste, variável com unidade errada (`delayMs` em segundos).
- Complexidade cognitiva acima de 25 numa função nova, ou aninhamento acima de 4.
- Ternário aninhado em lógica de regra de negócio, ou condição booleana de 5+ operandos sem nome.
- Dois termos para o mesmo conceito de domínio no mesmo módulo (`student` e `aluno` na mesma função).

**MINOR**
- Complexidade cognitiva de 16 a 25.
- Magic number isolado numa regra de negócio.
- Booleano sem prefixo, abreviação obscura, `else` depois de `return`.
- Cadeia de `map/filter/reduce` de 4 passos sem nomes.
- Arquivo novo que diverge do padrão do vizinho.

**NIT**
- Nome levemente melhorável, ordem de declaração, `data` em fronteira de resposta.

## Heurísticas anti-falso-positivo

- O formatter e o linter já pegam formatação. Não reporte.
- Convenção do ecossistema ganha do gosto: `i`/`j` em loop curto, `e` em handler de 3 linhas, `req`/`res`/`ctx`, `props`, `ref`, `cb` em assinatura de biblioteca.
- Termos do domínio fixados no repo ficam como estão, mesmo em PT-BR dentro de código em inglês (`turma`, `matrícula`, `cronograma`). Consistência com o repo vence regra pessoal de idioma.
- Complexidade que vem de uma regra inerentemente complexa, já extraída e nomeada, não é achado. Se o `switch` tem 12 casos de um enum e cada um tem uma linha, a complexidade cognitiva soma 1 por switch, independente dos 12 casos.
- Função longa e linear (sequência de passos sem ramificação) pesa menos que função curta e muito ramificada. Meça ramificação.
- Ternário simples de um nível e `?.`/`??` simples são idiomáticos.
- Código gerado (client OpenAPI, `*.generated.ts`, migrations geradas, `schema.d.ts`) está fora de escopo.
- Teste: nomes longos em `it('...')` descrevem comportamento. Não reporte comprimento.
- Nome curto em escopo de 3 linhas (`const u = users[0]`) é aceitável, a distância entre declaração e uso é o critério.
- Magic number auto-explicativo no contexto imediato (`Math.round(x * 100) / 100`, `% 2`, `* 1000` para ms em linha com `Ms` no nome, `404` em `status === 404` em ponto de uso HTTP) não precisa de constante.
- Não proponha renome que colide com nome existente no módulo. Confira o escopo.
- Não reporte dívida anterior. Linhas intocadas vão para `preexisting_debt` no máximo 3.
- Padrão do repo que o time escolheu, como `React.FC` ou prefixo `I`, não se reporta, mesmo com guia de estilo diferente.

## Ferramentas determinísticas opcionais

Rode só se instaladas no repo. A saída é insumo.

- ESLint com regras de complexidade: verifique `.eslintrc*`/`eslint.config.*`. Rode `npx eslint --no-eslintrc --parser @typescript-eslint/parser --rule 'complexity: [warn, 10]' --rule 'max-depth: [warn, 3]' --rule 'max-lines-per-function: [warn, 60]' --rule 'no-nested-ternary: warn' --rule 'no-magic-numbers: [warn, {ignore:[0,1,-1,2,100,1000]}]' <arquivos do diff>` apenas se `eslint` e `@typescript-eslint/parser` existirem em `node_modules/.bin`.
- `eslint-plugin-sonarjs` (`cognitive-complexity`): verifique `ls node_modules/eslint-plugin-sonarjs`. Rode `npx eslint --no-eslintrc --parser @typescript-eslint/parser --plugin sonarjs --rule 'sonarjs/cognitive-complexity: [warn, 15]' <arquivos>`.
- `radon cc -s -n C <arquivos.py>` (Python), se `radon` estiver no PATH ou venv. `ruff check --select C901,PLR0912,PLR0915 <arquivos.py>` se `ruff` estiver instalado.
- `eslint-plugin-unicorn` (`prefer-ternary`, `no-nested-ternary`, `no-negated-condition`), se já configurado.
- Verifique a presença com `ls node_modules/.bin | grep -E 'eslint|radon|ruff'` antes de rodar. Nunca instale.

## Exemplos

### Achado 1

```json
{
  "id": "LEG-001",
  "agent": "review-legibilidade",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "Nome que mente",
  "location": { "repo": "web-app", "file": "src/hooks/useCertificate.ts", "lines": "18-34" },
  "evidence": "export function getCertificate(enrollmentId: string) {\n  const cert = certificates.find((c) => c.enrollmentId === enrollmentId);\n  if (!cert) {\n    return issueCertificate(enrollmentId);\n  }\n  return cert;\n}",
  "problem": "getCertificate emite um certificado novo quando não encontra. Os 4 callers (CertificateTab, DownloadButton, ShareModal, useCertificateStatus) chamam o nome como consulta, inclusive em render. Um render de DownloadButton emite certificado de aluno que ainda não concluiu o curso.",
  "fix": "export function findCertificate(enrollmentId: string) {\n  return certificates.find((c) => c.enrollmentId === enrollmentId);\n}\n\nexport function issueCertificateIfMissing(enrollmentId: string) {\n  return findCertificate(enrollmentId) ?? issueCertificate(enrollmentId);\n}\n// callers de consulta passam a usar findCertificate",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["Clean Code cap. 2: nomes que não enganam"],
  "introduced_by_diff": true
}
```

```
### [MAJOR] LEG-001 — getCertificate emite certificado
**Onde:** web-app/src/hooks/useCertificate.ts:18-34 · **Confiança:** alta · **Esforço:** S
**Problema:** o nome promete consulta e o código emite. 4 callers usam como consulta.
**Correção:** separar em `findCertificate` e `issueCertificateIfMissing`.
```

### Achado 2

```json
{
  "id": "LEG-002",
  "agent": "review-legibilidade",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "Complexidade: ternário aninhado e booleano composto",
  "location": { "repo": "web-app", "file": "src/pages/main/Courses/helpers.ts", "lines": "52-60" },
  "evidence": "const status = e.active && !e.suspended && (e.expiresAt ? e.expiresAt > now : true) ? (e.progress >= 0.85 ? 'completed' : e.progress > 0 ? 'in_progress' : 'not_started') : 'blocked';",
  "problem": "A linha mistura elegibilidade (4 condições) e progresso (3 faixas) em 2 ternários aninhados. Complexidade cognitiva estimada: 12 em uma expressão. O limiar 0.85 aparece sem nome. Quem altera a regra de elegibilidade precisa decifrar a regra de progresso junto.",
  "fix": "const COMPLETION_THRESHOLD = 0.85;\n\nfunction resolveProgressStatus(progress: number) {\n  if (progress >= COMPLETION_THRESHOLD) return 'completed';\n  if (progress > 0) return 'in_progress';\n  return 'not_started';\n}\n\nconst isNotExpired = !e.expiresAt || e.expiresAt > now;\nconst isAccessible = e.active && !e.suspended && isNotExpired;\nconst status = isAccessible ? resolveProgressStatus(e.progress) : 'blocked';",
  "auto_fixable": true,
  "effort": "S",
  "refs": ["SonarSource Cognitive Complexity"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

```ts
const ms = Math.round(seconds * 1000);
for (let i = 0, n = items.length; i < n; i++) { total += items[i].price; }
```

Sinal aparente: `1000` sem constante, `i` e `n` curtos. `* 1000` converte segundos em milissegundos na mesma linha, com `ms` no nome da variável. `i`/`n` em loop de 1 linha são convenção do ecossistema. A constante nomeada acrescenta indireção sem ganho. Não reportar.
