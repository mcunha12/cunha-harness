# Modularidade: referência agnóstica de stack

## Descobrir a arquitetura declarada

Ordem de leitura, parando quando achar a regra:

1. `CLAUDE.md`, `README.md`, `docs/architecture*`, ADRs.
2. Config de lint de fronteira: `eslint-plugin-boundaries`, `no-restricted-imports`, `.dependency-cruiser.*`, `.importlinter`.
3. Estrutura de pastas e `exports` de pacote.
4. `repo_role` e `related_repos` da config do orquestrador.
5. Padrão dominante nos imports existentes (quem importa quem hoje).

Registre o que achou no `summary`. Sem regra declarada, aplique só a regra universal: detalhe depende de política, não o contrário. Rebaixe confiança para média.

## Regra de dependência: tabela de verificação

Para cada aresta nova `origem → destino`, classifique as pontas.

| Origem | Destino proibido | Destino correto |
|---|---|---|
| Domínio / regra | ORM, HTTP client, SDK, framework web, UI | interface (port) definida no domínio |
| Use case / service | objeto de request/response do transporte | DTO de aplicação, tipo de domínio |
| Controller / handler | repository, ORM, vendor | service / use case |
| Repository / adapter | service, controller | tipos de domínio |
| Feature A | internals de feature B | API pública de B |
| Módulo estável | módulo instável | interface própria |
| Pacote de lib | app que o consome | nada |

Dentro de um app CRUD fino sem domínio, controller → service → repository é a arquitetura inteira. Cobre só o que viola essa cadeia.

## Instabilidade e dependências estáveis

- Ca (aferente): quantos módulos importam este. Ce (eferente): quantos este importa.
- I = Ce / (Ca + Ce). I perto de 0 = estável, difícil de mudar. I perto de 1 = instável.
- Dependa na direção da estabilidade. Módulo com Ca alto muda pouco e expõe interface pequena.
- Meça Ca com `git grep -l "from '.*/<modulo>'" | wc -l`. Meça Ce lendo os imports do módulo.
- Ce 8+ em módulo que não é composition root indica coesão baixa.

## Ciclos: como provar e como quebrar

Prova: escreva o caminho completo (`a.ts → b.ts → c.ts → a.ts`) e cite as 3 linhas de import. Sem o caminho, confiança baixa.

Sintomas de runtime: `undefined` ao importar uma constante, `Cannot access 'X' before initialization`, classe base `undefined` em `extends`, erro só no bundle de produção ou só no teste.

Quebra, em ordem de preferência:

1. Extrair o conceito comum (tipo, constante, função) para um módulo que os dois importam.
2. Inverter a dependência: o módulo estável define a interface, o outro implementa.
3. Fundir os módulos quando mudam sempre juntos.
4. Passar a dependência por parâmetro em runtime.

Import tardio dentro de função e `forwardRef` escondem o ciclo. Nomeie como sintoma.

## Barrel files

- `export *` em diretório com 20+ arquivos: importar 1 símbolo carrega o diretório inteiro (bundle e testes), e abre ciclos quando um arquivo do barrel importa o próprio barrel.
- Sinal de ciclo por barrel: arquivo dentro de `feature/` importando `from '../feature'` ou `from '.'`.
- Correção: importar do arquivo de origem dentro da própria feature, e deixar o barrel só como API pública externa, com exports nomeados.
- Barrel de API pública com 5-10 símbolos nomeados é correto.

## Superfície pública

- Cada `export` é uma promessa. Export sem consumidor externo (confirme com `git grep`) vira interno.
- Tipos e constantes internos vazando pela assinatura pública (retorno de função exportada citando tipo interno) forçam o consumidor a importar o interno.
- Regra de lint que trava: `no-restricted-imports` com padrão `**/internal/**`, `exports` do `package.json`, `boundaries/element-types`.

## Responsabilidade por serviço (sistemas com 2+ repos)

Perguntas, na ordem:

1. Qual serviço é dono do dado e da regra? (README, `repo_role`, onde a escrita acontece.)
2. A camada de agregação só compõe, adapta shape e protege a borda?
3. Há decisão de negócio (valor, acesso, estado) fora do dono?
4. Existe caminho direto cliente → serviço interno que contorna a porta declarada?
5. A orquestração de LLM mora no serviço que a arquitetura designa?

Resposta "sim" em 3, 4 ou "não" em 5 gera achado. Cite a fonte da arquitetura no `problem`.

## Código compartilhado entre repos

Opções, da mais forte para a mais fraca:

1. Pacote versionado (semver, changelog, `exports`). O consumidor fixa a versão.
2. Código gerado a partir do schema de origem (OpenAPI, proto, zod). A fonte é única.
3. Cópia com origem citada (one-liner) e teste de paridade.
4. Cópia silenciosa. Achado.

Mudança em pacote compartilhado: o diff do pacote e o diff do consumidor andam juntos, com a ordem de publicação descrita.

## Side effects no import

Lista de sinais no topo de módulo: `connect()`, `new Client()` configurado com `process.env`, `setInterval`, `addEventListener`, `app.listen`, `fetch`, `fs.readFileSync` de config, `registerGlobal`, `import './setup'`.

Correção: factory chamada pela raiz de composição, ou inicialização preguiçosa idempotente (`getClient()`).

## Shotgun surgery

Contagem: arquivos tocados por uma única razão de mudança, em 4+ pastas. Pergunte: existe um lugar que, se existisse, conteria esta mudança toda? Tabela de configuração, mapa `Record<Kind, Handler>`, módulo de feature. O achado propõe esse lugar.

## Calibração de confiança

- alta: li as duas pontas da aresta, citei as linhas e confirmei a regra (README, lint, estrutura).
- media: a aresta viola a regra universal, e a arquitetura declarada não cobre o caso. Ou o dano depende de um consumidor que o diff não mostra.
- baixa: suspeita de ciclo ou de papel de repo sem o caminho completo. Diga o que confirmaria (rodar `madge`, abrir o README do serviço vizinho).
