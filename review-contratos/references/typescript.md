# Contratos em TypeScript

## zod na borda

- Sinal: `const body = req.body as CreateInput`, `const data: Foo = await res.json()`, `JSON.parse(raw) as Foo`. Impacto: o tipo é uma afirmação, o runtime pode divergir. Correção: `const body = CreateInputSchema.parse(req.body)`; use `safeParse` quando o erro vira resposta 400 ou erro de adapter.
- Sinal: `schema.parse(x)` com retorno descartado e uso de `x` depois. Impacto: campos transformados, defaults e `coerce` não chegam ao código. Correção: usar o valor retornado.
- Sinal: `z.any()`, `z.unknown()` num campo de payload que o código depois acessa, `z.object({}).passthrough()` em entrada de usuário. Impacto: campo arbitrário chega ao banco ou ao serviço seguinte (mass assignment é do review-seguranca, o schema frouxo é daqui). Correção: schema explícito.
- Sinal: `z.string()` para data, uuid, email, url. Correção: `z.string().datetime({ offset: true })`, `.uuid()`, `.email()`, `.url()`.
- Sinal: query string sem coerção (`z.number()` falha sempre, porque a query chega como string) ou com coerção ingênua (`z.coerce.boolean()` transforma `"false"` em `true`). Correção: `z.coerce.number().int().min(1).max(100)` e, para booleano, `z.enum(["true","false"]).transform(v => v === "true")`.
- Sinal: schema de resposta de terceiro com `.strict()`. Impacto: campo novo do fornecedor derruba a integração. Correção: `.strip()` (default) ou `.passthrough()` quando o resto é repassado.
- Sinal: `z.union` de objetos sem discriminador. Impacto: erro de validação ilegível e custo de tentar cada ramo. Correção: `z.discriminatedUnion("type", [...])`.
- Sinal: enum de response validado com `z.enum([...])` fechado no consumidor. Impacto: valor novo do produtor derruba o parse inteiro. Correção: `z.enum([...]).catch("UNKNOWN")` ou `z.string()` com ramo `unknown` na lógica, quando o consumidor é tolerante por desenho.
- Sinal: `z.number()` para dinheiro. Correção: `z.number().int()` em centavos ou `z.string().regex(/^\d+\.\d{2}$/)`.
- Sinal: `z.date()` em schema de payload JSON. Impacto: JSON não tem `Date`, o parse sempre falha. Correção: `z.coerce.date()` ou string `datetime`.
- `z.infer<typeof Schema>` é a fonte do tipo. Interface paralela à mão é drift (derivação é do review-tipagem, risco de contrato é daqui).

## Tipos gerados

- Sinal: arquivo `*.generated.ts`, `openapi.d.ts` ou `schema.ts` editado à mão no diff. Impacto: a próxima geração sobrescreve a edição. Correção: alterar a fonte (spec, schema) e regenerar.
- Sinal: o diff altera o spec ou o DTO e não altera o artefato gerado commitado. Impacto: cliente com tipo velho. Correção: regenerar e commitar, ou falhar o CI no diff do gerado.
- Sinal: tipo gerado reexportado com `Partial<>` ou `any` para "fazer compilar". Impacto: esconde exatamente a divergência que a geração existe para expor.

## Pacotes de tipos entre repos

- Sinal: o diff altera interface exportada de pacote publicado (`exports`, `types` no `package.json`). Impacto: semver. Remover ou estreitar é major. Correção: bump de versão compatível com a mudança e nota de release.
- Sinal: versão do pacote com `^` e a mudança de tipo é incompatível numa minor. Impacto: consumidores quebram no próximo install.
- Sinal: tipos copiados entre repos com comentário "copiado de X". Correção: pacote versionado.

## Narrowing de union vinda da rede

- Sinal: `switch (resp.status)` sem `default` e sem ramo para valor desconhecido, em dado de rede. Impacto: valor novo do produtor cai em nenhum ramo e a UI fica vazia. Correção: `default` que registra e usa fallback.
- Sinal: `assertNever` no `default` de enum que vem da rede. Impacto: lança em produção quando o produtor adiciona um valor. A exaustividade com `never` fica para enums internos. Para enums de rede, o `default` degrada.

## Serialização

- Sinal: `Date`, `Map`, `Set`, `bigint`, `undefined` dentro de objeto retornado para JSON. Impacto: `Date` vira string ISO (aceitável, mas o tipo TS continua `Date`), `Map` e `Set` viram `{}`, `bigint` lança `TypeError`, `undefined` some. Correção: DTO com tipos serializáveis e conversão explícita.
- Sinal: `JSON.stringify(entity)` com getter, relação circular ou coluna sensível. Correção: mapper para DTO.
- Sinal: `JSON.stringify` de `Decimal` do Prisma. Impacto: vira string. O contrato precisa declarar string decimal, não número.
