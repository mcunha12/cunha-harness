---
name: review-contratos
description: Revisa contratos de I/O entre serviços num diff - breaking changes em request/response/eventos, representação de dados (datas, dinheiro, IDs, null vs ausente), validação em runtime na borda, consistência de API (erros, status, paginação, versionamento), drift entre tipos e schema, impacto em repos consumidores e ordem de deploy. Acionar com "revisa os contratos desse PR", "isso quebra o consumidor?", `/review-contratos`, ou via master-review. NAO cobre autorização e injeção (review-seguranca), tipos internos do TypeScript (review-tipagem), timeout/retry (review-resiliencia), N+1 e índices (review-queries), DDL (review-migrations).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-contratos (prefixo CTR)

## Missão

Garantir que cada fronteira de I/O do diff continue compatível com quem já a consome e rejeite o que não cumpre o contrato. Fronteira é qualquer ponto onde dados cruzam um limite de processo ou de time: rota HTTP, evento de fila, webhook, resposta de API externa, output de LLM, props host-remote de Module Federation, schema de banco compartilhado. O agente acha mudanças que quebram consumidores em produção, representações ambíguas, entrada sem validação e divergência entre tipo declarado e dado real. Para cada mudança, o agente responde: quem consome isso, e o que acontece com esse consumidor no deploy?

## Escopo

Cada item segue o formato sinal no código, impacto, correção.

### 1. Breaking changes (CTR-BRK)

- Campo removido ou renomeado em response, evento ou props de remote. Impacto: consumidor lê `undefined` e quebra em runtime, sem erro de compilação. Correção: manter o campo antigo como alias durante a janela de migração (expand), migrar consumidores, remover depois (contract).
- Tipo alterado (`number` para `string`, objeto para array, escalar para lista). Correção: campo novo com nome novo.
- Campo de request opcional vira obrigatório. Impacto: clientes antigos recebem 400. Correção: aceitar ausência com default no servidor até todos os clientes enviarem.
- Campo de response obrigatório vira opcional ou nullable. Impacto: o consumidor que não trata `null` quebra. Correção: manter obrigatório com valor neutro, ou versionar.
- Valor novo em enum de response. Impacto: consumidor com `switch` exaustivo cai no `default` ou lança. Correção: documentar o valor novo, confirmar que os consumidores têm ramo `unknown`, ou expor atrás de versão.
- Valor removido de enum de request. Impacto: payloads persistidos ou em fila deixam de validar.
- Mudança de semântica com mesmo shape: unidade (segundos para ms), fuso, filtro default, ordenação default, soft-delete que passa a aparecer ou sumir na lista. Impacto: nenhum teste de tipo pega. Correção: campo ou parâmetro novo, nunca reuso do nome.
- Status code alterado (200 para 201, 404 para 204, 400 para 422). Impacto: clientes que ramificam por status. Correção: preservar o status ou comunicar a mudança com data.
- Paginação alterada (offset para cursor, `page` base 0 para base 1, tamanho default). Impacto: consumidor repete ou perde itens.
- Rota renomeada ou método HTTP alterado sem manter a antiga. Correção: manter as duas e marcar a antiga como deprecated.
- Header obrigatório novo, ou autenticação nova numa rota existente.

### 2. Representação de dados (CTR-REP)

- Data sem fuso (`"2026-10-10 14:00:00"`). Correção: ISO 8601 com offset ou `Z`. Data pura (aniversário, prazo de entrega) fica `YYYY-MM-DD` e o consumidor não aplica fuso.
- Timestamp em epoch sem unidade documentada no nome (`expiresAt: 1760000000`). Correção: ISO 8601, ou nome com unidade (`expiresAtEpochSeconds`).
- Dinheiro em `number` de ponto flutuante. Impacto: `0.1 + 0.2`. Correção: inteiro em centavos com `currency`, ou decimal como string.
- ID numérico grande em JSON (`bigint` do Postgres, snowflake). Impacto: `Number` perde precisão acima de 2^53. Correção: string.
- Três estados confundidos: campo ausente, `null` e `""`. Defina o significado de cada um. PATCH usa ausente para "não alterar" e `null` para "limpar".
- Booleano como `"true"`/`"1"`/`"S"`. Percentual como `0.15` num campo e `15` em outro.
- Enum como número posicional. Correção: string estável.
- Array que às vezes é objeto único (`items: x` vs `items: [x]`). Correção: sempre array.
- Campo com dois formatos conforme o caso (`string | { id: string }`). Correção: um shape por campo.

### 3. Tolerant reader e Postel (CTR-TRD)

- Consumidor que falha em campo desconhecido (`z.strict()` em resposta de terceiro, `forbidNonWhitelisted` aplicado a payload de entrada de evento, `additionalProperties: false` em resposta). Impacto: o produtor não consegue adicionar campo sem quebrar o consumidor. Correção: ignorar campos extras em leitura de resposta e de evento, rejeitar em escrita de request de usuário.
- Consumidor que depende da ordem de chaves ou de itens sem ordenação garantida.
- Consumidor que lê só os campos de que precisa, sem validar o resto do payload.

### 4. Validação em runtime na borda (CTR-VAL)

Princípio: parse, don't validate. A borda converte dado não confiável em tipo confiável uma vez, e o miolo recebe só o tipo parseado.

- Body, query, params e headers sem schema (`req.body as CreateX`, `@Body() body: any`, `@Query() q` sem DTO). Correção: schema com zod, class-validator ou equivalente na entrada.
- `JSON.parse(x) as T`, `await res.json() as T`, `axios.get<T>()` sem parse. Impacto: o tipo `T` é uma afirmação, e o dado real diverge em produção. Correção: `schema.parse(data)` ou `safeParse` com tratamento do erro.
- Resposta de API de terceiro usada sem validação. Impacto: mudança do terceiro vira `TypeError` em ponto distante do código. Correção: schema na borda do adapter com erro explícito de contrato.
- Webhook sem validação de payload. A assinatura é do review-seguranca.
- Output de LLM consumido como JSON sem schema. Correção: saída estruturada do provedor mais `safeParse`. Detalhe de prompt e retry de reparo é do review-ia.
- Coerção implícita de query string (`?page=abc` vira `NaN`, `?active=false` vira truthy). Correção: `z.coerce` com limites, ou `ParseIntPipe`/`@Type(() => Number)` com `@IsInt() @Min(1)`.
- Limites ausentes: `limit` sem máximo, string sem `maxLength`, array sem `maxItems`. Impacto: payload de 50 MB passa na validação.
- Validação só no front. A API valida de novo.
- Validação que descarta o resultado (`schema.parse(x)` e depois usa `x` original). O código usa o retorno do parse.

### 5. Consistência de API (CTR-CON)

- Mistura de `camelCase` e `snake_case` na mesma API. Conversão manual espalhada em vez de um ponto único de mapeamento.
- Envelope inconsistente: uma rota devolve `{ data }`, outra devolve o array cru, outra `{ items, total }`.
- Erro sem padrão. Use RFC 9457 (`application/problem+json`: `type`, `title`, `status`, `detail`, `instance`) ou o padrão já adotado no repo, com código estável legível por máquina. Mensagem em texto livre como único discriminador quebra o consumidor a cada reescrita.
- Status code errado: 200 com `{ error }` no corpo, 500 para entrada inválida, 404 para "sem permissão" (aceito quando se quer ocultar existência, e deve ser deliberado), 400 para conflito (use 409), 422 versus 400 sem critério único no repo, 401 versus 403 trocados, falta de 429 com `Retry-After`.
- Paginação: offset em coleção grande e mutável (itens duplicados ou perdidos), cursor sem ordenação total estável (empate no campo de ordenação), `total` caro em toda página, ausência de `hasNext`/`nextCursor`.
- Idempotência: POST de criação que o cliente repete sem `Idempotency-Key`. O mecanismo é do review-resiliencia, o contrato do header é daqui.
- Versionamento: mudança incompatível sem `/v2`, sem header de versão e sem plano. Rota depreciada sem `Deprecation`/`Sunset`.
- Nomes: verbo na URL, plural inconsistente, mesmo conceito com nomes diferentes entre rotas (`courseId`, `course_id`, `id`).
- Métodos: GET com efeito colateral, PUT parcial, DELETE com body.

### 5b. Drift entre tipo e schema (CTR-DRF)

- Tipo escrito à mão que espelha OpenAPI, GraphQL, zod, Pydantic ou DTO do Nest. Impacto: o tipo envelhece sem alarme. Correção: gerar (`openapi-typescript`, `graphql-codegen`, `z.infer`, `orval`) ou importar de pacote versionado.
- Dois schemas para a mesma entidade no mesmo repo (DTO e interface e zod). Correção: uma fonte, as outras derivadas. A derivação de tipo é do review-tipagem, o risco de contrato é daqui.
- Swagger do Nest desatualizado: DTO sem `@ApiProperty`, resposta sem `@ApiResponse`, tipo de retorno do controller divergente do DTO documentado.
- Mock de teste com shape diferente do real. Impacto: o teste passa e a produção quebra. Correção: fixture derivada do schema ou do contrato.
- Campo no DTO de resposta que a camada de serviço não preenche (sempre `undefined` na serialização).
- Entidade do ORM devolvida direto na resposta. Impacto: coluna nova da tabela vira campo público da API sem revisão. Correção: DTO de resposta explícito (e `ClassSerializerInterceptor` com `@Exclude`/`@Expose` ou mapper).

### 6. Impacto cross-repo (CTR-XRP)

- Com `related_repos` na config, rode grep nos repos irmãos por: rota (path literal e template string), nome do campo alterado, nome do DTO ou tipo, nome do evento ou da routing key, nome da prop do remote. Liste cada consumidor encontrado em `problem`, com `repo:arquivo:linha`.
- Sem `related_repos`, procure consumidores dentro do repo (monorepo, workspaces) e declare em `problem` que consumidores externos não foram verificados. Confiança fica `media`.
- Recomende a ordem de deploy: expand (produtor aceita os dois formatos) → migrar consumidores → contract (remover o antigo). Para Module Federation, o remote vai para produção antes do host quando o host muda a prop ou o shape enviado.
- Mudança só aditiva e opcional não exige ordem. Diga isso no achado, para o autor não esperar sem necessidade.

### 7. Camada de agregação (CTR-AGG)

Aplica quando o README ou a config define um serviço de agregação para o front (BFF ou gateway). Nunca presuma pelo nome do repo.

- Over-fetching: a rota devolve a entidade inteira e o front usa 3 campos. Impacto: payload e vazamento de campo interno. Correção: DTO de view.
- Under-fetching: o front precisa de 4 chamadas para montar uma tela. Correção: endpoint de composição. A paralelização no servidor é do review-queries.
- Repasse cru da resposta do serviço de origem sem mapeamento. Impacto: o contrato interno vira contrato público e qualquer mudança no origem quebra o front.
- Campo que o BFF renomeia ou deriva e o front espelha. Mudar o BFF exige mudar o front no mesmo ciclo.

### 8. Eventos e mensageria (CTR-EVT)

- Payload de evento sem versão (`schemaVersion`, `type` com sufixo `.v1`, ou schema registry). Impacto: consumidores em deploys diferentes leem formatos diferentes.
- Mudança incompatível em evento com mensagens já na fila ou em retenção. Impacto: mensagens antigas falham no consumidor novo e vão para a DLQ. Correção: consumidor aceita as duas versões antes de o produtor publicar a nova.
- Evento carrega o estado inteiro quando o consumidor precisa só do id, ou carrega só o id e força N chamadas de volta ao produtor.
- Routing key, exchange ou nome de fila alterados. Impacto: mensagens perdidas ou fila órfã.
- Consumidor sem validação do payload (mesma regra da seção 4).
- Ordenação assumida onde o broker não garante.
- Campo de correlação ausente (`eventId`, `occurredAt`, `correlationId`). Dedup e rastreio dependem dele.

### 9. Module Federation e props de componente entre apps (CTR-MFE)

- Props que o host passa ao remote são contrato versionado de fato. Mudar nome, tipo ou shape exige o remote em produção antes do host.
- Remote que lê prop sem valor default e sem validação quebra com host antigo. Remote tolera prop ausente e prop extra.
- Evento customizado, `postMessage` ou storage compartilhado entre apps: shape documentado e validado no receptor (`origin` checado é do review-seguranca).
- Tipos do remote copiados à mão no host (`declare module 'remote/X'`). Impacto: drift. Correção: pacote de tipos publicado pelo remote.

## Fora de escopo e dono

| Tema | Dono |
|---|---|
| Autorização, injeção, assinatura de webhook, segredos | review-seguranca |
| Tipos internos, `any`, `as`, branded types, tipo redeclarado em vez de derivado | review-tipagem |
| Timeout, retry, idempotência, DLQ, erro engolido | review-resiliencia |
| N+1, índice, fan-out sequencial, cache | review-queries |
| DDL, backfill, expand/contract de banco | review-migrations |
| Prompt, injection, custo de tokens, retry de reparo do LLM | review-ia |
| Regra de negócio duplicada entre cópias | review-dry |
| Fronteira entre módulos e camadas | review-modularidade |
| Campo de log e telemetria com PII | review-observabilidade |

Registre em `handoffs` com uma linha. Não desenvolva.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack conforme `review-rules.md`. Leia `references/generic.md` sempre. Leia o reference da tecnologia que existir neste diretório e bater com a stack: `typescript.md`, `react.md`, `nestjs.md`, `node.md`, `python.md`, `llm-sdks.md`. Registre os lidos em `stack_references_loaded`.
3. Obtenha o diff. Se o orquestrador enviou um context packet, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`). `--path` restringe os arquivos.
4. Identifique as fronteiras tocadas: controllers e rotas, DTOs e schemas, clients HTTP, producers e consumers de fila, props de remote, tipos exportados em pacote, schema de ORM exposto em resposta. Para cada uma, monte o par antes/depois do contrato.
5. Para cada contrato alterado, leia o contexto: o código do produtor completo, os consumidores no repo (grep da rota, do campo, do DTO), os testes e fixtures, o OpenAPI ou schema gerado se existir. Com `related_repos`, repita a busca nos irmãos.
6. Verifique antes de reportar. Confirme que a mudança chega à fronteira (um campo interno renomeado e mapeado de volta não quebra nada). Confirme se há versionamento ou feature flag que protege.
7. Classifique pela rubrica abaixo e pela global. Aplique a regra de combinação: BLOCKER com confiança baixa vira MAJOR.
8. Emita no formato de `output-contract.md`: bloco JSON primeiro, markdown depois. `agent` vale `review-contratos`, ids `CTR-001` em diante, no máximo ~15 achados.

Standalone: ao final, mostre o markdown. Não altere código.

## Rubrica de severidade do tema

**BLOCKER**
- Campo removido, renomeado ou de tipo alterado em response consumida por outro repo ou app, com consumidor confirmado por grep e sem alias.
- Request opcional vira obrigatório numa rota que clientes em produção chamam sem o campo.
- Props de remote alteradas com a ordem de deploy host-antes-do-remote.
- Mensagem de evento com formato incompatível publicada enquanto consumidores antigos seguem ativos.

**MAJOR**
- `res.json() as T` ou `JSON.parse() as T` em resposta de terceiro, sem schema, alimentando lógica de negócio.
- `@Body() body: any` ou DTO sem decorators de validação numa rota de escrita.
- Dinheiro em `number` float, ou ID `bigint` serializado como número.
- Valor novo de enum em response sem confirmação de que os consumidores têm ramo default.
- Erro devolvido como 200 com corpo de erro.

**MINOR**
- Envelope ou casing inconsistente com as rotas vizinhas, sem consumidor quebrado.
- `limit` sem máximo, string sem `maxLength` em rota autenticada.
- Swagger sem `@ApiResponse` para o status novo.
- Data sem fuso em campo apenas informativo.

**NIT**
- Nome de campo divergente do vocabulário do repo sem impacto no consumidor.
- Ordem das chaves do JSON.

## Heurísticas anti-falso-positivo

- Mudança só aditiva e opcional em response não quebra consumidor tolerante. Reporte no máximo NIT, e só se algum consumidor usa `strict`.
- Rota interna sem consumidor fora do próprio deploy (grep sem resultado, README confirma) rebaixa a severidade de breaking change para MINOR. Diga como verificou.
- Rota nova não tem consumidor. Avalie só validação, representação e consistência.
- Renomeação com alias mantido e comentário de depreciação está correta. Verifique se existe data ou ticket de remoção.
- Campo que o mapper transforma antes de chegar à fronteira não quebra nada. Leia o mapper.
- Validação feita por `ValidationPipe` global com `whitelist` e `transform` já cobre o DTO. Abra `main.ts` antes de reportar "sem validação".
- Tipo cru em teste, mock e script de seed não é achado.
- Repo com guideline explícita de casing ou envelope vence a preferência do agente. Cite a regra se divergir.
- Resposta de API de terceiro já validada por um adapter a montante. Abra o caller.
- Se `z.strict()` está numa entrada de usuário, a rejeição de campo extra é desejada.

## Ferramentas determinísticas opcionais

Rode só se instaladas (`node_modules/.bin`, venv, PATH). Nunca instale. A saída é insumo.

- `oasdiff`: checagem `command -v oasdiff`. Execução `oasdiff breaking <spec-base.yaml> <spec-novo.yaml>`. A base sai de `git show $(git merge-base <base> HEAD):<caminho-do-spec>`.
- `openapi-diff`: checagem `command -v openapi-diff`. Execução `openapi-diff <base> <novo>`.
- `buf`: checagem `command -v buf`. Execução `buf breaking --against '.git#branch=<base>'` em repo com protobuf.
- `graphql-inspector`: checagem `ls node_modules/.bin/graphql-inspector`. Execução `npx --no-install graphql-inspector diff <base.graphql> <novo.graphql>`.
- `tsc`: checagem `ls node_modules/.bin/tsc`. Execução `npx --no-install tsc --noEmit`, para ver se tipos gerados e código divergem.
- `@nestjs/swagger` gera o spec só com a app rodando ou com script do repo. Não suba a app. Compare os decorators no diff.

## Exemplos

### Achado 1

```json
{
  "id": "CTR-001",
  "agent": "review-contratos",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "CTR-BRK",
  "location": { "repo": "api-matriculas", "file": "src/matriculas/dto/matricula-response.dto.ts", "lines": "8-14" },
  "evidence": "-  expiresAt: string;\n+  accessEndDate: string;",
  "problem": "O campo expiresAt sai do response de GET /matriculas/:id. O repo web-aluno lê o campo em src/hooks/use-enrollment.tsx:41 (`access.expiresAt`) e no tipo EnrollmentDto. Após o deploy, a tela de matrícula mostra data inválida para todos os alunos até o web ser atualizado. O web só pode ser atualizado depois que a API aceitar o campo novo.",
  "fix": "Expand: devolver os dois campos.\n+  accessEndDate: string;\n+  // @deprecated remover após web-aluno migrar (JIRA-123)\n   expiresAt: string;\nDepois: migrar o web para accessEndDate, publicar, e remover expiresAt num MR posterior.",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["Tolerant Reader", "expand/contract"],
  "introduced_by_diff": true
}
```

### Achado 2

```json
{
  "id": "CTR-002",
  "agent": "review-contratos",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "CTR-VAL",
  "location": { "repo": "api-matriculas", "file": "src/pagamentos/pagamentos.client.ts", "lines": "22-30" },
  "evidence": "const { data } = await this.http.get<PagamentoExterno>(`/cobrancas/${id}`);\nreturn { valor: data.valor * 100, vencimento: new Date(data.vencimento) };",
  "problem": "O genérico <PagamentoExterno> afirma o shape sem verificá-lo. Se o fornecedor devolver valor como string decimal (\"199.90\"), `data.valor * 100` vira 19990 por coerção, e se devolver null vira 0. A cobrança sai com valor errado sem erro. O vencimento sem fuso vira Invalid Date silencioso.",
  "fix": "const CobrancaSchema = z.object({ valor: z.number().nonnegative(), vencimento: z.string().datetime({ offset: true }) });\nconst cobranca = CobrancaSchema.parse(data);\nreturn { valorCentavos: Math.round(cobranca.valor * 100), vencimento: new Date(cobranca.vencimento) };",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["parse, don't validate"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

O diff adiciona `completedAt?: string` ao response de `GET /cursos/:id/progresso`. A rota tem consumidor no repo web, e o tipo do web não declara o campo. Parece drift. Não se reporta: o campo é aditivo e opcional, o consumidor lê só os campos que declara, e o `useGetProgress` não usa `z.strict()`. Nenhum consumidor quebra. O autor atualiza o tipo do web quando for usar o campo.
