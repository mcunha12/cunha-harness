# Núcleo

Vale para todo código. Cada regra evita um BLOCKER ou MAJOR do especialista de origem.

## Segurança

- [SEG] Toda busca por id de recurso filtra pelo dono ou pelo tenant do usuário autenticado, além do id. — origem: review-seguranca/bola-idor
- [SEG] Query parametrizada sempre. Nunca interpole entrada de usuário em SQL, comando de shell ou caminho de arquivo. — origem: review-seguranca/injecao
- [SEG] Segredo (chave de provedor, token, senha) vem de variável de ambiente no servidor. Nunca no diff, no bundle ou em `window.env`. — origem: review-seguranca/segredo-no-bundle
- [SEG] Endpoint com custo por chamada (LLM, e-mail, SMS) nasce com rate limit por usuário. — origem: review-seguranca/abuso
- [SEG] HTML vindo de usuário ou de terceiro passa por sanitizer antes de renderizar. — origem: review-seguranca/xss
- [SEG] Webhook verifica a assinatura antes de processar o corpo. — origem: review-seguranca/webhook
- [SEG] Update a partir do body usa whitelist de campos. Nunca `update(id, req.body)`. — origem: review-seguranca/mass-assignment
- [SEG] CORS com allowlist exata por ambiente; regex de origem sempre com âncora; nunca `*` com credenciais. — origem: review-seguranca/cors

## Legibilidade

- [LEG] O nome diz o que a função faz. `getX` e `isX` não gravam, não publicam evento e não têm efeito colateral. — origem: review-legibilidade/nome-que-mente
- [LEG] Variável com unidade leva a unidade no nome e no valor (`delayMs` em milissegundos). — origem: review-legibilidade/nome-que-mente
- [LEG] Sem ternário dentro de ternário. Use `if/else`, early return ou um objeto de mapeamento. — origem: review-legibilidade/complexidade
- [LEG] Condição com 5 ou mais operandos vira uma função ou constante com nome. — origem: review-legibilidade/complexidade
- [LEG] Função nova com complexidade cognitiva até 25 e aninhamento até 4. Acima disso, extraia funções com nome. — origem: review-legibilidade/complexidade
- [LEG] Um termo por conceito de domínio. Use o termo que o repo já usa (faça grep antes de nomear). — origem: review-legibilidade/linguagem-ubiqua
- [LEG] Nome de rota e de handler bate com a chave que ele usa: "get by slug" busca por `slug`. — origem: review-legibilidade/nome-que-mente

## Clean

- [CLN] Função de leitura não grava. Separe consulta de comando. — origem: review-clean/side-effect
- [CLN] Servidor não guarda estado de request em variável de módulo. Estado por request vai no contexto da request. — origem: review-clean/estado-compartilhado
- [CLN] Nunca mute parâmetro que o caller reutiliza. Copie antes de `sort`, `splice` ou atribuição. — origem: review-clean/mutacao-de-parametro
- [CLN] Serviço com um motivo de mudança. Caso de uso novo que mistura IO, regra e formatação vira outra unidade. — origem: review-clean/responsabilidade-de-servico
- [CLN] `switch` por tipo repetido em 3 ou mais pontos vira mapa ou polimorfismo antes de ganhar mais um tipo. — origem: review-clean/switch-repetido
- [CLN] Regra crítica (pagamento, matrícula, nota) recebe o client de IO por parâmetro ou construtor. Nunca `new` do client dentro da decisão. — origem: review-clean/seam-de-teste
- [CLN] Retorno com significado único. Use união discriminada ou erro tipado no lugar de `null` com vários sentidos. — origem: review-clean/null-ambiguo
- [CLN] Override nunca lança `NotImplemented` em método que o fluxo principal chama. — origem: review-clean/lsp

## DRY

- [DRY] Regra de cobrança, desconto, nota, aprovação ou acesso tem uma fonte única. Antes de escrever, procure se ela já existe em outro arquivo ou repo. — origem: review-dry/regra-de-negocio
- [DRY] Ao mudar uma regra replicada, mude todas as cópias no mesmo diff, ou extraia a fonte única. — origem: review-dry/regra-de-negocio
- [DRY] Filtro de tenant e de soft delete entra em toda query equivalente. Prefira um escopo único no repository. — origem: review-dry/filtro-replicado
- [DRY] Validação de formulário e DTO usam os mesmos limites, de preferência do mesmo schema. — origem: review-dry/validacao-divergente
- [DRY] Não estenda util com flags booleanas. Abstração com 4 ou mais ramos por caller vira funções separadas. — origem: review-dry/god-util

## Comentários

- [COM] Comentário é one-liner e explica o porquê. Sem bloco multi-linha. — origem: review-comentarios/multi-linha
- [COM] Mudou o comportamento, atualize o comentário no mesmo diff. Comentário mentiroso é pior que nenhum. — origem: review-comentarios/comentario-mentiroso
- [COM] Risco não óbvio ganha one-liner: `await` removido de propósito, ordem crítica, dado sensível, `@ts-expect-error`. — origem: review-comentarios/adicionar-one-liner

## Tipagem

- [TIP] Fronteira de I/O valida em runtime (zod, class-validator) e deriva o tipo do schema. Nunca `res.json() as T` ou `JSON.parse() as T`. — origem: review-tipagem/fronteira-de-io
- [TIP] Sem `any`, `as` mentiroso, `@ts-ignore` ou `@ts-nocheck` em regra de negócio. — origem: review-tipagem/escape
- [TIP] Estado com combinações ilegais vira união discriminada com checagem exaustiva. — origem: review-tipagem/TIP-MOD
- [TIP] Type predicate checa de fato o que afirma. — origem: review-tipagem/predicate
- [TIP] Nunca desligue `strict` no `tsconfig`. — origem: review-tipagem/tsconfig
- [TIP] Contexto React nasce com valor real ou `undefined` checado. Nunca `createContext({} as Ctx)`. — origem: review-tipagem/contexto

## Arquitetura e lições gerais

- [ARQ] Antes de criar um padrão, procure como o repo já resolve o mesmo problema e siga. — origem: review-arquitetura/conformidade
- [ARQ] Reutilize componente, hook, util ou serviço que já existe antes de criar outro. — origem: review-arquitetura/conformidade
- [LEG] Arquivo de componente acima de ~200 linhas se divide; util com responsabilidades distintas se divide por domínio. — origem: review-legibilidade/arquivo-extenso
- [CTR] Renomear campo de DTO é breaking change de contrato: faça grep dos consumidores e mude produtor e consumidor juntos. — origem: review-contratos/CTR-BRK
- [MOD] Mudança local não altera comportamento global (estilo global, config compartilhada, util usado em todo o app) sem pedido explícito. — origem: review-modularidade/escopo
