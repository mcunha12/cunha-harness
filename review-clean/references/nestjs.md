# Clean em NestJS

## Controllers, services e responsabilidade

- Sinal: controller com regra de negócio, acesso direto a repository/ORM ou montagem de query. Correção: controller valida, delega e devolve. A regra vive no service ou use case. Camadas e fronteiras entre módulos são de review-modularidade. Aqui conta a responsabilidade da classe.
- Sinal: service com 8+ providers injetados e métodos sem estado em comum. SRP. Correção: serviços por caso de uso (`EnrollStudentService`, `CancelEnrollmentService`) ou por agregado.
- Sinal: `@Injectable()` que mistura chamada a API externa, regra e formatação de resposta. Correção: client/adapter para a API externa, regra em classe de domínio, mapper para a resposta.

## DIP

- Sinal: `new OpenAI()`, `new Redis()`, `new S3Client()`, `axios.create()` dentro de método de service. Correção: provider do módulo com `useFactory`, injetado por construtor.
- Sinal: `@Inject()` de classe concreta de vendor na regra. Correção: token de interface (`@Inject(PAYMENT_GATEWAY) private gateway: PaymentGateway`) quando existe fronteira real (troca de vendor, fake de teste). Sem fronteira real, a classe concreta injetada serve.
- Sinal: `ModuleRef.get()`/`moduleRef.resolve()` na lógica (service locator). Impacto: dependência escondida, teste sem aviso. Correção: injeção por construtor.
- Sinal: `Date.now()` na regra. Correção: provider `Clock`.

## Efeitos colaterais

- Sinal: `onModuleInit` com escrita em banco ou chamada externa sem idempotência. Impacto: roda a cada start e a cada réplica.
- Sinal: getter de service (`get status()`) ou `find*` que atualiza. CQS.
- Sinal: estado em campo de provider singleton (`this.currentUser = ...`, `this.cache = {}`) escrito por request. BLOCKER: o provider padrão é singleton e vaza entre requests. Correção: passar no parâmetro, `Scope.REQUEST` com consciência do custo, ou `AsyncLocalStorage`/`nestjs-cls`.
- Sinal: `@Global()` módulo com estado mutável.
- Sinal: interceptor/guard que muta o `request` com dado de negócio além de `user`. Correção: decorator de parâmetro dedicado.

## OCP

- Sinal: `switch (dto.type)` no service para escolher regra, repetido em 3 métodos. Correção: strategy providers registrados com token multi (`@Inject(HANDLERS) handlers: Handler[]`) e mapa por `kind`.
- Sinal: lista de `if (event.name === ...)` em consumer de mensagens. Correção: `Record<EventName, Handler>` ou decorators por evento do `@golevelup/nestjs-rabbitmq` (`@RabbitSubscribe` por routing key).

## Exceções e fluxo

- Sinal: service que lança `HttpException`/`NotFoundException` (acopla a regra ao HTTP). Correção: exceção de domínio no service e exception filter que traduz para HTTP. Em app só HTTP pequeno, o padrão local prevalece.
- Sinal: `return null` do service tratado com `if (!x) throw new NotFoundException()` em 5 controllers. Correção: método `getOrThrow` no service, ou filtro de exceção de domínio.
- Sinal: método com `try/catch` grande que mistura 3 operações. Correção: extrair operações, tratar erro por operação.

## Parâmetros e DTOs

- Sinal: método de service com 5+ parâmetros espelhando o DTO inteiro. Correção: receber o DTO (ou tipo de domínio) como objeto.
- Sinal: `@Body() body: any` ou `Record<string, unknown>` passado adiante. Tipagem e validação: review-tipagem e review-contratos.
- Sinal: método com `userId, courseId, enrollmentId, packId` repetidos. Data clump. Correção: `EnrollmentRef`.

## Testabilidade como sinal

- 5+ providers mockados num `Test.createTestingModule` para testar 1 regra: SRP ou DIP. Correção: extrair a regra para classe pura que o teste instancia sem Nest.
- `jest.mock('../db')` global para conseguir testar: DIP.
