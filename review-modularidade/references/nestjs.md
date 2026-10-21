# Modularidade em NestJS

## Anatomia da fronteira

- O módulo (`@Module`) é a unidade. `providers` é o privado. `exports` é a API pública. `imports` são as dependências declaradas.
- Fronteira correta: outro módulo usa um provider porque o dono o listou em `exports` e porque o consumidor importou o módulo.
- Bypass: importar a classe do arquivo (`import { XService } from '../x/x.service'`) e listá-la nos `providers` do módulo consumidor. Cria uma segunda instância, com dependências próprias, fora do controle do dono. Correção: importar o módulo e consumir via `exports`.

## Sinais por item

- `forwardRef(() => M)`: ciclo entre módulos ou providers. Cite o caminho nos dois sentidos. Correção: extrair o terceiro módulo com o conceito comum (consulta, evento de domínio) e importar nos dois. Alternativa: eventos (`EventEmitter2`, mensagem) para desacoplar a chamada de volta.
- `@Global()` em módulo de feature. Reservado para infra (config, logger, observabilidade). Correção: importar onde usa.
- `exports` com 10+ providers ou com providers internos (repositories, mappers). Correção: exportar só o service/facade do módulo.
- Módulo `SharedModule`/`CommonModule` que importa módulos de feature. Seta invertida.
- Módulo de feature que declara o `PrismaService`/repository de outra feature em `providers`. Correção: importar o módulo dono.
- `ModuleRef.get(X, { strict: false })` para pegar provider de outro módulo: service locator que contorna `imports`. Correção: declarar a dependência.
- Provider de um módulo injetando o `Repository` de outra feature (tabela alheia). Correção: chamar o service da feature dona.

## Camadas dentro do módulo

- Controller: transporte, validação (pipes/DTO), autorização por guard, delegação. Sem regra e sem ORM.
- Service / use case: regra e orquestração. Sem `Request`/`Response`, sem decorators HTTP, sem `HttpException` quando houver filtro de domínio (siga o padrão local).
- Repository / adapter: ORM e vendor. Sem regra.
- Domínio: tipos e regras puros. Sem `@nestjs/*`, sem ORM, sem `class-validator`.
- Sinal: entidade de domínio com decorators `@Column` (TypeORM) acoplada ao schema. Aceito em app que usa entidade ORM como modelo. Reporte só quando a regra importa a entidade para lógica de negócio com mapeamento reverso complicado.

## Responsabilidade entre serviços (Nest como BFF/gateway)

Leia o README. Se o serviço é camada de agregação:

- Service com `if` de negócio (elegibilidade, preço, desconto, estado) é sinal. Service que junta 3 chamadas, renomeia campos e filtra o que o front precisa cumpre o papel.
- Controllers do gateway que repassam o body cru para o serviço dono sem validação própria: contrato de review-contratos.
- Chamada do gateway a outro gateway ou a um serviço que a arquitetura reserva para outro papel: confirme no README.
- Módulos de IA: cliente de LLM e prompts no módulo/serviço que o README designa. Chave e custo no lugar errado são sinal.

## Integração entre módulos por mensagem

- RabbitMQ (`@golevelup/nestjs-rabbitmq`): `@RabbitSubscribe` com nomes de exchange/routing key em strings em dois módulos. Fronteira acoplada por string. Correção: constantes em um módulo de contrato importado por producer e consumer. Shape do evento é de review-contratos.
- Consumer de um módulo chamando repository de outro módulo: bypass. Correção: chamar o service dono.

## Configuração e infra

- `ConfigModule.forRoot` com `isGlobal: true` é aceito. `process.env` lido direto em service de domínio: fronteira vazada. Correção: `ConfigService` tipado injetado.
- `onModuleInit` com efeito (conectar, assinar fila) em módulo de feature: confirme que roda uma vez e que o fechamento existe. Resiliência pertence a review-resiliencia.
- `DynamicModule` (`forRoot`/`forRootAsync`) para libs internas: padrão correto para config por consumidor.

## Ferramentas

- `madge --circular --extensions ts src` detecta ciclo de arquivo. Ciclo de módulo Nest aparece como `forwardRef` (`git grep -n forwardRef`).
- `dependency-cruiser` com regras por pasta (`controllers` não importam `repositories`).
- `nest-commander`/Nest DevTools gráfico: fora do escopo da checagem automática.
