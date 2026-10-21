# DRY em NestJS

## DTO versus tipo de domínio versus entidade

- Sinal: `CreateXDto`, `UpdateXDto`, `XResponseDto` e `interface X` com os mesmos 8 campos escritos à mão.
- Impacto: campo novo entra em 2 de 4 declarações. O Swagger documenta um shape e o service usa outro.
- Correção: `PartialType`, `PickType`, `OmitType`, `IntersectionType` de `@nestjs/swagger` (ou `@nestjs/mapped-types`). Resposta e entidade permanecem separadas por ciclo de vida. Derive o que tem motivo comum.
- Sinal: regras do `class-validator` copiadas de um DTO para outro com limites diferentes (`@MaxLength(100)` contra `@MaxLength(120)` para o mesmo campo).

## Cross-cutting repetido

- Sinal: `try/catch` com o mesmo mapeamento de erro em 5 controllers. Mesma checagem de ownership ou tenant no início de 6 handlers. Mesmo `ParseUUIDPipe` configurado à mão em toda rota.
- Correção: exception filter, interceptor, guard com decorator (`@RequireOwnership()`), pipe global. Checagem de autorização copiada é BLOCKER potencial: uma rota esquecida expõe dado.

## Configuração e constantes

- Sinal: `process.env.X` lido em 4 services, com default diferente em cada um. Nome de fila, exchange e routing key RabbitMQ como string em producer e consumer.
- Impacto: o producer publica numa routing key que o consumer não escuta. Silencioso.
- Correção: `ConfigService` tipado com schema validado no boot. Constantes de mensageria exportadas de um módulo que producer e consumer importam. Entre repos, pacote ou contrato documentado.

## Clients HTTP

- Sinal: `axios.create` repetido em 3 módulos com baseURL, timeout e headers copiados. Interceptors de log e de erro replicados.
- Correção: `HttpModule` configurado uma vez com factory, ou um client provider por serviço externo. O wrapper expõe métodos tipados do serviço externo, sem repassar o `AxiosInstance` cru.

## Repositórios e serviços

- Sinal: mesmo `where` com soft delete (`deletedAt: null`) e tenant em 5 métodos. Mesma paginação reescrita por módulo.
- Correção: método privado do repository com o filtro base. Para filtro de segurança, extensão do cliente ORM. Paginação em helper único com o contrato de resposta do repo.

## Anti-DRY em Nest

- Sinal: `BaseService<T>`/`BaseController<T>` genéricos com hooks e flags, herdados por 6 módulos que sobrescrevem metade dos métodos. Cada módulo diverge em regra de acesso e validação.
- Correção: composição com providers pequenos. Herdar só quando todos os filhos usam todos os métodos.

## Eventos e mapeamentos

- Sinal: payload de evento montado em 2 lugares com campos diferentes. Handler duplicado em 2 consumers para a mesma mensagem.
- Correção: factory de evento por tipo e DTO do evento versionado. Contrato de mensageria é de review-contratos.
