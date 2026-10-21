# Tipagem em NestJS

## DTO e class-validator

- DTO é `class`, nunca `interface`/`type`, porque os decorators dependem de metadado de runtime (`emitDecoratorMetadata`).
- Cada propriedade do DTO tem tipo TS e decorator coerentes:

| Tipo TS | Decorators coerentes |
|---|---|
| `string` | `@IsString()`, `@IsNotEmpty()` se obrigatório, `@MaxLength(n)` |
| `number` | `@IsInt()` ou `@IsNumber()`, mais `@Type(() => Number)` em query |
| `boolean` | `@IsBoolean()`, mais `@Transform` em query |
| `string?` | `@IsOptional()` mais `@IsString()` |
| `Status` (enum) | `@IsEnum(Status)` |
| `Foo[]` | `@IsArray()`, `@ValidateNested({ each: true })`, `@Type(() => Foo)` |
| `Date` | `@IsDate()` com `@Type(() => Date)`, ou `@IsISO8601()` com `string` |
| `Foo \| Bar` | sem decorator direto: `@ValidateNested` com `@Type` discriminador, ou separar DTOs |

- Sinal de divergência: `foo?: string` sem `@IsOptional()` (obrigatório em runtime, opcional no tipo); `foo: string` com `@IsOptional()`; `@IsString()` em `number`; `@IsEnum(A)` com tipo `B`; array sem `@ValidateNested`. Impacto: o handler recebe valor que o tipo não prevê. Correção: alinhar.
- `!:` em propriedade de DTO é convenção. `?:` com `@IsOptional()` é o padrão para opcional.
- `PartialType`, `PickType`, `OmitType`, `IntersectionType` de `@nestjs/swagger` (ou `mapped-types`) herdam tipo e decorators. Sinal: DTO de update copiando campos do DTO de create.
- `@Transform` e `@Type` mudam o tipo entre entrada e saída. Sem `ValidationPipe({ transform: true })`, o tipo declarado (`number`) diverge do valor recebido (`string`). Verifique o pipe global em `main.ts`.
- DTO de resposta com `@Exclude`/`@Expose` e `plainToInstance`: o tipo de retorno do método tem de ser o DTO.

## Injeção e módulos

- Token por string ou `Symbol` com `@Inject('TOKEN') private readonly x: SomeType`: o tipo é uma afirmação. Correção: classe abstrata como token, ou constante de token tipada junto da interface.
- `ModuleRef.get('X')` devolve `any`. Use `get<T>(Token)` com classe.
- `forwardRef(() => X)` e `@Inject(forwardRef(...))`: tipo circular é sintoma de ciclo de módulo (dono: review-modularidade).
- `DynamicModule` com `forRoot(options: any)`. Correção: interface de opções e `ConfigurableModuleBuilder`.

## Config

- `ConfigService.get('PORT')` retorna `any` (ou `unknown` conforme versão). `get<number>('PORT')` é um cast. Correção: `ConfigService<EnvVars, true>` com `infer`, ou schema (`zod`, `Joi`) em `validate` do `ConfigModule` e tipo derivado do schema.
- `process.env.X` é `string | undefined`. Converta com validação no boot (dono do boot é o review-resiliencia).

## Controllers e services

- Retorno de método de controller tipado como DTO de resposta. `Promise<any>` desliga o Swagger e a serialização tipada.
- `@Req() req: any` e `@Req() req: Request` sem o usuário. Correção: `interface AuthenticatedRequest extends Request { user: JwtPayload }` ou decorator `@CurrentUser()` com tipo.
- Decorator customizado (`createParamDecorator`) devolve `any` por padrão: tipar o retorno do decorator e o parâmetro do handler.
- Guard e interceptor com `context.switchToHttp().getRequest()` (`any`): genérico `getRequest<AuthenticatedRequest>()`.
- Exception filter: `catch(exception: unknown, host: ArgumentsHost)` com estreitamento por `instanceof HttpException`.
- `@Query() query` sem DTO é `any`. `@Query() q: ListQueryDto` com `transform: true`.
- `@Param('id') id: string` sem pipe. `ParseUUIDPipe`/`ParseIntPipe` alinham tipo e valor.

## Mensageria

- `@RabbitSubscribe` handler com `msg: any`. Tipe o payload e valide na entrada (schema).
- `@EventPattern`/`@MessagePattern` com `@Payload() data: any`.

## ORM

- Entidade TypeORM com `@Column()` sem tipo explícito para `string | null`/`union`: o metadado vira `Object`. Correção: `@Column({ type: 'varchar', nullable: true })`.
- Prisma: `Prisma.UserCreateInput` e `UncheckedCreateInput` são tipos diferentes. Misturar relação (`connect`) e FK escalar (`userId`) falha no tipo.
