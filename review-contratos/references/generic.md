# Contratos: regras agnósticas de stack

Cada item: sinal no código, impacto, correção.

## Matriz de compatibilidade

Classifique cada mudança de schema pela direção do dado. Produtor é quem emite, consumidor é quem lê.

| Mudança | Em response/evento (produtor emite) | Em request (consumidor do servidor envia) |
|---|---|---|
| Campo novo opcional | Compatível | Compatível |
| Campo novo obrigatório | Compatível para leitor tolerante | Quebra clientes antigos |
| Remover campo | Quebra quem lê | Compatível se o servidor ignora |
| Renomear campo | Quebra quem lê | Quebra quem envia |
| Tipo mais largo (`int` para `number`, `string` para `string \| null`) | Quebra quem lê | Compatível |
| Tipo mais estreito | Compatível | Quebra quem envia o valor excluído |
| Enum com valor novo | Quebra leitor com switch fechado | Compatível |
| Enum com valor removido | Compatível | Quebra quem envia o valor |
| Obrigatório vira opcional | Quebra leitor que não trata ausência | Compatível |
| Opcional vira obrigatório | Compatível | Quebra |

Sinal: o diff altera um DTO, schema zod, tipo exportado, `.proto`, `.graphql` ou OpenAPI. Impacto: o resultado da matriz decide a severidade. Correção: aplicar expand/contract.

## Expand / contract

1. Expand: o produtor passa a aceitar e emitir os dois formatos.
2. Migrate: cada consumidor passa a usar o formato novo e deploya.
3. Contract: o produtor remove o formato antigo, depois de confirmar por métrica ou log que ninguém mais usa.

Sinal: remoção e uso do campo novo no mesmo MR. Impacto: janela de deploy em que consumidor e produtor discordam (segundos a horas, em apps com cache de bundle ou app mobile, semanas). Correção: separar em MRs e registrar a ordem no achado.

Para clientes que não controlam a data de atualização (app mobile, bundle em cache de CDN, WebView), o contract só ocorre depois da data de suporte mínimo.

## Ordem de deploy por tipo de mudança

- Mudança aditiva em response: produtor primeiro, sem ordem rígida.
- Campo novo obrigatório em request: servidor aceita ausência (com default) → clientes passam a enviar → servidor passa a exigir.
- Remoção em response: consumidores param de ler → produtor remove.
- Props host para remote (Module Federation): remote em produção primeiro, host depois.
- Evento: consumidor aceita os dois formatos → produtor publica o novo → drena a fila antiga → consumidor remove o formato antigo.
- Cadeia de três serviços: do mais interno ao mais externo para aditivas, na ordem inversa para remoções.

## Representação

- Tempo: instante em ISO 8601 com offset (`2026-10-10T14:00:00-03:00` ou `Z`). Data de calendário em `YYYY-MM-DD`. Duração em ISO 8601 (`PT30M`) ou número com unidade no nome (`durationMs`). `new Date("2026-10-10")` interpreta UTC e `new Date("2026-10-10T00:00:00")` interpreta fuso local: a mesma data cai em dias diferentes.
- Dinheiro: inteiro em menor unidade com `currency` (`{ amountCents: 19990, currency: "BRL" }`), ou string decimal. Nunca float. Arredondamento fica em um ponto só.
- IDs: string opaca. Número só quando o domínio garante menos de 2^53.
- Ausente, null e vazio: ausente significa "não informado", `null` significa "sem valor", `""` raramente significa algo. Escolha uma convenção por API e aplique em todo campo. Em PATCH, ausente não altera e `null` limpa.
- Enum: string estável em `SCREAMING_SNAKE` ou `kebab-case`, um estilo por API. Nunca ordinal.
- Booleano: `true`/`false` JSON. Nunca string.
- Lista vazia é `[]`. Ausência de lista é `null` só se o domínio distinguir os dois.
- Localização: o contrato carrega código (`status: "APPROVED"`) e o cliente traduz. Texto de exibição no response fixa o idioma.
- Número decimal exato (nota, percentual de progresso): defina a escala (`0..1` ou `0..100`) no nome ou na documentação e mantenha em todas as rotas.

## Validação na borda

- Toda entrada vinda de fora do processo passa por schema antes de chegar à regra de negócio: body, query, params, headers, cookies, payload de fila, webhook, resposta de HTTP externo, retorno de LLM, leitura de arquivo, `postMessage`, storage.
- O schema define: tipos, obrigatoriedade, formato (`uuid`, `email`, `datetime`), limites (`min`, `max`, `maxLength`, `maxItems`), enum fechado e campos desconhecidos (rejeitar em entrada de usuário, ignorar em resposta de terceiro).
- A validação devolve um valor novo tipado. O código passa a usar o valor retornado.
- Falha de validação em entrada de cliente devolve 400 ou 422 com lista de campos. Falha em resposta de terceiro vira erro de contrato do adapter (5xx do ponto de vista do cliente, log com o payload mascarado).
- Sinal de ausência: cast direto (`as T`), tipo genérico no client HTTP sem parse, `any` na assinatura do handler, `JSON.parse` sem schema. Impacto: erro em runtime longe da causa. Correção: schema na borda.

## Tolerant reader

- Leia só o que precisa. Ignore campo desconhecido. Aceite valor de enum desconhecido com ramo `unknown` explícito (UI mostra fallback neutro, job registra e segue).
- Não dependa de ordem de chaves, ordem de array sem `orderBy` documentado, nem de presença de campo opcional.
- Quem emite não remove campo sem a janela de depreciação. Quem lê não quebra por campo novo.

## Consistência de API

- Um padrão de casing por API. Converter em um ponto único (interceptor, mapper, serializer), nunca em cada handler.
- Um envelope por API. Exemplo: coleção `{ items, nextCursor }`, item cru ou `{ data }`, o padrão que o repo já usa.
- Erro padronizado. RFC 9457:

```json
{ "type": "https://api.exemplo.com/erros/matricula-encerrada", "title": "Matrícula encerrada", "status": 409, "detail": "A matrícula 123 encerrou em 2026-09-30.", "code": "ENROLLMENT_CLOSED" }
```

  O cliente ramifica por `code` ou `type`, nunca por `detail`.
- Status: 400 sintaxe ou validação, 401 sem autenticação, 403 autenticado sem permissão, 404 inexistente, 409 conflito de estado, 422 regra semântica (use só se o repo já distingue de 400), 429 com `Retry-After`, 5xx falha do servidor. 200 com erro no corpo quebra qualquer cliente que confia no status.
- Paginação: cursor opaco para coleção grande ou mutável, com ordenação total estável (campo de ordenação mais `id` como desempate). Offset serve para coleção pequena e estática. Resposta sempre traz como pedir a próxima página.
- Filtros e ordenação: allowlist de campos. `sort=-createdAt` aceita só campos indexados.
- Idempotência: POST de criação aceita `Idempotency-Key` quando o cliente repete por timeout.
- Versionamento: mudança incompatível entra em versão nova (`/v2`, header ou media type), com `Deprecation` e `Sunset` na antiga (RFC 8594). Nunca remova a antiga sem medir uso.
- Caminhos de cache: `ETag`/`Cache-Control` coerentes com a mutabilidade do recurso. A regra de cache em si é do review-queries.

## Drift entre tipo e schema

- Fonte única por entidade de fronteira. As outras representações derivam dela por geração (`openapi-typescript`, `orval`, `graphql-codegen`, `datamodel-code-generator`) ou por inferência (`z.infer`, `Static<typeof Schema>`).
- Sinal de drift: interface escrita à mão com os mesmos campos de um DTO ou schema, `declare module` com shape manual de remote, fixture JSON copiada, enum duplicado entre repos, constante de rota repetida em client e servidor.
- Impacto: campo adicionado no servidor não aparece no cliente, o compilador não avisa, e o bug aparece em produção.
- Correção: pacote versionado de tipos, ou geração no CI com falha quando o artefato gerado diverge do commitado.
- Teste de contrato (Pact, schema test contra OpenAPI) fecha o ciclo. A decisão de escrever teste é do test-audit. O agente aponta a ausência como handoff.

## Eventos e mensageria

- Envelope mínimo: `eventId` (dedup), `type` com versão, `occurredAt` ISO 8601, `correlationId`, `payload`.
- Schema versionado, publicado num lugar que o consumidor lê (registry, pacote, doc). Mudança incompatível cria tipo novo (`matricula.criada.v2`).
- Mensagens persistidas (fila durável, retenção, event sourcing) obrigam o consumidor novo a ler os formatos antigos para sempre, ou até a retenção expirar.
- Consumidor valida o payload. Mensagem inválida vai para DLQ com motivo. O descarte silencioso é do review-resiliencia.
- Payload não carrega dado sensível desnecessário. A regra de PII é do review-seguranca e do review-observabilidade.
- Evento gordo (estado completo) acopla consumidor ao modelo do produtor. Evento fino (só id) força chamada de volta. Escolha por consumidor conhecido e registre a escolha.

## Webhooks recebidos e enviados

- Recebido: valida o payload com schema, tolera campo extra, responde 2xx rápido e processa assíncrono. A assinatura é do review-seguranca. Dedup e retry são do review-resiliencia.
- Enviado: documenta o schema, versiona, inclui `eventId` e timestamp. Mudança de schema segue expand/contract com os receptores.

## LLM como fronteira

- Output do modelo é entrada não confiável. Contrato: schema JSON passado ao provedor (saída estruturada ou tool use) mais validação local do resultado.
- O contrato do schema (campos, enums, limites) é daqui. Prompt, retry de reparo, refusal e truncamento são do review-ia.

## Cross-repo: procedimento de busca

1. Liste os nomes que mudaram: path da rota, campos, DTO, tipo, evento, routing key, prop de remote.
2. Para cada repo em `related_repos`, busque literais com `grep -rn --include='*.ts' --include='*.tsx' --include='*.py' --include='*.json' '<literal>' <repo>` excluindo `node_modules`, `dist`, `build`.
3. Busque também a forma dinâmica: template string de rota (`/matriculas/${`), chave de objeto (`['accessEndDate']`), desestruturação (`{ expiresAt }`).
4. Reporte `repo:arquivo:linha` de cada consumidor. Consumidor encontrado confirma o impacto e sobe a confiança para `alta`. Nenhum resultado em repo irmão não prova ausência de consumidor fora da lista: diga isso.
5. Proponha a ordem de deploy com os repos nomeados.
