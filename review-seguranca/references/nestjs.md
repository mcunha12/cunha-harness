# Segurança em NestJS

## Guards, escopo e deny por padrão

- **Guard global.** Abra `main.ts` e `app.module.ts`. Procure `APP_GUARD` (JwtAuthGuard, RolesGuard, ThrottlerGuard) e `app.useGlobalGuards`. Com guard global, rota pública precisa de `@Public()` explícito. Rota nova com `@Public()` (ou `@SkipAuth`, `@AllowAnonymous`) é achado: confirme que o payload é público.
- **Sem guard global.** Controller novo sem `@UseGuards(...)` na classe nem no método é rota aberta. Impacto: endpoint sem autenticação. Correção: `@UseGuards(JwtAuthGuard, RolesGuard)` na classe.
- **Ordem de guards.** `@UseGuards(RolesGuard, JwtAuthGuard)` roda Roles antes do JWT: `request.user` é `undefined`. Correção: autenticação primeiro.
- **RolesGuard que retorna `true` sem `@Roles`.** Sinal: `if (!roles) return true`. Aceitável só se o JwtAuthGuard cobre a autenticação. Rota de admin sem `@Roles` fica acessível a qualquer logado.
- **Guard assíncrono sem await.** `canActivate` que devolve Promise sem `await` interno retorna truthy. Confirme `async/await`.
- **Ownership.** O guard de role não cobre ownership. Todo service que recebe id do cliente aplica `where: { id, ownerId: user.id }` ou chama `assertOwns(user, recurso)`. Procure `findOne(id)`/`findUnique({ where: { id } })` direto do `@Param`.
- **`@Req() req` e `req.body`.** Pular o DTO elimina a validação. Correção: `@Body() dto: CreateXDto`.

## Validação e mass assignment

- `ValidationPipe` global com `whitelist: true`, `forbidNonWhitelisted: true`, `transform: true`. Sem `whitelist`, propriedades extras chegam ao service e a `repo.update(id, dto)` (mass assignment). Ausência de `whitelist` no `main.ts` ao tocar DTO é MAJOR.
- DTO sem decorator em campo (`name!: string` sem `@IsString()`) é ignorado pelo whitelist (campo descartado) ou aceito sem validação sem whitelist. Cheque todos os campos.
- `@IsOptional()` sem tipo, `@IsObject()` sem `@ValidateNested() @Type(() => X)`: objeto aninhado passa sem validação.
- Arrays sem `@ArrayMaxSize`, strings sem `@MaxLength`, números sem `@Min/@Max`. Impacto: DoS por payload e paginação sem teto.
- `@Param('id') id: string` sem `ParseUUIDPipe`/`ParseIntPipe`: input livre vai para a query. Com Prisma o risco é erro 500 e enumeração. Com raw SQL é injeção.
- DTO de update derivado com `PartialType(CreateDto)` herda campos privilegiados (`role`, `tenantId`). Use `PickType`/`OmitType` ou DTO próprio.
- Body parser: `bodyParser: true` default aceita 100 KB. Alterar `limit` para valor alto sem motivo é MINOR. Upload via `FileInterceptor` sem `limits: { fileSize }` e `fileFilter`: MAJOR.

## Serialização e exposição

- Controller devolvendo entidade/Prisma model inteiro. Correção: DTO de resposta, `@Exclude()` com `ClassSerializerInterceptor` global, ou `select` explícito.
- `@Exclude()` sem `ClassSerializerInterceptor` não faz nada. Confirme o interceptor.
- Filtro de exceção que devolve `exception.stack` ou `message` do ORM/axios ao cliente (`AllExceptionsFilter`). Correção: mensagem genérica, log interno com correlation id.
- Swagger (`SwaggerModule.setup`) aberto em produção expõe a superfície inteira e exemplos com dados. Correção: condicionar ao ambiente ou proteger com auth.
- Health/metrics (`/metrics`, `/health/details`, `/debug`) públicos expõem versões e topologia.

## Autenticação

- `JwtModule.register({ secret })` com secret literal ou fraco. `signOptions` sem `expiresIn`. `JwtStrategy` com `ignoreExpiration: true`. `passport-jwt` sem `algorithms`.
- `validate(payload)` da strategy que confia no payload sem buscar o usuário quando há revogação/desativação de conta.
- Validação de token de IdP (Cognito): confira `issuer`, `audience`/`client_id`, `token_use`, JWKS com cache e rotação. `jwt.decode` sem verify é achado BLOCKER.
- `@nestjs/passport` local strategy comparando senha com `===`. Correção: `argon2.verify`/`bcrypt.compare`.

## CORS, headers, CSRF, rate limit

- `app.enableCors()` sem opções libera `*`. `origin: true` reflete qualquer origem. Com `credentials: true`, é MAJOR. Correção: lista exata por ambiente.
- `helmet()` ausente em `main.ts` de serviço exposto ao navegador. MINOR se um gateway já aplica os headers.
- `ThrottlerModule`/`@Throttle`: rotas de login, reset, OTP, criação de conta e endpoints de IA com `@SkipThrottle()` ou sem throttler. Atrás de proxy, configure `trust proxy` e a chave do throttler (IP real). Sem isso todos os clientes compartilham o IP do proxy.
- Cookies: `httpOnly`, `secure`, `sameSite` configurados em `res.cookie`.

## Webhooks e mensageria (RabbitMQ via @golevelup)

- Endpoint de webhook com `@Public()` sem verificação de assinatura sobre `rawBody` (`NestFactory.create(AppModule, { rawBody: true })`). Verificar assinatura sobre o JSON reparseado falha e pode ser contornado.
- `@RabbitSubscribe` handler confia no payload: valide com `ValidationPipe`/zod dentro do handler. Mensagens de fila compartilhada são input externo.
- Handler que usa `userId` da mensagem para ler/alterar dado sem checar se o produtor é confiável: confira o contrato do evento.
- Credenciais de broker em `AMQP_URI` literal no código.

## HTTP client (axios, HttpService)

- `HttpService.get(userUrl)`: SSRF. Correção: allowlist de host e bloqueio de IP privado pós-DNS.
- `httpsAgent: new https.Agent({ rejectUnauthorized: false })`: MAJOR em produção.
- Repasse de header `Authorization` do usuário a terceiros por interceptor genérico. Correção: token por destino.
- Log do interceptor axios com `config.headers`/`data`: handoff para review-observabilidade (vaza token).
- Redirect follow em axios (`maxRedirects` default 5) em fetch de URL de usuário. Correção: `maxRedirects: 0` e revalidar cada salto.

## Redis (ioredis) e cache

- Chave de cache sem id do usuário/tenant para resposta personalizada: leitura cruzada. Correção: incluir `user.id` ou `tenantId` na chave.
- Chave montada com input do usuário sem prefixo e sem limite: poluição de chaves, colisão de namespace.
- `KEYS *`/`SCAN` por padrão vindo do cliente, `EVAL` com input.
- Senha do Redis ausente em config de ambiente compartilhado.

## ORM e SQL dentro de Nest

- `@InjectRepository` com ``createQueryBuilder().where(`x = ${v}`)``: injeção. Correção: `.where('x = :v', { v })`.
- `prisma.$queryRawUnsafe`: ver `prisma-postgres.md`.

## Configuração

- `ConfigModule` sem validação (`validationSchema`/`validate`): variável ausente derruba para default inseguro (`JWT_SECRET ?? 'dev'`). Correção: falhar no boot.
- `process.env.X || 'valor-hardcoded'` para segredo.
- `app.set('trust proxy', true)` incondicional permite spoof de IP via `X-Forwarded-For` em rate limit.
- `synchronize: true` em prod é do dono review-migrations.

## Falsos positivos frequentes

- Rota sem guard local coberta por `APP_GUARD`.
- `@Public()` em `/health` e `/ready` sem detalhes.
- `ValidationPipe` configurado por `@UsePipes` na classe em vez de global.
- Entidade devolvida sem DTO quando só tem campos públicos (catálogo).
