# Contratos em Node HTTP (Express, Fastify, Koa)

## Express

- Sinal: `req.body`, `req.query`, `req.params` lidos direto, sem schema. Impacto: `req.query.id` é `string | string[] | ParsedQs`, e `?id=1&id=2` vira array. Código que chama `.toLowerCase()` quebra com 500. Correção: `Schema.parse(req.query)`.
- Sinal: `express.json()` sem `limit` explícito. O default é 100 kb. Rota que recebe payload maior falha com 413 sem aviso. Rota pública sem teto explícito aceita o default. Verifique se o limite combina com o contrato.
- Sinal: `app.use(express.json())` ausente ou depois da rota. `req.body` fica `undefined`.
- Sinal: `res.json(row)` com linha do banco (`pg`, `knex`). Impacto: colunas novas vazam, `bigint` vem como string e `numeric` vem como string, `timestamp` vira `Date`. Correção: mapper para DTO, com conversão de tipo explícita.
- Sinal: `res.send(obj)` e `res.json(obj)` misturados, status 200 implícito em criação. Verifique 201 quando o repo usa.
- Sinal: handler async sem `next(err)` ou wrapper (Express 4 não captura rejeição). Impacto: a requisição fica pendurada. O tema de erro é do review-resiliencia. O contrato é que o erro tenha formato padrão: um `errorHandler` final (`(err, req, res, next)`) que serializa no formato do repo.
- Sinal: `cors` com origem ou header novo sem atualizar o consumidor. A política é do review-seguranca.

## Fastify

- Fastify valida e serializa por JSON Schema (`schema: { body, querystring, params, headers, response }`). Sinal: rota sem `schema.body` onde o repo usa schemas. Sinal: `schema.response` ausente. Impacto: sem schema de response, o `fast-json-stringify` não filtra campo, e a entidade inteira sai.
- Sinal: `additionalProperties` omitido em `body`. O default do Ajv do Fastify remove campo extra (`removeAdditional: true`) e coage tipos (`coerceTypes: 'array'`). Dado de entrada muda sem aviso. Verifique se o contrato tolera.
- Com `fastify-type-provider-zod` ou `@sinclair/typebox`, o schema é a fonte do tipo. Sinal: `request.body as X` ao lado de schema declarado.

## Koa e outros

- Sinal: `ctx.request.body` sem parser com limite e sem schema. Mesma regra.

## Respostas de erro e status

- Sinal: `res.status(200).json({ success: false, error })`. Impacto: clientes e monitores confiam no status. Correção: status correto e corpo de erro padronizado.
- Sinal: `res.status(500).json({ message: err.message })`. Vazamento é do review-seguranca. O contrato quer `code` estável.
- Sinal: rota que devolve `404` para "sem permissão" e `403` em outras rotas do mesmo recurso. Escolha uma política por recurso e documente.

## Streams e download

- Sinal: mudança de `Content-Type` ou `Content-Disposition` em rota de download. Impacto: o cliente que lê `blob` ou `text` quebra.
- Sinal: resposta que passa de JSON para NDJSON ou SSE sem rota nova. Impacto: `res.json()` do cliente falha.

## Clients HTTP (axios, fetch, undici, got)

- Sinal: `await fetch(url)` seguido de `res.json()` sem checar `res.ok`. Impacto: corpo de erro HTML (502 do proxy) vira `SyntaxError` sem contexto. Correção: checar `ok`, ler `content-type`, parse com schema.
- Sinal: `axios.get<T>()` com `T` assumido. Mesma regra de validação da borda.
- Sinal: `fetch` com `body: JSON.stringify(x)` sem `Content-Type: application/json`. O servidor recebe `text/plain` e `req.body` vem vazio.
- Sinal: query string montada por concatenação (`?q=${q}`). Impacto: `&`, `#` e acentos quebram o contrato do parâmetro. Correção: `URLSearchParams` ou `params` do axios. Injeção é do review-seguranca.
