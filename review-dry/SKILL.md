---
name: review-dry
description: Revisa duplicação de conhecimento (DRY) em diff ou PR. Acione em "revisa a duplicação desse PR", "tem regra copiada aqui?", /review-dry, ou via master-review. Cobre regra de negócio replicada entre camadas e repos, validações divergentes, magic values repetidos, copy-paste com variação, mapeamentos de DTO e enums espelhados, e o lado inverso (abstração prematura, wrong abstraction, god util com flags). Não cobre naming ou complexidade (review-legibilidade), SRP e smells de função (review-clean), fronteiras de módulo (review-modularidade), tipo redeclarado (review-tipagem), SQL e performance (review-queries).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-dry

## Missão

Encontrar conhecimento duplicado e abstração errada no diff. DRY mede conhecimento (Hunt & Thomas), não caracteres. O teste de cada candidato: "se essa regra mudar, quantos lugares mudam, e pelo mesmo motivo?" Mais de um lugar pelo mesmo motivo é duplicação. Dois trechos parecidos que mudam por motivos diferentes são coincidência, e unificá-los cria acoplamento. A skill reporta os dois erros: a cópia que diverge e a abstração que força trechos distintos a andar juntos.

## Escopo

Cada item segue: sinal no código, impacto, correção típica.

### 1. Regra de negócio replicada

- Sinal: a mesma regra (progresso, elegibilidade, preço, prazo, permissão, transição de estado, arredondamento, janela de datas) aparece em dois ou mais pontos: componente e hook, front e BFF, serviço e job, repo A e repo B. Procure por constantes numéricas de domínio, comparações de status, fórmulas de percentual.
- Impacto: as cópias divergem no primeiro ajuste. Divergência sutil (`>=` contra `>`, truncar contra arredondar, fuso diferente) gera valor diferente para o mesmo aluno em duas telas. Divergência observável por usuário ou por dinheiro é BLOCKER ou MAJOR.
- Correção: eleger uma fonte da verdade. A fonte fica onde o dado nasce (normalmente o serviço dono do domínio). Os demais consomem o campo pronto, ou importam função pura de pacote versionado. Se a cópia no cliente é inevitável (validação otimista), cite a fonte no código com one-liner e mantenha um teste que compara as duas.

### 2. Validação duplicada e divergente

- Sinal: o mesmo campo validado em formulário, DTO e schema de banco com regras diferentes (min/max, regex, obrigatoriedade). Dois schemas zod para a mesma entidade. `class-validator` e tipo TS escritos à mão.
- Impacto: o cliente aceita o que o servidor rejeita, ou o servidor aceita o que o banco rejeita. Resultado: erro 500 ou dado inconsistente.
- Correção: derivar. `z.infer` e `.pick`/`.extend` a partir de um schema base. DTO gerado do OpenAPI. Validação duplicada por camada é aceitável quando as duas derivam do mesmo schema.

### 3. Constantes e magic values repetidos

- Sinal: o mesmo literal (limite, timeout, status string, URL, chave de feature flag, nome de evento de analytics, chave de cache, nome de fila) em 2+ arquivos.
- Impacto: renomear uma ocorrência quebra as outras sem erro de compilação. Chave de flag escrita à mão em 3 lugares: um typo desliga a feature em um só.
- Correção: constante nomeada exportada de um módulo dono (`as const`), consumida nos pontos de uso. Literal repetido sem relação de domínio (`0`, `1`, `'id'`) fica fora.

### 4. Copy-paste com pequenas variações

- Sinal: blocos de 8+ linhas que diferem em 1-3 tokens (nome do campo, rota, tipo). Handlers, hooks de fetch, reducers, testes de setup e seções de JSX quase idênticos.
- Impacto: correção de bug aplicada em uma cópia só. Número de cópias = número de lugares a lembrar.
- Correção: extrair função ou componente parametrizado pelo que varia, desde que a variação caiba em 1-2 parâmetros de dados. Variação em comportamento (callbacks, flags) pede o caso 8.

### 5. Mapeamentos de DTO copiados

- Sinal: o mesmo `toDomain`/`toResponse`/`mapX` reescrito em dois services. Campo a campo idêntico em controller, service e teste.
- Impacto: campo novo entra no mapper A e falta no B. O consumidor recebe `undefined` em uma rota.
- Correção: mapper único por entidade, colocado junto ao dono do tipo.

### 6. Queries, configs e infraestrutura repetidas

- Sinal: mesmo `where`/`select`/`include` em 3 métodos de repository. Mesma config de axios (baseURL, headers, interceptors) criada em vários módulos. Mesmo bloco de CI, Dockerfile ou env duplicado.
- Impacto: filtro de soft delete ou de tenant esquecido em uma das cópias. Vazamento de dado ou registro fantasma.
- Correção: fragment/const de `select`, método de repository nomeado, factory de client. Para filtros de segurança (tenant, soft delete), prefira extensão ou middleware do ORM.

### 7. Enums e contratos espelhados à mão entre repos

- Sinal: o mesmo union de strings, enum ou tabela de códigos declarado em dois repos. Tipo de resposta de API escrito à mão no consumidor.
- Impacto: valor novo no produtor chega ao consumidor como string desconhecida e cai em `default`. Silencioso em produção.
- Correção: gerar o tipo do OpenAPI/zod/proto do produtor, ou publicar pacote versionado. Sem pacote, o consumidor trata valor desconhecido de forma explícita e o PR cita a fonte.

### 8. Anti-DRY: abstração errada

- Abstração prematura: helper criado para 2 usos, antes da regra de três, ou para trechos que mudam por motivos distintos. Recomende manter duplicado.
- Acoplamento acidental: duas telas compartilham componente porque hoje se parecem. Uma nova exigência de uma delas força prop condicional.
- God util: função com 3+ parâmetros booleanos ou `options` com ramos por caller. Cada chamador usa 1 das combinações.
- Wrong abstraction (Sandi Metz): abstração que acumula `if (caller === ...)` a cada PR. Recomende inline nos callers e re-duplicar, depois extrair o que realmente permanece comum.
- Impacto: cada mudança exige entender todos os callers. A regressão em um caller quebra os outros.

## Fora de escopo

| Tema | Dono |
|---|---|
| Tipo redeclarado em vez de derivado (Pick/Omit/z.infer) | review-tipagem |
| Naming, complexidade cognitiva, fluxo | review-legibilidade |
| SRP e smells em função/classe | review-clean |
| Fronteiras entre módulos, camadas, repos, ciclos, shotgun surgery | review-modularidade |
| Shape de dados entre serviços e breaking changes | review-contratos |
| N+1, índices, cache | review-queries |
| Segredo hardcoded | review-seguranca |
| Comentários | review-comentarios |
| Testes | test-audit |

Regra de negócio duplicada pertence a esta skill. Shotgun surgery pertence a review-modularidade: aqui só se referencia.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia o reference da tecnologia detectada, entre `typescript.md`, `react.md`, `nestjs.md`, `prisma-postgres.md` e `python.md`. Liste os carregados em `stack_references_loaded`.
3. Obtenha o diff. Com context packet do orquestrador, use o packet. Standalone, detecte a base (`main`, `master` ou `develop`; o argumento `--base` vence) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua `git diff HEAD` (staged e unstaged) e arquivos novos não rastreados. `--path` filtra por glob.
4. Analise cada hunk com 3 perguntas. O trecho novo copia conhecimento que já existe? Algum trecho existente copia o conhecimento que o diff acabou de mudar (cópia que ficou para trás)? O diff cria abstração para menos de 3 usos reais?
5. Verifique o contexto antes de reportar. Rode `grep -rn` pelo literal, pelo nome da função, pelo nome do campo e pela forma da expressão em todo o repo. Com `related_repos` na config, rode a busca nos repos irmãos e liste cada cópia. Leia as duas cópias inteiras e confirme que mudam pelo mesmo motivo.
6. Classifique severidade e confiança pela rubrica abaixo e pelo `severity-rubric.md`.
7. Emita no formato do `output-contract.md`: bloco JSON, depois markdown. Prefixo dos ids: `DRY`. Standalone: mostre o markdown ao final e não altere código.

Saída extra de todo achado de duplicação:

- Liste todas as cópias no `problem`, no formato `repo/arquivo:linhas`, uma por linha.
- Nomeie a fonte da verdade sugerida e o motivo (onde o dado nasce, quem é dono do domínio).
- Se a cópia está em repo irmão, diga a ordem de mudança (fonte primeiro, consumidores depois) e inclua um `handoffs` para review-contratos quando houver shape de API envolvido.

Categorias (`category`): `regra-de-negocio`, `validacao`, `constante`, `copy-paste`, `mapper`, `query-config`, `enum-espelhado`, `abstracao-prematura`, `acoplamento-acidental`, `god-util`, `wrong-abstraction`.

## Rubrica de severidade do tema

**BLOCKER**
- Regra de cobrança, desconto, nota, aprovação ou acesso implementada em dois lugares com condição diferente, e o diff muda só um deles. Exemplo: `progress >= 0.75` no BFF e `progress > 0.75` no front para liberar certificado.
- Filtro de tenant ou de soft delete presente em 2 de 3 queries equivalentes, e o diff adiciona a terceira sem ele.
- Enum de status espelhado em dois repos, o produtor ganha um valor novo neste diff e o consumidor o trata como inválido com throw.

**MAJOR**
- Regra de domínio copiada em 2+ pontos, hoje idêntica, sem fonte única. Exemplo: cálculo de prazo de acesso em 3 componentes.
- Schema de validação duplicado com limites diferentes entre formulário e DTO.
- Wrong abstraction com 4+ ramos por caller, tocada pelo diff.
- God util com 3+ flags booleanas que o diff estende com mais uma.

**MINOR**
- Literal de domínio (chave de flag, nome de evento, timeout) repetido em 3+ arquivos.
- Mapper de DTO copiado em 2 services, hoje idêntico.
- Bloco copy-paste de 10+ linhas com variação em 2 tokens.

**NIT**
- Constante de config repetida em 2 arquivos de teste.
- Helper de 3 linhas reescrito em 2 lugares.

## Heurísticas anti-falso-positivo

- Meça por motivo de mudança. Trechos parecidos de telas com donos de produto diferentes não são cópia.
- Regra de três: 2 ocorrências sem relação de domínio ficam como NIT ou não se reportam. 3+ com mesmo motivo de mudança entram.
- Código de teste admite repetição. Fixtures explícitas valem mais que helper opaco. Reporte só regra de negócio copiada dentro do teste (resultado esperado calculado com a mesma fórmula do código).
- Tipos gerados, migrations, snapshots, arquivos de lock e código vendorizado ficam fora.
- DTO de entrada e DTO de saída com os mesmos campos têm ciclos de vida distintos. Reporte só quando o diff comprova divergência ou quando o schema tem derivação óbvia.
- Duas camadas validando o mesmo dado (defesa em profundidade) estão corretas quando derivam do mesmo schema ou quando a camada interna protege invariante própria.
- Adapters de vendor diferentes com forma parecida (um por provedor) expressam fronteira. Não unifique.
- Boilerplate imposto pelo framework (decorators do Nest, `useQuery` com a mesma forma) pede padrão consistente, não abstração.
- Antes de recomendar extração, confira se o repo já tem o helper. Se tem, o achado é "usar o existente".
- Verifique o histórico (`git log -S`) quando a duplicação parecer intencional. Comentário ou commit que explica a cópia encerra o achado.

## Ferramentas determinísticas opcionais

Rode só se instaladas. A saída é insumo, não veredito.

- jscpd. Checagem: `ls node_modules/.bin/jscpd` ou `command -v jscpd`. Execução: `jscpd --min-lines 8 --min-tokens 70 --reporters json --output /tmp/jscpd <paths do diff>`. Cruze os clones com os arquivos do diff.
- PMD CPD. Checagem: `command -v pmd`. Execução: `pmd cpd --minimum-tokens 100 --language typescript --dir <paths> --format csv`.
- Fallback sem ferramenta: `git grep -n -F '<literal>'` e `git grep -n -E '<regex da expressão>'` para cada literal e fórmula suspeitos do diff.

## Exemplos

### Achado 1: regra duplicada com divergência

```json
{
  "id": "DRY-001",
  "agent": "review-dry",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "regra-de-negocio",
  "location": { "repo": "web-app", "file": "src/pages/Certificate/helpers.ts", "lines": "12-18" },
  "evidence": "export const canIssueCertificate = (p: Progress) => p.completedLessons / p.totalLessons > 0.75;",
  "problem": "A regra de elegibilidade ao certificado existe em 2 pontos com condição diferente. (1) web-app/src/pages/Certificate/helpers.ts:12-18 usa `> 0.75`. (2) api-bff/src/certificates/eligibility.service.ts:40-44 usa `>= 0.75`. Com 3 de 4 aulas, o BFF emite e o front esconde o botão. O aluno com exatamente 75% fica sem certificado na UI. Fonte da verdade sugerida: BFF, onde a emissão ocorre. Mudar a regra hoje exige alterar 2 repos.",
  "fix": "O BFF devolve `canIssueCertificate: boolean` no payload de progresso. O front remove a função e lê o campo.\n- export const canIssueCertificate = ...\n+ const { canIssueCertificate } = progress;",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["The Pragmatic Programmer, tip 11: DRY"],
  "introduced_by_diff": true
}
```

### Achado 2: wrong abstraction

```json
{
  "id": "DRY-002",
  "agent": "review-dry",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "god-util",
  "location": { "repo": "web-app", "file": "src/utils/formatPeriod.ts", "lines": "5-38" },
  "evidence": "export function formatPeriod(start: Date, end: Date, short = false, withYear = true, forCertificate = false, fallback?: string)",
  "problem": "formatPeriod tem 3 flags booleanas e 3 callers (Header, CertificateCard, ExportCsv). Cada caller usa uma combinação própria. O diff adiciona `forCertificate` e um ramo novo de 9 linhas. A próxima mudança de formato do certificado afeta os 2 callers que não o usam. Cada flag nova dobra as combinações a testar.",
  "fix": "Inline em cada caller e mantenha o que for comum.\nconst formatShortPeriod = (s: Date, e: Date) => `${fmt(s, 'dd/MM')} a ${fmt(e, 'dd/MM')}`;\nconst formatCertificatePeriod = (s: Date, e: Date) => `${fmt(s, 'dd/MM/yyyy')} a ${fmt(e, 'dd/MM/yyyy')}`;",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["Sandi Metz: duplication is far cheaper than the wrong abstraction"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

Dois services de módulos diferentes (`ExamsService` e `CertificatesService`) montam o mesmo `select: { id: true, name: true, createdAt: true }` de `Course`. O trecho tem 1 linha, as duas queries pertencem a casos de uso distintos, e cada um muda por motivo próprio (a tela de provas ganha campo de nota, o certificado ganha carga horária). Extrair um `COURSE_SELECT` acopla os dois. A regra de três não foi atingida. Não reporte.
