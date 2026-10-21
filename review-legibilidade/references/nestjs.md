# review-legibilidade — NestJS

Camadas, módulos e DI (fronteiras) são de review-modularidade. SRP de service é de review-clean. Aqui entra a leitura.

## 1. Nome e estrutura
- Arquivo por papel, com sufixo do Nest: `enrollments.controller.ts`, `enrollments.service.ts`, `enrollments.module.ts`, `create-enrollment.dto.ts`, `enrollment.entity.ts`. Arquivo `helpers.ts` com regra de negócio de enrollment deveria ser serviço ou função nomeada.
- Classe: `EnrollmentsService` (plural quando o repo adota), nome de método com verbo de domínio (`cancelEnrollment`, `transferToClass`). `process`, `handle`, `execute`, `run` sem objeto não dizem. `create/update/remove/findOne/findAll` (CRUD padrão do Nest) são aceitos em CRUD puro.
- Método de controller nomeia a ação, e a rota nomeia o recurso (`POST /enrollments/:id/cancel`). Verbo no path divergente do padrão do repo é MINOR.
- DTO nomeia a intenção: `CreateEnrollmentDto`, `EnrollmentSummaryResponseDto`. `DataDto`, `PayloadDto`, `ReqDto` não dizem.
- Nome de provider token em string solta (`@Inject('ENR_SVC')`): constante exportada com nome legível, ou classe como token.

## 2. Controller e service legíveis
- Controller fino: validação, delegação, resposta. Controller com `if` de regra de negócio e 3 níveis de aninhamento pesa na leitura; mover para service é de review-modularidade. Aqui reporte o custo de leitura e faça handoff.
- Método de service com mais de ~40 linhas de IO intercalado com cálculo: extraia o cálculo para função pura nomeada (reduz complexidade; o princípio é de review-clean).
- Injeção por construtor com 7+ dependências indica classe grande. Mencione e passe para review-clean.
- Decorators empilhados (`@UseGuards`, `@UseInterceptors`, `@ApiResponse` ×5, `@Roles`) acima de ~6 linhas por método: agrupe com `applyDecorators` em decorator nomeado (`@AuthenticatedRoute()`).
```ts
export const StudentRoute = () => applyDecorators(UseGuards(JwtAuthGuard, StudentGuard), ApiBearerAuth());
```
- `@Body() body: any`, `@Query() query` sem DTO: custo de leitura (o leitor não sabe o formato). Tipo é de review-tipagem; validação de borda é de review-contratos.

## 3. Async, erros e logs
- Exceção HTTP com mensagem útil: `throw new NotFoundException(`Matrícula ${id} não encontrada`)`. `throw new Error('erro')` e `BadRequestException()` sem mensagem custam na leitura de log e de resposta.
- Exception de domínio própria (`EnrollmentAlreadyCancelledException`) lê melhor que `ConflictException('...')` repetida em 5 lugares. Reuse (review-dry).
- `try/catch` com `catch (e) { throw e; }` sem ação: remover.
- Log com contexto textual do caso, com ids: `this.logger.warn(`Turma ${classId} sem vagas para matrícula ${enrollmentId}`)`. `this.logger.log('here')`, `console.log('debug')`: MINOR. Estrutura de log e PII são de review-observabilidade.

## 4. Configuração e constantes
- `process.env.X` espalhado e comparado com literais (`=== 'true'`): `ConfigService` com getter nomeado (`isFeatureXEnabled`). Duplicação de leitura de env é de review-dry.
- Constantes de domínio (limites, prazos) com unidade no nome e localizadas junto do serviço que as usa. Constante usada em vários módulos vive no módulo dono.
- Valores de timeout e TTL: `CACHE_TTL_SECONDS = 300`, nome com unidade.

## 5. Testes (nome apenas)
- `describe('EnrollmentsService')` > `describe('cancelEnrollment')` > `it('lança Conflict quando já cancelada')`. Nome que diz comportamento e condição. Estrutura e dados de teste são de test-audit.
