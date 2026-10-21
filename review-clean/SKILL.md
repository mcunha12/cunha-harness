---
name: review-clean
description: Revisa design de função e classe (SOLID pragmático, smells de Fowler, efeitos colaterais, fluxo de controle, functional core, value objects) em diff ou PR. Acione em "revisa o design desse código", "esse service está com responsabilidade demais?", /review-clean, ou via master-review. Cobre SRP, OCP, LSP, ISP, DIP em nível de classe, long method, parameter list, flag arguments, feature envy, data clumps, message chains, side effect oculto, violação de CQS, mutação de parâmetro, aninhamento, null ambíguo, primitive obsession conceitual. Não cobre naming e complexidade cognitiva (review-legibilidade), fronteiras entre módulos e camadas (review-modularidade), duplicação (review-dry), tipos (review-tipagem).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-clean

## Missão

Avaliar o design de funções, classes e componentes que o diff cria ou altera. O critério é custo de mudança: uma unidade bem desenhada muda por um motivo, expõe o que faz sem efeito escondido e recebe suas dependências. A skill aplica SOLID de forma pragmática. Princípio sem dor concreta no código (acoplamento que quebrou teste, mudança que tocou 5 métodos) não gera achado. Cada achado nomeia o motivo de mudança que está misturado, o efeito oculto ou a dependência presa, e mostra a refatoração em código.

## Escopo

Cada item segue: sinal no código, impacto, correção típica.

### 1. SRP: mais de um motivo de mudança

- Sinal: classe ou função cujo corpo mistura IO (HTTP, banco, fila), regra de negócio e formatação. Service com métodos que não compartilham campos de estado. Nome terminado em `Manager`/`Handler`/`Helper`/`Processor` com 6+ responsabilidades. Imports de 4+ domínios distintos.
- Impacto: toda mudança de regra reabre código de infra. Testes exigem 5 mocks.
- Correção: separar por motivo de mudança. Regra em função pura ou classe de domínio, IO em adapter, formatação em apresentador. Separação sem ganho de teste ou de mudança fica como está.

### 2. OCP: switch/if por tipo repetido

- Sinal: o mesmo `switch (type)` ou cadeia `if (x.kind === ...)` em 2+ funções. Adicionar um tipo novo exige editar todas.
- Impacto: um ramo esquecido vira bug silencioso em `default`.
- Correção: tabela `Record<Kind, Handler>`, polimorfismo, ou union discriminada com `assertNever` no `default`. Um único `switch` local, estável, fica como está.

### 3. LSP: subtipo que quebra o contrato

- Sinal: override que lança `NotImplementedError`/`UnsupportedOperationException`, estreita pré-condição (valida mais que a base), retorna `null` onde a base promete valor, ou ignora argumento. `instanceof` no caller para tratar subclasse especial.
- Impacto: o caller correto da abstração falha em runtime com subtipo específico.
- Correção: separar a interface, trocar herança por composição, ou remover o método da abstração.

### 4. ISP: interface gorda

- Sinal: interface/port com 8+ métodos onde cada consumidor usa 1-2. Mocks de teste com 6 métodos vazios. Props de componente com 15 chaves repassadas inteiras.
- Impacto: consumidor depende do que não usa. Mudança num método recompila e retesta todos.
- Correção: interfaces por papel (`Reader`, `Writer`), `Pick<>` na assinatura do consumidor, props agrupadas por responsabilidade.

### 5. DIP em nível de classe

- Sinal: `new HttpClient()`, `new PrismaClient()`, `new OpenAI()`, `new Redis()` dentro de lógica de negócio. Import direto de singleton de IO (`import { db } from './db'`) usado no meio de regra. `Date.now()`, `Math.random()`, `uuid()` chamados em lógica que o teste precisa fixar.
- Impacto: teste sem mock global é impossível. Troca de vendor reescreve a regra.
- Correção: receber a dependência por construtor (ou parâmetro), depender de interface mínima, injetar relógio e gerador de id. DIP entre camadas e módulos pertence a review-modularidade.

### 6. Smells de Fowler (reportar com sinal concreto)

- Long method: função com 50+ linhas e 3+ níveis de abstração. Corrija com extração por intenção, não por tamanho.
- Long parameter list: 4+ parâmetros posicionais, ou 3+ do mesmo tipo (`string, string, string`). Correção: objeto de parâmetros nomeado.
- Flag arguments: `doThing(x, true)`. Impacto: dois comportamentos em uma função, chamada ilegível. Correção: duas funções.
- Feature envy: método que usa mais campos de outro objeto que do próprio. Correção: mover o método para o dono dos dados.
- Data clumps: o mesmo grupo de 3+ campos viaja junto por várias assinaturas (`start`, `end`, `timezone`). Correção: objeto/value object.
- Divergent change: uma classe que muda por razões distintas a cada PR. Correção: dividir (SRP).
- Temporary field: campo da classe usado só em um fluxo e `undefined` nos outros. Correção: extrair classe ou passar por parâmetro.
- Message chains (Demeter): `a.getB().getC().doD()` atravessando 3+ objetos. Impacto: o caller conhece a estrutura interna. Correção: método delegador no dono. Encadeamento fluente de API desenhada para isso (builder, query builder, array methods) está correto.
- Middle man: classe que só delega. Correção: remover o intermediário.
- Refused bequest: subclasse que ignora ou desabilita a maioria da base. Correção: composição.
- Speculative generality: parâmetro, hook, interface ou generic sem segundo uso. Correção: remover.
- Dead code: função, branch, export, parâmetro sem uso. Correção: remover (git guarda o histórico).

### 7. Efeitos colaterais e estado

- Sinal: getter, `isX()`, `calculateX()` ou `useMemo` que grava em banco, dispara evento, muta campo ou faz IO. Função `validate` que também normaliza e salva.
- Impacto: o caller que acha estar lendo causa escrita. Chamar duas vezes duplica o efeito. Teste quebra por ordem.
- Correção: separar consulta e comando (CQS). Nome com verbo de ação na função que escreve.
- Sinal: mutação de parâmetro (`arr.sort()`, `obj.field = ...`, `push` em argumento). Impacto: o caller perde o dado original. Correção: copiar (`[...arr].sort()`, `toSorted`, spread) ou retornar novo valor.
- Sinal: estado global mutável (`let cache = {}` no módulo, singleton com campos escritos por requests). Impacto: vazamento entre requests e entre testes. Correção: injetar o estado, escopo por request, ou módulo imutável.

### 8. Fluxo de controle

- Sinal: `if` aninhado em 3+ níveis, `else` depois de `return`, pirâmide de `try/catch`. Correção: guard clauses no início, retorno antecipado, extração de ramo.
- Sinal: `null` com 2+ significados (ausente, erro, vazio). Impacto: o caller trata um deles por acaso. Correção: `Result`/union discriminada (`{ ok: true, value } | { ok: false, error }`), exceção de domínio tipada, ou `Optional` explícito.
- Sinal: booleano de retorno com sentido de erro (`return false` quando falha). Correção: erro explícito com a causa.

### 9. Functional core, imperative shell

- Sinal: regra de decisão misturada com leitura de banco e chamada HTTP na mesma função. Impossível testar sem mock.
- Correção: o shell lê os dados, chama função pura `decide(input): Decision`, e executa a decisão. O core não importa IO.
- Aplicação em UI: hook de efeito e fetch na borda, função pura de cálculo no centro, componente apresentacional.

### 10. Primitive obsession conceitual

- Sinal: CPF, e-mail, dinheiro, período, percentual, id de matrícula como `string`/`number` crus com validação repetida em volta. `amount: number` com centavos e reais misturados.
- Impacto: valor inválido circula pelo sistema. Parâmetros trocados de ordem compilam.
- Correção: value object com construtor que valida (`Money.fromCents`, `Cpf.parse`), imutável, com igualdade por valor. Branded types para ids são de review-tipagem.

## Fora de escopo

| Tema | Dono |
|---|---|
| Naming, complexidade cognitiva, ordem de leitura | review-legibilidade |
| Fronteiras entre módulos/camadas/repos, ciclos, DIP entre camadas | review-modularidade |
| Regra de negócio duplicada, abstração prematura | review-dry |
| Branded types, `any`, `as`, unions e exaustividade como tema de tipos | review-tipagem |
| Erro engolido, timeout, retry | review-resiliencia |
| Re-render, effects e bundle | review-front |
| Shape de API | review-contratos |
| Testes | test-audit |

Value object e primitive obsession conceitual pertencem a esta skill. Branded type para ids pertence a review-tipagem.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia o reference da tecnologia detectada, entre `typescript.md`, `react.md`, `nestjs.md` e `python.md`. Liste os carregados em `stack_references_loaded`.
3. Obtenha o diff. Com context packet do orquestrador, use o packet. Standalone, detecte a base (`main`, `master` ou `develop`; `--base` vence) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`) e arquivos novos não rastreados. `--path` filtra por glob.
4. Para cada função, classe ou componente alterado, leia o arquivo inteiro. O hunk não mostra campos de estado, dependências nem os outros métodos.
5. Analise com 5 perguntas. Quantos motivos de mudança esta unidade tem? Quais efeitos ela produz além do retorno? De onde vêm as dependências de IO e de tempo? O que acontece ao adicionar o próximo caso (tipo, variante, parâmetro)? Um dev consegue testar a regra sem subir infraestrutura?
6. Verifique o contexto. Abra os callers (`git grep -n 'nomeDaFuncao('`), os overrides e as implementações da interface. Confirme que o smell existe no uso real. Verifique se o repo adota convenção local que explica o padrão (ex.: o framework impõe a classe com decorators).
7. Classifique pela rubrica abaixo e pelo `severity-rubric.md`.
8. Emita no formato do `output-contract.md`: bloco JSON, depois markdown. Prefixo dos ids: `CLN`. Standalone: mostre o markdown ao final e não altere código.

Categorias (`category`): `SRP`, `OCP`, `LSP`, `ISP`, `DIP`, `long-method`, `parameter-list`, `flag-argument`, `feature-envy`, `data-clumps`, `divergent-change`, `temporary-field`, `message-chain`, `middle-man`, `refused-bequest`, `speculative-generality`, `dead-code`, `side-effect`, `CQS`, `mutacao-de-parametro`, `estado-global`, `aninhamento`, `null-ambiguo`, `functional-core`, `primitive-obsession`.

## Rubrica de severidade do tema

**BLOCKER**
- Função com nome de leitura (`getX`, `isValid`) que grava no banco ou publica evento, chamada em render, em `useMemo` ou em loop de retry. O efeito duplica em produção.
- Estado mutável de módulo compartilhado entre requests de um servidor (`let currentUser` no escopo do módulo, escrito no handler). Vaza dado de um usuário para outro.
- Override que lança `NotImplemented` num ponto que o fluxo principal chama via abstração.

**MAJOR**
- Classe de serviço com 3+ motivos de mudança, que o diff aumenta (mais um caso de uso misturado com IO e formatação).
- `switch` por tipo copiado em 3+ funções, e o diff adiciona um tipo editando só alguns.
- Mutação de parâmetro que o caller reutiliza depois (`sort` in place num array vindo de cache).
- Lógica de decisão com `new` de client de IO dentro, sem seam de teste, em código crítico (pagamento, matrícula, nota).
- `null` com 3 significados num retorno consumido em 4 lugares.

**MINOR**
- Função com 5 parâmetros posicionais criada no diff.
- Flag argument booleano novo em função com 2 callers.
- Aninhamento de 4 níveis resolvível com guard clauses.
- Feature envy em método recém-criado.
- Value object ausente para `period` com 3 campos (start, end, tz) repetidos em 5 assinaturas.

**NIT**
- Middle man pequeno.
- Dead code de 2 linhas no hunk.
- Parâmetro opcional sem uso.

## Heurísticas anti-falso-positivo

- Meça dor real. "Viola SRP" sem 2 motivos de mudança nomeados não é achado.
- Tamanho sozinho não prova long method. Uma função linear de 60 linhas (montar objeto de configuração, tabela de mapeamento) lê melhor que 6 funções de 10 linhas.
- Orquestração é responsabilidade legítima. Controller, use case e handler de fila que coordenam 3-5 chamadas têm uma responsabilidade: coordenar. Reporte quando a regra mora no orquestrador.
- Controllers e resolvers do framework (decorators, `@Injectable`) impõem a forma de classe. Não reporte "classe sem estado" ou "classe só com métodos".
- Builders, query builders, `Array` methods, `zod` e jQuery-like fluentes têm encadeamento por design. Demeter não se aplica.
- DTO, entidade de ORM e props são estruturas de dados. Getters/setters simples e campos públicos nelas não são "data class smell".
- Hooks React com efeito são o lugar de efeito. Reporte efeito escondido em função com nome de cálculo, não o `useEffect`.
- Parâmetros em cascata de composição raiz (módulo, `main.ts`) são esperados. O DIP se verifica na lógica, não no ponto de montagem.
- Uma única implementação de interface é legítima quando a interface existe por seam de teste ou fronteira. Speculative generality exige ausência de uso, de teste e de fronteira.
- Código gerado, migrations, mocks e fixtures de teste ficam fora.
- Dívida anterior ao diff vai para `preexisting_debt` (no máximo 3).
- Um refactor grande que o diff pede e o time não adotou é MINOR com `effort: L`. O achado propõe o primeiro passo pequeno.

## Ferramentas determinísticas opcionais

Rode só se instaladas. A saída é insumo, não veredito.

- ESLint (complexity, max-params, max-lines-per-function, max-depth, no-param-reassign, no-else-return). Checagem: `ls node_modules/.bin/eslint`. Execução: `npx --no-install eslint --no-eslintrc --rule '{"max-params":["warn",4],"max-depth":["warn",3],"no-param-reassign":"warn","max-lines-per-function":["warn",60]}' <arquivos do diff>`. Respeite a config do repo: se o repo já define essas regras, use `npx --no-install eslint <arquivos>`.
- knip e ts-prune para dead code. Checagem: `ls node_modules/.bin/knip`. Execução: `npx --no-install knip --reporter json`.
- Python: `radon cc -s -n C <paths>` (complexidade), `vulture <paths>` (dead code), `ruff check --select PLR0913,PLR0912,PLR0915,C901 <paths>`. Checagem: `command -v radon vulture ruff`.

## Exemplos

### Achado 1: efeito oculto em leitura

```json
{
  "id": "CLN-001",
  "agent": "review-clean",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "side-effect",
  "location": { "repo": "api-bff", "file": "src/progress/progress.service.ts", "lines": "31-47" },
  "evidence": "async getCourseProgress(userId: string, courseId: string) {\n  const p = await this.repo.findProgress(userId, courseId);\n  if (p.percent === 100 && !p.completedAt) {\n    await this.repo.markCompleted(p.id);\n    await this.events.publish('course.completed', { userId, courseId });\n  }\n  return p;\n}",
  "problem": "getCourseProgress lê e também conclui o curso e publica `course.completed`. O endpoint GET /progress chama o método a cada abertura de tela, e o job de relatório também o chama (relatorio.job.ts:22). Cada chamada concorrente com percent 100 e completedAt vazio publica o evento mais de uma vez. O consumidor emite o certificado duas vezes. A leitura passa a ter efeito, e o teste de unidade da tela precisa mockar o publisher.",
  "fix": "Separar consulta e comando.\nasync getCourseProgress(userId, courseId) { return this.repo.findProgress(userId, courseId); }\nasync completeCourse(userId, courseId) {\n  const done = await this.repo.markCompletedIfPending(userId, courseId); // UPDATE ... WHERE completed_at IS NULL\n  if (done) await this.events.publish('course.completed', { userId, courseId });\n}\nQuem hoje depende do efeito chama completeCourse num fluxo de escrita.",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["Command-Query Separation (Meyer)"],
  "introduced_by_diff": true
}
```

### Achado 2: dependência de IO presa na regra

```json
{
  "id": "CLN-002",
  "agent": "review-clean",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "DIP",
  "location": { "repo": "api-bff", "file": "src/exams/grade.calculator.ts", "lines": "8-29" },
  "evidence": "export async function calculateFinalGrade(examId: string) {\n  const prisma = new PrismaClient();\n  const answers = await prisma.answer.findMany({ where: { examId } });\n  const weight = new Date() > DEADLINE ? 0.8 : 1;\n  return answers.reduce((s, a) => s + a.score, 0) * weight;\n}",
  "problem": "A regra de nota instancia PrismaClient e lê o relógio dentro da função. O teste não fixa o horário nem substitui o banco sem mock global do módulo. Cada chamada abre um pool novo. A regra de penalidade (0.8 após o prazo) só se verifica com banco real e data real.",
  "fix": "Extrair o núcleo puro e injetar o resto.\nexport const finalGrade = (scores: number[], submittedAt: Date, deadline: Date) =>\n  scores.reduce((s, x) => s + x, 0) * (submittedAt > deadline ? 0.8 : 1);\n// o service lê answers via repo injetado e passa submittedAt vindo da submissão",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["Functional core, imperative shell"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

`CourseController.getCourse()` chama `this.courseService.find(id)`, depois `this.progressService.forUser(user, id)` e `this.ratingService.summary(id)`, e monta a resposta com 3 linhas. A função tem 3 dependências e nenhuma regra de negócio. Controller que coordena chamadas e monta resposta tem uma responsabilidade. Dividir em um "CourseResponseAssembler" adiciona uma camada sem motivo de mudança novo. Não reporte. Se o controller calculasse o percentual ali, seria MAJOR.
