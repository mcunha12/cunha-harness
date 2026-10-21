---
name: review-modularidade
description: Revisa fronteiras, camadas e acoplamento em diff ou PR (MOD). Acione em "revisa a arquitetura desse PR", "isso respeita as camadas?", "tem ciclo de import?", /review-modularidade, ou via master-review. Cobre regra de dependência (controller, service, repository), domínio importando infra, ciclos, responsabilidade por serviço e repo, camada de agregação com regra de domínio, vazamento de internals (deep imports, barrel files), SDK de vendor no domínio, coesão por feature, acoplamento aferente e eferente, shotgun surgery, código compartilhado entre repos, side effects no import, singletons, NestJS (módulos, providers, forwardRef) e Module Federation (contrato host e remote). Não cobre SRP de classe e smells de função (review-clean), duplicação (review-dry), shape de API (review-contratos), naming (review-legibilidade).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-modularidade

## Missão

Verificar que o diff respeita as fronteiras do sistema: entre camadas dentro de um repo, entre módulos, entre pacotes e entre serviços. O critério é a direção das dependências e o custo de mudança. Cada import cria acoplamento. O achado nomeia a aresta indevida (`A importa B`), a regra que ela viola e o que quebra quando B mudar. A arquitetura vigente se descobre no repo (README, `CLAUDE.md`, config de lint, estrutura de diretórios, `repo_role` da config do orquestrador). A skill nunca presume o papel de um repo pelo nome. Sem arquitetura declarada, aplica a regra de dependência universal (política depende de detalhe: proibido) e marca a confiança como média.

## Escopo

Cada item segue: sinal no código, impacto, correção típica.

### 1. Regra de dependência entre camadas

- Sinal: controller/handler/resolver importando repository, ORM ou client de vendor direto. Service importando `express`/`Request`/DTO HTTP. Domínio (entidades, regras) importando `@prisma/client`, `axios`, SDK de LLM, `@nestjs/*`, React. Repository chamando service. Infra importando caso de uso.
- Impacto: troca de ORM, de transporte ou de vendor reescreve a regra. Teste de regra exige infraestrutura.
- Correção: a seta aponta para dentro. Controller → service/use case → port (interface) ← adapter (infra). Mover a regra para o service, a chamada ao vendor para um adapter, e injetar. Se o repo é CRUD fino sem domínio, controller → service → repository basta. Exigir hexagonal ali é excesso.

### 2. Ciclos

- Sinal: `A → B → A` direto ou indireto (3+ arquivos), ciclo entre pastas de feature, `forwardRef` no Nest, import tardio dentro de função para fugir do erro, `import type` usado para esconder ciclo, `undefined` em runtime no import.
- Impacto: ordem de carga define o comportamento. `undefined` intermitente, falha só em bundle de produção, impossibilidade de extrair um dos lados.
- Correção: extrair o conceito comum para um terceiro módulo que os dois importam, inverter a dependência com interface, ou fundir os módulos se mudam sempre juntos. `forwardRef` é sintoma, a correção é a extração.

### 3. Responsabilidade por serviço e por repo

- Sinal: camada de agregação para o front (BFF/gateway, conforme README/config) com regra de domínio: cálculo de elegibilidade, preço, progresso, decisão de acesso, máquina de estado, validação de invariante. Cliente (web, app) chamando um serviço de dados diretamente quando a arquitetura define o gateway como porta de entrada. Serviço de domínio formatando resposta para uma tela específica. Orquestração de LLM fora do serviço que a arquitetura designa para IA.
- Impacto: a regra existe em dois donos e diverge. O gateway vira ponto de acoplamento de deploy. Segredo e custo de LLM migram para a camada errada.
- Correção: mover a regra para o serviço dono do domínio, expor o resultado por endpoint, e deixar a camada de agregação só compor, autorizar a borda e adaptar o shape. Cite no `problem` a fonte da arquitetura que sustenta a leitura (trecho do README, config, estrutura). Sem fonte, confiança baixa.

### 4. Vazamento de internals

- Sinal: deep import (`import { x } from '@org/pkg/dist/internal/x'`, `../../other-feature/internal/helper`) atravessando a API pública de outro módulo. Barrel `index.ts` com `export *` de tudo. Export público de símbolo usado em um único arquivo do próprio módulo. Teste importando privado de outro módulo.
- Impacto: qualquer refactor interno do dono quebra consumidores. Barrel que reexporta tudo puxa o módulo inteiro para o bundle e cria ciclos. Superfície pública grande trava a evolução.
- Correção: expor um `index.ts` curto, com exports nomeados deliberados, e importar só por ele. Remover `export` do que é interno. Regra de lint (`no-restricted-imports`, `eslint-plugin-boundaries`, `exports` do `package.json`) para travar.

### 5. SDK de vendor no domínio

- Sinal: tipos do SDK (`OpenAI.Chat.ChatCompletion`, `Stripe.Charge`, `PrismaClient`, `AxiosResponse`) em assinatura de função de domínio, em retorno de service, em props de componente de negócio. Regra que conhece formato de erro do vendor.
- Impacto: trocar de vendor ou de versão maior do SDK atravessa todo o código. O teste depende do mock do SDK.
- Correção: port com tipo próprio (`LlmClient.complete(input): Completion`) e adapter que traduz. O tipo do vendor não cruza a fronteira. Para ORM em app CRUD, o tipo gerado do Prisma como modelo de dados costuma ser aceito pelo padrão do repo.

### 6. Coesão: feature contra tipo técnico

- Sinal: estrutura por tipo técnico (`controllers/`, `services/`, `utils/`, `types/`) em que uma feature espalha 6+ arquivos em 5 pastas, ou um `utils/` e `common/` que crescem a cada PR. God module: arquivo ou pasta com 20+ exports de assuntos distintos.
- Impacto: uma mudança de feature toca N pastas. `utils` vira o ponto de acoplamento de todo mundo.
- Correção: agrupar por feature/domínio (`enrollment/`, `exam/`) com API pública própria. Mover cada util para o módulo que o usa. Estrutura existente do repo prevalece para código antigo, e o código novo segue a direção escolhida pelo time.

### 7. Acoplamento aferente, eferente e instabilidade

- Sinal: módulo novo importando 8+ módulos distintos (Ce alto), ou módulo com 15+ dependentes que o diff altera de forma incompatível (Ca alto). Instabilidade I = Ce / (Ca + Ce). Módulo estável (I perto de 0) dependendo de instável (I perto de 1).
- Impacto: módulo estável com dependência instável muda toda vez que o instável muda. Alto Ce indica falta de coesão.
- Correção: inverter a dependência (estável define interface, instável implementa), extrair interface mínima, quebrar o módulo de alto Ce. Princípio das dependências estáveis: depender na direção da estabilidade.

### 8. Shotgun surgery

- Sinal: o diff toca 6+ arquivos em 4+ pastas para uma única mudança de regra ou campo (adicionar um status, um tipo de curso, um campo de payload). Mesmo literal ou assinatura editada em N pontos.
- Impacto: cada nova variante repete a edição em N lugares, e um esquecido vira bug.
- Correção: concentrar a decisão num ponto (tabela de configuração, estratégia, módulo dono). Duplicação de regra é de review-dry. Aqui o foco é a falta de um módulo que contenha a mudança.

### 9. Código compartilhado entre repos

- Sinal: arquivo copiado de repo irmão (cabeçalho, nome e conteúdo iguais), `git submodule` ou script de sync, tipos de outro serviço colados à mão, workspace que importa por caminho relativo fora do pacote (`../../other-app/src`).
- Impacto: cópias divergem. Correção em um repo não chega no outro.
- Correção: pacote versionado com semver e changelog, ou geração de código a partir do schema de origem. Sem pacote viável, cópia com teste de paridade e one-liner citando a origem. Regras duplicadas pertencem a review-dry.

### 10. Side effects no import e singletons

- Sinal: módulo que conecta ao banco, abre socket, lê env com `process.exit`, registra listener global, inicia timer ou faz fetch ao ser importado. Singleton exportado com estado mutável (`export const client = new X()` configurado por quem chega primeiro). `import './polyfill'` com efeito em módulo de domínio.
- Impacto: ordem de import muda o comportamento. Teste herda conexão aberta. SSR e Module Federation executam o efeito em ambientes errados.
- Correção: exportar factory (`createClient(config)`), inicializar na raiz de composição (`main.ts`, bootstrap, entrypoint). Constante pura e módulo sem efeito são aceitáveis.

### 11. NestJS

- `forwardRef(() => XModule)` ou `@Inject(forwardRef(...))`: ciclo entre módulos ou providers. Reportar o ciclo e a extração.
- Provider usado por outro módulo sem estar em `exports`, e import do arquivo da classe direto em vez do módulo: bypass da fronteira.
- `exports` com 10+ providers: superfície pública excessiva.
- `@Global()` em módulo de feature. Reservado para infra transversal (config, logger).
- Módulo "shared" que importa módulos de feature (seta invertida).
- Controller injetando repository ou `PrismaService`. Detalhes em `references/nestjs.md`.

### 12. Module Federation e micro-frontends

- Contrato de props host → remote e módulos expostos são API pública versionada. Alterar shape sem ordem de deploy documentada quebra produção, porque o remote carrega ao vivo.
- Singletons (`react`, `react-dom`, `styled-components`) fixados no `shared`. Versão fora do range fixado ou `singleton: false` em lib com contexto duplica o runtime.
- Remote consumido sem boundary de erro: reportar conforme a convenção do repo. A convenção do repo (CLAUDE.md) vence.
- Host importando arquivo de dentro do remote por caminho relativo ou o remote importando do host. Detalhes em `references/react.md`.

## Fora de escopo

| Tema | Dono |
|---|---|
| SRP, smells, efeitos colaterais, DIP entre classes | review-clean |
| Regra de negócio duplicada, abstração prematura | review-dry |
| Breaking change de API, shape de payload, ordem de deploy de contrato | review-contratos |
| Naming, fluxo de leitura | review-legibilidade |
| Tipo redeclarado, `any`, branded types | review-tipagem |
| Bundle size, code splitting, re-render | review-front |
| Autorização e segredos | review-seguranca |
| Timeouts, retry, graceful shutdown | review-resiliencia |
| DDL e migrations | review-migrations |
| Testes | test-audit |

Fronteiras entre módulos, camadas e repos, DIP entre camadas e ciclos pertencem a esta skill. DIP dentro de uma classe (`new` de client em método) pertence a review-clean. Shotgun surgery pertence a esta skill. Regra duplicada pertence a review-dry.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia o reference da tecnologia detectada, entre `typescript.md`, `react.md` (inclui Module Federation e Next), `nestjs.md`, `node.md` e `python.md`. Liste os carregados em `stack_references_loaded`.
3. Descubra a arquitetura declarada. Leia `README.md`, `CLAUDE.md`, `docs/`, `.dependency-cruiser.*`, `eslint.config.*` (regras `boundaries`, `no-restricted-imports`), `tsconfig` paths, `package.json` (`exports`, workspaces), `webpack.config.*` (ModuleFederationPlugin) e a estrutura de `src/`. Registre as camadas e as regras que o repo declara. Com `repo_role` e `related_repos` na config do orquestrador, use-os.
4. Obtenha o diff. Com context packet do orquestrador, use o packet. Standalone, detecte a base (`main`, `master` ou `develop`; `--base` vence) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`) e arquivos novos não rastreados. `--path` filtra por glob.
5. Analise as arestas novas. Liste cada `import`/`require`/injeção adicionados no diff como `origem → destino`. Classifique a camada de cada ponta. Marque as arestas que cruzam fronteira (camada, feature, pacote, repo).
6. Verifique o contexto. Abra o destino da aresta e confirme o que é público. Rode `git grep -n "from '.*<modulo>"` para contar dependentes (Ca). Procure o caminho de volta para detectar ciclo. Leia o `index.ts`/`exports`/módulo Nest do destino. Em ciclo suspeito, rode `madge` ou `dependency-cruiser` se existirem. Em repo irmão (config `related_repos`), busque o uso do que o diff muda.
7. Classifique pela rubrica abaixo e pelo `severity-rubric.md`. Sem arquitetura declarada, rebaixe a confiança de violação de camada para média.
8. Emita no formato do `output-contract.md`: bloco JSON, depois markdown. Prefixo dos ids: `MOD`. Standalone: mostre o markdown ao final e não altere código.

Categorias (`category`): `regra-de-dependencia`, `ciclo`, `responsabilidade-de-servico`, `bypass-de-gateway`, `deep-import`, `barrel`, `export-excessivo`, `vendor-no-dominio`, `coesao`, `acoplamento`, `shotgun-surgery`, `codigo-compartilhado`, `side-effect-no-import`, `singleton`, `nest-modulo`, `module-federation`.

## Rubrica de severidade do tema

**BLOCKER**
- Ciclo de import que produz `undefined` em runtime ou falha no bundle de produção, comprovado pelo código (constante usada no topo de um módulo do ciclo).
- Módulo exposto do remote tem o shape de props alterado e o host ainda envia o shape antigo, sem ordem de deploy no PR.
- Side effect no import que abre conexão ou registra listener, em módulo importado por código de browser e de servidor (SSR) ou por testes.
- Regra de autorização ou de acesso movida para a camada de agregação, enquanto o serviço de domínio continua aceitando chamada direta sem checagem.

**MAJOR**
- Domínio importando ORM/SDK/HTTP client, com 3+ arquivos de regra afetados.
- Camada de agregação ganhando regra de negócio (cálculo, elegibilidade) com o serviço dono existente.
- Cliente chamando serviço interno por fora do gateway que o README define como porta.
- `forwardRef` novo entre módulos Nest.
- Deep import em módulo de outra feature, em 3+ pontos.
- Barrel `export *` que fecha ciclo ou arrasta módulo pesado para a rota inicial.
- Módulo estável (15+ dependentes) passa a depender de módulo instável.
- Shotgun surgery com 6+ arquivos para uma variante que o diff adiciona.

**MINOR**
- Deep import único em outra feature.
- Export público sem uso externo.
- `utils/` ganhando função de uma feature só.
- Barrel novo com `export *` sem ciclo.
- Singleton exportado em vez de factory, sem efeito no import.

**NIT**
- Pasta por tipo técnico em feature nova, quando o repo todo é assim.
- Ordem de imports entre camadas sem regra declarada.

## Heurísticas anti-falso-positivo

- A arquitetura declarada vence a preferência pessoal. Repo CRUD com controller → service → Prisma não precisa de ports.
- Confira o `repo_role` e o README antes de acusar "regra na camada errada". Camada de agregação que filtra campos, junta respostas, converte shape e autoriza a borda cumpre o papel. Cálculo que decide acesso ou valor de negócio é a violação.
- Importar tipo (`import type`) de outro módulo para anotar assinatura tem custo bem menor que importar valor. Reduza um nível, e ainda reporte se o tipo é interno.
- Teste, fixture, story e arquivo de config podem cruzar fronteiras. O teste de integração importa o módulo real por desenho.
- Composition root (`main.ts`, `app.module.ts`, `providers/index.tsx`, bootstrap do remote) importa tudo por definição. Não aplique Ce alto nele.
- `@Global()` em config e logger é aceito. `forwardRef` já existente fora do diff é débito (`preexisting_debt`).
- Barrel pequeno e deliberado de um módulo (5-10 exports nomeados) é API pública. Reporte `export *` em árvore grande.
- Pacote interno dentro de monorepo com `exports` definido: importar pelo nome do pacote é a forma correta.
- Duas features parecidas que importam a mesma lib compartilhada não têm acoplamento entre si.
- Antes de reportar ciclo, confirme que o caminho de volta existe lendo o arquivo. Ciclo só de tipos (`import type`) some em compilação e é MINOR.
- Mudança só de mover arquivo (rename com imports atualizados) não cria acoplamento novo.
- Convenção do repo para MFE (como `LABErrorBoundary` ao redor de remote) é lida do `CLAUDE.md`. A skill cobra o que o repo declara.

## Ferramentas determinísticas opcionais

Rode só se instaladas. Nunca instale. A saída é insumo, não veredito.

- dependency-cruiser. Checagem: `ls node_modules/.bin/depcruise` e config `.dependency-cruiser.*`. Execução: `npx --no-install depcruise --config -- src` ou `npx --no-install depcruise --output-type err-long src`. Sem config do repo, use `--no-config --output-type json src` e filtre `circular` e `orphans`.
- madge. Checagem: `ls node_modules/.bin/madge`. Execução: `npx --no-install madge --circular --extensions ts,tsx src`.
- knip (exports e arquivos sem uso). Checagem: `ls node_modules/.bin/knip`. Execução: `npx --no-install knip --reporter json`. ts-prune como alternativa: `npx --no-install ts-prune`.
- eslint-plugin-boundaries / `no-restricted-imports`. Checagem: procurar `boundaries` ou `no-restricted-imports` em `eslint.config.*`/`.eslintrc*`. Execução: `npx --no-install eslint <arquivos do diff>`.
- Python: import-linter. Checagem: `command -v lint-imports` e `.importlinter` ou `[tool.importlinter]`. Execução: `lint-imports`. Ciclos: `pydeps <pacote> --show-cycles` (se instalado).
- Fallback sem ferramenta: `git grep -n -E "from ['\"].*<modulo>"` para contar dependentes. Para ciclo curto, leia os imports dos dois arquivos.

## Exemplos

### Achado 1: regra de domínio no gateway

```json
{
  "id": "MOD-001",
  "agent": "review-modularidade",
  "severity": "MAJOR",
  "confidence": "media",
  "category": "responsabilidade-de-servico",
  "location": { "repo": "api-bff", "file": "src/certificates/certificates.service.ts", "lines": "22-39" },
  "evidence": "const eligible = progress.completedLessons / progress.totalLessons >= 0.75 && !enrollment.suspended;\nif (!eligible) throw new ForbiddenException('Não elegível');\nreturn this.apiClient.post('/certificates', { enrollmentId });",
  "problem": "O README do repo descreve o serviço como BFF do front (agrega e adapta respostas). O service decide elegibilidade ao certificado (75% de progresso, matrícula não suspensa) antes de chamar a API. A regra de domínio passa a existir no BFF. O endpoint POST /certificates da API aceita a chamada sem checar elegibilidade (certificates.controller.ts:30 em pos-api, via related_repos). Qualquer cliente que chame a API direto emite o certificado. Mudar o limiar exige alterar o BFF e confirmar a API. Confiança média: não verifiquei se a API tem outra guarda no service.",
  "fix": "A API valida elegibilidade no caso de uso e responde 409 com o motivo. O BFF repassa o erro e remove a regra.\n- const eligible = progress.completedLessons / progress.totalLessons >= 0.75 && !enrollment.suspended;\n- if (!eligible) throw new ForbiddenException('Não elegível');\n  return this.apiClient.post('/certificates', { enrollmentId });\nOrdem de mudança: API primeiro (validação), BFF depois (remoção).",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["Dependency Rule", "README: BFF do front"],
  "introduced_by_diff": true
}
```

### Achado 2: ciclo disfarçado por forwardRef

```json
{
  "id": "MOD-002",
  "agent": "review-modularidade",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "ciclo",
  "location": { "repo": "pos-api", "file": "src/enrollments/enrollments.module.ts", "lines": "8-16" },
  "evidence": "@Module({\n  imports: [forwardRef(() => ClassesModule)],\n  providers: [EnrollmentsService],\n  exports: [EnrollmentsService],\n})",
  "problem": "EnrollmentsModule importa ClassesModule via forwardRef. ClassesModule já importa EnrollmentsModule (classes.module.ts:6) para ler a matrícula do aluno. O diff adiciona o caminho de volta porque EnrollmentsService passa a chamar ClassesService.getVacancies() (enrollments.service.ts:57). O forwardRef faz o Nest subir, e mascara o ciclo. Os dois módulos só se carregam juntos e nenhum dos dois se testa sem o outro. Cada mudança numa assinatura de ClassesService afeta matrícula.",
  "fix": "Extrair a consulta de vagas para um provider sem dependência de matrícula e importá-lo nos dois módulos.\n// vacancies/vacancies.module.ts\n@Module({ providers: [VacanciesService], exports: [VacanciesService] })\nexport class VacanciesModule {}\n// enrollments.module.ts\n@Module({ imports: [VacanciesModule], providers: [EnrollmentsService] })\nO ClassesService delega a VacanciesService e ClassesModule deixa de ser importado por EnrollmentsModule.",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["Acyclic Dependencies Principle"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

`app.module.ts` do serviço importa 14 módulos de feature, e `src/providers/index.tsx` do front monta 7 providers aninhados. Os dois arquivos são composition root: o papel deles é conhecer tudo para ligar as partes. O acoplamento eferente alto ali não tem custo de mudança, porque nenhum módulo depende deles. Não reporte Ce alto nem "god module". Reporte só se um módulo de feature importar o composition root.
