# Contratos em NestJS

## DTOs e ValidationPipe

- Abra `main.ts` (ou `app.module.ts`) antes de reportar. Procure `app.useGlobalPipes(new ValidationPipe({...}))` ou `APP_PIPE`. Sem pipe global, só `@UsePipes` ou `@Body(new ValidationPipe())` valida.
- Opções que importam: `whitelist: true` (remove campo sem decorator), `forbidNonWhitelisted: true` (rejeita campo extra), `transform: true` (instancia a classe e converte tipos), `transformOptions: { enableImplicitConversion }`. Sem `transform: true`, `@Body() dto: CreateDto` entrega objeto plano e `@Type()` não age.
- Sinal: `@Body() body: any` ou `@Body() body: Record<string, unknown>`. Impacto: nenhuma validação. Correção: classe DTO com decorators.
- Sinal: `@Body() body: CreateDto` com `CreateDto` como `interface` ou `type`. Impacto: tipos TS somem em runtime, o pipe não tem metadado e passa tudo. Correção: `class`.
- Sinal: propriedade de DTO sem nenhum decorator de `class-validator`. Impacto: com `whitelist: true`, o campo é removido silenciosamente e o handler recebe `undefined`. Sem `whitelist`, o campo passa sem validação. Correção: `@IsString()`, `@IsOptional()` e os demais.
- Sinal: `@IsOptional()` ausente em campo `?:`. Impacto: o campo vira obrigatório em runtime e o tipo TS diz opcional. Divergência de contrato. Correção: alinhar decorator e tipo.
- Sinal: `@IsString()` em campo `number`. `@IsNumber()` em query param sem `@Type(() => Number)`. Impacto: query chega como string e a validação falha sempre, ou a coerção implícita faz `"abc"` virar `NaN` que passa em `@IsNumber()` (use `@IsNumber({ allowNaN: false })`).
- Sinal: `@IsBoolean()` com `@Type(() => Boolean)` em query. Impacto: `"false"` vira `true`. Correção: `@Transform(({ value }) => value === 'true' || value === true)`.
- Sinal: array ou objeto aninhado sem `@ValidateNested()` e `@Type(() => Child)`. Impacto: o conteúdo não é validado.
- Sinal: `@IsArray()` sem `@ArrayMaxSize`, `@IsString()` sem `@MaxLength`, paginação sem `@Max`. Impacto: payload sem teto.
- Sinal: `@IsEnum(Status)` onde o enum TS é numérico. Impacto: aceita número e nome reverso. Correção: enum de strings.
- Sinal: DTO de update escrito à mão. Correção: `PartialType(CreateDto)`, `PickType`, `OmitType` (de `@nestjs/mapped-types` ou `@nestjs/swagger`, para manter o Swagger coerente).
- Divergência DTO e tipo de domínio (ex.: `interface Matricula` com `status: 'ATIVA' | 'ENCERRADA'` e DTO com `@IsString()`): o DTO aceita valor fora do domínio. Correção: `@IsIn([...])` ou `@IsEnum`. A derivação do tipo é do review-tipagem.

## Resposta

- Sinal: controller devolve entidade do Prisma ou do TypeORM. Impacto: coluna nova vira campo público, coluna sensível (hash, token, flag interna) vaza (a exposição é do review-seguranca, o contrato é daqui). Correção: DTO de resposta e mapper, ou `ClassSerializerInterceptor` com `@Exclude()`/`@Expose()` e `@SerializeOptions({ strategy: 'excludeAll' })`.
- Sinal: `@Res()` injetado sem necessidade. Impacto: desliga interceptors, serialização e filtros de exceção. Correção: devolver o valor e usar `@HttpCode`, `@Header`.
- Sinal: tipo de retorno do método diferente do DTO documentado em `@ApiResponse({ type })`. Impacto: o Swagger mente e o cliente gerado erra.
- Sinal: `@HttpCode` ausente em POST que não cria (Nest devolve 201 por padrão). Impacto: status inesperado para ações como "recalcular". Verifique a intenção.
- Sinal: `Date` em retorno sem decisão de formato. Nest serializa com `toISOString()`, em UTC. Correto para instante, errado para data de calendário (`@db.Date`), que vira `2026-10-10T00:00:00.000Z` e muda de dia no fuso do cliente. Correção: string `YYYY-MM-DD` no DTO.
- Sinal: `BigInt` ou `Prisma.Decimal` em resposta. Impacto: `BigInt` lança no `JSON.stringify`, `Decimal` vira string. Correção: conversão explícita no mapper e tipo documentado.

## Swagger

- `@ApiProperty`/`@ApiPropertyOptional` em todo campo de DTO quando o repo usa `@nestjs/swagger`. Sem o plugin do CLI (`nest-cli.json` com `@nestjs/swagger` em `plugins`), os decorators são obrigatórios. Com o plugin, as propriedades são inferidas e o decorator só acrescenta descrição e exemplo.
- Sinal: rota nova sem `@ApiOperation`, `@ApiResponse` por status relevante (inclusive 400, 404, 409), `@ApiBearerAuth` quando autenticada. Impacto: cliente gerado sem os tipos de erro.
- Sinal: `@ApiProperty({ type: Object })` ou `any`. Impacto: schema vazio no spec.
- Enum: `@ApiProperty({ enum: Status, enumName: 'Status' })` para o spec reaproveitar o schema.

## Erros

- Padrão de erro do repo: procure `ExceptionFilter` global (`APP_FILTER`, `app.useGlobalFilters`). Sinal: `throw new Error('...')` em handler. Impacto: vira 500 sem corpo útil. Correção: `HttpException` específica (`BadRequestException`, `ConflictException`, `NotFoundException`) ou exceção de domínio mapeada pelo filter.
- Sinal: mensagem de erro em texto livre usada pelo cliente para ramificar. Correção: campo `code` estável no corpo.
- Sinal: `new BadRequestException(err.message)` com mensagem interna (nome de tabela, stack). Vazamento é do review-seguranca.
- Sinal: erro de validação com formato diferente do filter global (ValidationPipe devolve `{ statusCode, message: string[], error }`). Verifique se o front trata `message` como array.

## Versionamento e rotas

- `app.enableVersioning({ type: VersioningType.URI })` e `@Version('2')`/`@Controller({ version: '2' })`. Sinal: mudança incompatível em controller sem versão nova. Correção: controller v2 que coexiste com o v1 e reutiliza o service.
- Sinal: `@Controller('matriculas')` renomeado no diff. Impacto: a rota antiga some. Correção: manter as duas até migrar os consumidores.
- Sinal: ordem de rotas no controller (`@Get(':id')` antes de `@Get('resumo')`) captura `resumo` como id. Verifique ao adicionar rota estática.
- Parâmetros: `@Param('id', ParseUUIDPipe)` ou `ParseIntPipe`. Sem pipe, `id` é string livre e chega ao ORM.

## Microservices e filas

- RabbitMQ via `@golevelup/nestjs-rabbitmq`: `@RabbitSubscribe({ exchange, routingKey, queue })` define o contrato. Sinal: alteração de `exchange`, `routingKey`, `queue` ou `queueOptions` (durable, arguments). Impacto: mensagens perdidas, ou `PRECONDITION_FAILED` no boot porque a fila existente tem argumentos diferentes. Correção: fila nova, consumo em paralelo, remoção da antiga depois.
- Sinal: handler com `@RabbitPayload() msg: SomeDto` onde `SomeDto` é interface ou classe sem pipe de validação. Impacto: o Nest não valida payload de mensagem por padrão. Correção: `@RabbitPayload(new ValidationPipe(...))` ou `schema.safeParse` na primeira linha.
- Sinal: publicação com `amqpConnection.publish(exchange, key, payload)` onde `payload` é entidade ORM, sem `type`/`version`/`eventId`. Correção: envelope tipado.
- Sinal: `@MessagePattern`/`@EventPattern` com string literal repetida em produtor e consumidor. Correção: constante compartilhada em pacote.

## HTTP client (axios, HttpService)

- Sinal: `this.http.get<Foo>(url)` e uso direto de `data`. Mesma regra de validação da borda.
- Sinal: `data` de resposta usado sem `status` tratado (`validateStatus: () => true`). Verifique o ramo de erro.
- Sinal: interceptors que convertem casing (`camelcase-keys`) apenas num dos lados. Impacto: campo `courseId` vs `course_id` some.
