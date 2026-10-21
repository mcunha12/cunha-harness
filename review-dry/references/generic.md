# DRY: referência agnóstica de stack

## Como identificar conhecimento duplicado

Conhecimento é uma decisão que o sistema toma: "aluno aprovado tem nota >= 7 e frequência >= 75%". Duplicação é a mesma decisão escrita em 2+ lugares. Procure por decisões, não por texto.

Sinais de busca, em ordem de rendimento:

1. Literais numéricos de domínio (0.75, 7, 30, 86400, 100).
2. Strings de status e de tipo comparadas com `===`, `case`, `IN (...)`.
3. Fórmulas (percentual, média, desconto, prazo = início + N dias).
4. Listas de valores permitidos (arrays de strings, enums, `IN`).
5. Condições compostas de elegibilidade (`a && b || c`).
6. Nomes de campos de payload usados em 2+ camadas com transformação.
7. Chaves de cache, de feature flag, de evento e de fila.

Comando base: `git grep -n -F '<literal>'`, depois `git grep -n -E '<forma da expressão>'`. Procure também a forma invertida (`< 0.75`, `!(x >= 0.75)`).

## Cópia que ficou para trás

O diff altera uma regra. Busque todas as outras ocorrências. Se existem e o diff não as toca, o achado tem confiança alta e severidade pelo impacto da divergência. Esse é o caso mais valioso desta skill, porque o revisor humano só vê o hunk.

## Fonte da verdade: critérios de escolha

Escolha pela ordem:

1. Onde o dado nasce ou onde o efeito é irreversível (emissão, cobrança, gravação). A regra mora ali.
2. O serviço dono do domínio, segundo README, config ou `related_repos`.
3. Um pacote compartilhado versionado, quando 3+ consumidores precisam avaliar a regra localmente.
4. O servidor devolve o resultado calculado (`canX: boolean`) e o cliente só exibe. Preferível a duplicar a fórmula.

Código compartilhado entre repos tem 3 formas, da mais segura para a menos: pacote versionado (semver, changelog), geração de código a partir de um schema, cópia com teste de paridade. Cópia sem teste de paridade é achado.

## Cadeia de derivação aceitável

Schema (zod, OpenAPI, Prisma, proto) → tipos gerados → validação → formulário. Duplicar entre camadas é correto quando cada camada deriva do schema. A cópia manual quebra a cadeia.

## Quando duplicar é a decisão correta

- Motivos de mudança distintos (telas de produtos diferentes, adapters de vendors diferentes).
- Menos de 3 ocorrências e nenhuma regra de domínio.
- A abstração exigiria parâmetros booleanos ou callbacks para cobrir as diferenças.
- Fronteira entre serviços sem pacote compartilhável: cópia com teste de contrato custa menos que acoplamento de deploy.
- Teste: fixture explícita vale mais que helper opaco.

Nesses casos o achado é NIT ou não existe.

## Anti-DRY: sinais no diff

| Sinal | Leitura |
|---|---|
| Helper novo com 1-2 callers | Prematuro. Manter inline. |
| Parâmetro booleano novo em helper existente | Ramo por caller. Contar os ramos. |
| `options` com 5+ chaves opcionais | God util. |
| Caller passa `undefined`/`null` posicional para pular argumentos | Abstração apertada demais. |
| Componente com prop `variant` que troca estrutura inteira | Dois componentes dentro de um. |
| Herança para reaproveitar 2 métodos | Composição ou função. |
| Base class com hooks `onX` vazios que 1 subclasse usa | Template method sem uso real. |

Correção típica de wrong abstraction: inline a abstração em cada caller, apague o que cada um não usa, extraia de volta só o núcleo comum que sobrar.

## Severidade: critérios por impacto da divergência

| Divergência provável entre cópias | Severidade base |
|---|---|
| Dinheiro, nota, acesso, certificado, dado de outro usuário | BLOCKER |
| Valor exibido diferente entre telas, bug funcional visível | MAJOR |
| Comportamento diferente em borda (vazio, zero, timezone) | MAJOR |
| Constante cosmética, texto, cor | MINOR |
| Utilitário trivial | NIT |

Reduza um nível quando existe teste de paridade entre as cópias.

## Checklist de verificação antes de emitir

1. Listei todas as cópias com `repo/arquivo:linhas`.
2. Confirmei que mudam pelo mesmo motivo.
3. Nomeei a fonte da verdade e justifiquei.
4. O `fix` mostra o código da extração ou da remoção.
5. Conferi que o helper proposto não existe já no repo.
6. Descrevi a ordem de mudança quando há 2+ repos.
