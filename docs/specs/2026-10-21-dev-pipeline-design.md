# /dev — pipeline de desenvolvimento

Data: 21/10/2026. Autor do pedido: Marcelo Cunha. Status: design para aprovação.

## 1. Intenção

O /dev leva uma feature do pedido ao MR com a maior velocidade, o menor gasto de tokens e a mesma qualidade de hoje ou maior. O Marcelo entrega o pedido (prompt, link do Jira, link do Notion, `.txt`, imagem). O /dev investiga, pergunta o que falta, quebra em tasks, monta o grafo, executa com até 4 workers e revisa em pontos definidos.

Quatro peças saem deste design:

| Peça | O que é | Estado hoje |
|---|---|---|
| `dev` | orquestrador do pipeline | nova |
| `master-review` | swarm de review pós-código | existe; ganha `--lean`, roast, ux, arquitetura e log de achados |
| `code-guard` | a master-review como diretriz de escrita, usada durante a implementação | nova |
| `review-roast`, `review-ux`, `review-arquitetura` | especialistas novos da master-review | novos |

## 2. Objetivos, não-objetivos, anti-objetivos

Objetivos:

- Uma feature por vez, do começo ao fim. 4 workers sempre progredindo nela.
- O Marcelo responde todas as perguntas de requisito de uma vez, no começo. Depois disso a execução não para para perguntar, salvo bloqueio real.
- Parar uma feature no meio e retomar depois, com rapidez e baixo risco, inclusive em outra sessão.
- Um HTML por feature com tasks, grafo, gates, decisões, aprendizado e custo, atualizado a cada passo.
- Erros que se repetem viram regra na `code-guard` sem intervenção do Marcelo.

Não-objetivos:

- Executar duas features em paralelo.
- Deploy. O /dev termina no MR.
- Substituir a skill da empresa (`vibecode-<empresa>`). Ela continua dona das regras da empresa.

Anti-objetivos (falha mesmo que funcione):

- Travar o PC do Marcelo.
- Reverter edição do Marcelo ou de outra sessão.
- Commit, push ou merge em `main`/`master`.
- Branch da feature quebrada depois de uma pausa.
- A `code-guard` inchar a ponto de cada implementador gastar mais tokens do que a review economiza.

## 3. Restrições

- Todas as regras do `~/.claude/CLAUDE.md` valem dentro do pipeline e em todo subagent: STE Operacional, comentários one-liner, testes só dos arquivos alterados com `--maxWorkers=2`, /test-audit antes de mudar comportamento, UI em navegador headless no iPhone SE (375×667) e depois desktop (1440×900), releitura antes de todo write.
- Modelos e esforço por papel, fixados pelo Marcelo: escopo e avaliação em Opus 5.5 xhigh, leitura de código em Haiku 5.5 medium, implementação em Sonnet 5.5 medium.
- No máximo 4 workers.
- Repositório das skills: `github.com/mcunha12/cunha-harness`, uma pasta por skill.
- `dev` e `master-review` não têm `disable-model-invocation`. O /dev invoca a master-review pelo Skill tool, com as flags.
- O desenho assume que só a sessão principal dispara agentes. O /dev encadeia os passos de cada task a partir da sessão principal. O construtor confirma essa limitação no Claude Code atual.

## 4. Comandos

| Comando | Efeito |
|---|---|
| `/dev <pedido>` | Inicia: requisitos de todas as features do pedido, depois a primeira feature. |
| `/dev` | Lista as features: em andamento, paradas, na fila, concluídas, com os repos de cada uma. |
| `/dev stop` | Para a feature ativa com segurança (seção 9). |
| `/dev resume <feature>` | Retoma uma feature parada (seção 9). |

## 5. Fase 1 — Requisitos (todas as features do pedido)

1. Entrada. O orquestrador (Opus xhigh) lê todas as fontes: Jira e Notion pelos conectores, arquivo e imagem pelo Read. Link citado dentro de uma fonte é seguido até 1 nível.
2. Recon em paralelo. Enquanto o Opus lê, um swarm Haiku mapeia onde o pedido toca no código: módulos, rotas, telas, testes existentes.
3. Divisão em features. Uma feature pode cruzar repos (BFF + web, por exemplo). Critério: 1 feature = 1 branch com o mesmo nome em cada repo que ela toca = 1 MR por repo. O orquestrador mostra a divisão. O Marcelo confirma e escolhe a ordem. Dependência entre features (B usa o endpoint que A cria) aparece aqui e informa a ordem.
4. Perguntas. Só o que fontes e código não respondem. Rodadas de até 4 perguntas pelo AskUserQuestion, opção recomendada primeiro. Entra nas perguntas o acesso a dado real para os testes (a /test-audit exige registro real anonimizado), para a execução não travar depois.
5. Saída por feature: `spec.md` com histórias, critérios de aceite, fora do escopo e decisões. Cada decisão registra a origem: fonte, código ou resposta do Marcelo. A spec serve também de spec do modo A da /test-audit.

## 6. Fase 2 — Plano da feature (quando ela começa)

A camada de código do plano roda só quando a feature começa, porque ela envelhece com o código.

### 6.1 Revalidação

O orquestrador cruza os arquivos que as features anteriores alteraram com os arquivos do recon desta feature. Com interseção, as decisões da spec que dependem desses arquivos voltam ao Marcelo para confirmação. Sem interseção, o plano segue direto.

### 6.2 Quebra em tasks

Cada task tem:

| Campo | Conteúdo |
|---|---|
| `id`, `title` | `T1`, título curto |
| `description` | o que entregar |
| `done_when` | critério de pronto observável |
| `files_hint` | arquivos e módulos previstos |
| `read_list` | o que o swarm Haiku lê no passo 2 |
| `complexity` | 1 a 5 (rubrica abaixo) |
| `risk` | 1 a 5 (rubrica abaixo) |
| `repo` | repo onde a task roda; uma task toca um repo só |
| `depends_on` | ids das tasks que precisam estar concluídas, de qualquer repo da feature |
| `changes_behavior` | sim/não; sim dispara o modo A da /test-audit |
| `has_ui` | sim/não; sim dispara revisão visual e `review-ux` |

Complexidade:

| Nota | Critério |
|---|---|
| 1 | 1 arquivo, mudança local |
| 2 | 2 a 3 arquivos no mesmo módulo |
| 3 | 4 a 8 arquivos ou 2 módulos |
| 4 | 9 a 15 arquivos, 3+ módulos ou lógica nova não trivial |
| 5 | mais de 15 arquivos ou mudança transversal |

Risco:

| Nota | Critério |
|---|---|
| 1 | copy, estilo, sem lógica |
| 2 | UI com lógica local |
| 3 | regra de negócio coberta por teste existente |
| 4 | contrato entre serviços, autenticação, dinheiro, dado de aluno |
| 5 | migration de schema, dado irreversível, segurança |

Risco 4 ou 5 = risco alto.

### 6.3 Grafo de dependências (com direção)

- Nó = task ou gate. Aresta A → B = B depende de A.
- Ciclo é erro de planejamento. O orquestrador refaz a quebra. Se o ciclo persistir, ele leva o caso ao Marcelo.
- `custo = complexity × risk`.
- `caminho_à_frente(t) = custo(t) + max(caminho_à_frente(dependentes de t))`. Gate tem custo 0.
- O caminho crítico é a cadeia de maior `caminho_à_frente` a partir das raízes.

### 6.4 Grafo de afinidade e clusters (MST)

- Grafo sem direção entre todas as tasks. Peso da aresta = distância de contexto: `1 − |arquivos em comum| / |arquivos da união|` sobre `files_hint`. Empate se desfaz por módulo e camada.
- O orquestrador monta a MST, corta as arestas com distância ≥ 0,8 e obtém os clusters. Cluster tem no máximo 4 tasks. O limiar e o teto ficam configuráveis.
- Os clusters decidem três coisas: lote de review lean, lugar dos gates e afinidade de worker. Eles nunca passam por cima de uma dependência.
- Tasks de repos diferentes têm distância 1 e nunca dividem cluster.

### 6.5 Gates

Gate é um nó do grafo. Ele espera um conjunto de tasks e segura as que vêm depois. No gate roda a /master-review full. Regras de colocação:

1. Sempre há um gate final, depois da última task.
1b. Em feature com vários repos, o gate roda uma /master-review full por repo, com os outros repos da feature em `related_repos`. O gate passa quando todas passam. Contrato entre repos (endpoint do BFF consumido pelo web) cai na regra 2.
2. Gate depois do conjunto de tasks que congela um contrato (API, schema, evento, tipo compartilhado) consumido por task de outro cluster.
3. No máximo 6 tasks entre dois gates, para limitar o escopo da review full.
4. O gate entra no fechamento de cluster sempre que isso não contraria as regras 2 e 3.

O gate passa quando a review full termina sem BLOCKER e sem MAJOR, depois da correção. Achado que vira task manual bloqueia o gate e vai para o Marcelo.

### 6.6 Plano publicado

O plano vai para `plan.json` e para o HTML. A execução começa sem esperar aprovação. O Marcelo corrige o plano com `/dev stop`, ajuste e `/dev resume`.

## 7. Fase 3 — Execução

### 7.1 Worker e processos pesados

- Worker = vaga de pipeline em andamento. No máximo 4. Um swarm Haiku, uma review lean ou uma review full ocupam 1 worker cada.
- Processo pesado (`tsc`, testes, build, navegador headless, `npm install`) tem limite global de 2 simultâneos, somando todos os workers. Um script de trava (semáforo em arquivo) faz cumprir. Worker sem vaga espera na fila.
- Se o PC ainda travar, o ajuste é baixar o limite de processos pesados para 1. Os 4 workers continuam.

### 7.2 Agendador

A cada worker livre, o orquestrador preenche nesta ordem:

1. Task pronta (dependências concluídas) para os passos 3 a 6, pela maior `caminho_à_frente`. Empate: a task do mesmo cluster que o worker acabou de fazer, para reaproveitar contexto.
2. Review lean ou gate pendente.
3. Passos 1 e 2 de task futura (dependências ainda abertas), pela maior `caminho_à_frente`. A leitura antecipada vale só para task sem arquivo em comum com task em andamento. As outras recebem o diff quando a dependência fechar.

Nenhum worker fica parado enquanto houver trabalho em qualquer uma das três filas.

### 7.3 Pipeline de uma task

| Passo | Papel | Modelo | Saída em `tasks/<id>/` |
|---|---|---|---|
| 1 Escopo | fecha entrega e critério de pronto | Opus 5.5 xhigh | `scope.md` |
| 2 Leitura | lê `read_list` e devolve fatos com `arquivo:linha` | swarm Haiku 5.5 medium, até 3 agentes | `reading.md` |
| 3 Avaliação | decide arquivos, mudança por arquivo, casos de teste, comandos de verificação | Opus 5.5 xhigh | `plan.md` |
| 4 Testes | modo A da /test-audit: spec, testes de integração/E2E com dado real anonimizado, vermelho pelo motivo certo, commit | Sonnet 5.5 medium | commit `test:` |
| 5 Implementação | implementa até o verde, com a `code-guard` carregada | Sonnet 5.5 medium | commits `feat:`/`fix:` + `result.json` |
| 6 Review | /master-review lean (seção 7.4) | ver seção 10 | `reviews/<id>.md` |

- Passos 1 e 2 rodam em paralelo.
- Task com `changes_behavior = não` pula o passo 4.
- No passo 5 o Sonnet carrega o núcleo da `code-guard`, os arquivos de domínio pelo roteamento, o `CLAUDE.md` do repo e, em repo da empresa, a skill da empresa. Em conflito, a skill da empresa vence.
- Todo agente grava a saída em arquivo e devolve à sessão principal só o caminho e um resumo de até 5 linhas. A sessão principal guarda estado, não conteúdo.
- Falha: o Sonnet não fecha o verde em 2 tentativas → o Opus refaz o passo 3 uma vez → nova falha marca a task como "bloqueada: precisa do Marcelo". O HTML mostra o bloqueio. Os workers seguem nas outras tasks.
- Review lean com MAJOR que os fixers não resolveram: a task não entra na branch da feature e fica "bloqueada: precisa do Marcelo".
- Task com `has_ui = sim` só passa na review com a revisão visual feita. Sem ela, a task fica bloqueada. O `~/.claude/CLAUDE.md` exige print de toda tela alterada. A Fase 1 coleta, por repo, o que a revisão visual precisa: comando para subir o app, URL, login de teste e backend usado. Fica em `~/.claude/dev/repos/<repo>/run.json` e é reaproveitado nas features seguintes. Task de web que depende de task de BFF sobe o BFF a partir da branch da feature.

### 7.4 Review lean e branches

- Cada task roda numa git worktree própria, no repo dela, numa branch filha da branch da feature naquele repo.
- Task de risco alto: review lean logo depois do passo 5, só no diff dela.
- Task de risco baixo ou médio: entra no lote do cluster. A review lean roda quando todas as tasks do cluster terminam o passo 5, no diff combinado.
- Dentro do mesmo cluster, a task dependente se empilha na branch da dependência, ainda sem review. É aqui que o lote economiza: a review não lê código que a task seguinte reescreveu.
- Entre clusters, a task dependente só começa o passo 3 depois que a dependência passou pela review e entrou na branch da feature.
- Se uma dependência à espera do lote bloqueia uma task pronta, a review do cluster roda já, com as tasks que terminaram. O lote nunca segura o caminho crítico.
- A branch da feature só recebe task revisada. Os fixers da master-review editam o working tree. O orquestrador do /dev commita as correções (`fix(review):`) na branch da task ou do lote.
- Worktree nova reaproveita o `node_modules` da branch da feature quando a task não mexe em `package.json`.

### 7.5 Fim da feature

1. Gate final passa.
2. Modo B da /test-audit no diff da feature.
3. O orquestrador mostra o resumo e pede confirmação para push da branch da feature e abertura de 1 MR por repo. Cada MR cita os outros e a ordem de deploy (quem fornece o contrato sobe primeiro). Nunca em `main`.
4. A próxima feature da fila começa sem esperar essa confirmação. Ela parte da base, ou da branch da feature de que depende.

## 8. Estado em arquivo

```
~/.claude/dev/features/<feature-slug>/
  state.json        # fonte da verdade: fase, repos, status de cada task e passo, workers, gates, custos
  spec.md
  plan.json         # tasks, arestas, clusters, gates, custos, caminho crítico
  decisions.jsonl   # uma decisão por linha, com origem
  costs.jsonl       # um registro por agente: papel, modelo, task, tokens ou duração
  tasks/<id>/scope.md, reading.md, plan.md, result.json
  reviews/<id>.md
  tracker.html
```

- Escrita atômica: arquivo temporário e rename.
- O /dev nunca depende da memória da conversa. Uma sessão nova retoma só pelos arquivos.
- `reading.md` guarda o hash de cada arquivo lido, para a retomada saber se a leitura ficou velha.

## 9. Pausa e retomada

`/dev stop`:

- Passos 1, 2, 3 e review só leem. O orquestrador corta na hora e o passo recomeça na retomada.
- Passos 4 e 5 editam código. O orquestrador faz commit `wip:` na branch da task, remove as worktrees e mantém as branches.
- O `state.json` registra o ponto exato e o motivo.

`/dev resume <feature> [instrução]`:

0. Com instrução em linguagem natural ("tira o T7", "junta T2 e T3", "gate depois do T5"), o orquestrador altera o `plan.json`, valida (sem ciclo, toda dependência existe), recalcula caminho crítico, clusters e gates e mostra a diferença. Task concluída que a mudança toca volta para o passo 3. Task com `wip:` que a mudança toca: o Opus decide se aproveita o diff.
1. A base andou: merge da base na branch da feature e nova rodada dos testes das tasks concluídas.
2. Hash de arquivo lido mudou: a leitura daquela task é refeita.
3. Existe commit `wip:`: o Opus lê o diff e decide se continua ou descarta.
4. Worktrees recriadas, workers retomam pelo agendador.

## 10. master-review: mudanças

### 10.1 `--lean`

- Piso MAJOR no scan, no relatório e na correção. Os especialistas recebem a instrução de devolver só BLOCKER e MAJOR, para gastar menos tokens.
- Roteamento igual ao da full.
- Roast só com `--roast`. O /dev passa `--roast` nas tasks de risco alto.
- Diff com UI: revisão visual e `review-ux` só no iPhone SE. Desktop fica para a full.
- Relatório curto: veredito, achados, correção.

### 10.2 Full

O comportamento atual, mais roast, ux e arquitetura quando o roteamento se aplica. Roda nos gates e na /master-review avulsa.

### 10.3 `review-roast` (prefixo ROAST)

- Revisor externo muito crítico. Recebe só o diff e a spec, sem as convenções do repo.
- Julga negativamente o máximo de pontos possível. Toda crítica traz trecho exato, motivo e consequência. Crítica sem motivo é descartada.
- Sem teto de achados.
- O orquestrador verifica BLOCKER e MAJOR como de qualquer especialista e descarta crítica que contradiz convenção documentada. Achado igual ao de outro especialista vira co-assinatura e sobe a confiança.
- Modelo: Sonnet 5.5 medium.
- Seção própria no relatório.
- Roda na full e na lean de task de risco alto. Não entra na `code-guard`.

### 10.4 `review-ux` (prefixo UX)

- Roda quando o diff tem UI. Entrada: prints do fluxo real de cliques capturados no passo 8b (iPhone SE primeiro, depois desktop), o diff e o job to be done da spec.
- Lente "Caminho A→B". Cada achado diz quanto ele aumenta o caminho do usuário até o job to be done: passos, decisões ou itens a lembrar a mais.

| # | Dimensão | Fontes |
|---|---|---|
| 1 | Caminho: passos, decisões e campos até concluir o job | job to be done |
| 2 | Estado e feedback | Nielsen 1; Shneiderman 3 e 4; Norman (feedback) |
| 3 | Modelo mental e mapeamento | Nielsen 2; Norman (modelo conceitual, mapeamento) |
| 4 | Sinalização: o clicável parece clicável | Norman (affordance, signifiers) |
| 5 | Consistência | Nielsen 4; Shneiderman 1 |
| 6 | Erro: prevenir, restringir, recuperar | Nielsen 5 e 9; Shneiderman 5; Norman (restrições) |
| 7 | Memória: reconhecer em vez de lembrar, ajuda no contexto | Nielsen 6 e 10; Shneiderman 8 |
| 8 | Controle e reversão | Nielsen 3; Shneiderman 6 e 7 |
| 9 | Foco e eficiência | Nielsen 7 e 8; Shneiderman 2 |
| 10 | Mobile: tela pequena, polegar, digitação mínima, interrupção, rede ruim | Joyce e Lilley |

- WCAG 2.2 (POUR) continua com a `review-a11y`. A `review-ux` só faz referência.
- Limite: a lista exata de heurísticas de Joyce e Lilley não foi conferida. O construtor confirma na fonte antes de fechar a dimensão 10.
- Modelo: Sonnet 5.5 medium, porque o trabalho depende de ler prints.

### 10.5 `review-arquitetura` (prefixo ARQ)

- Dono de: conformidade com o repo (como o repo já resolve o mesmo tipo de problema em outro lugar), escalabilidade (mais dados, mais carga, mais features), dependência ou padrão novo que pede ADR, tamanho da solução frente ao problema.
- A `review-modularidade` continua dona de camadas, fronteiras e ciclos. A ownership matrix ganha as linhas da divisão.
- Roda quando há arquivo ou módulo novo, dependência nova, padrão novo, mudança de fluxo de dados ou mais de ~10 arquivos.
- Modelo: Haiku 5.5, como os outros especialistas. O orquestrador verifica os MAJOR.

### 10.6 Emulação do iPhone SE

O Chrome headless não abre janela com menos de 500 px: um print com `--window-size=375,...` sai como layout de 500 px cortado. A revisão visual emula o aparelho pelo protocolo do Chrome (`Emulation.setDeviceMetricsOverride`: 375×667, DPR 2, toque, mobile). A regra vale para a master-review, para a `code-guard` e para os subagents de UI.

### 10.7 Log de achados

Todo BLOCKER e MAJOR confirmado, de qualquer review (lean, full, avulsa), entra em `~/.claude/code-guard/ledger.jsonl`: data, repo, feature, task, especialista, categoria, arquivo, problema em uma linha, regra da `code-guard` que cobria (ou nenhuma), se o arquivo de domínio carregou.

## 11. code-guard

### 11.1 Conteúdo

- Fonte: os especialistas `review-*`. Cada regra de detecção vira diretriz de escrita.
- Entram só as regras que geram BLOCKER ou MAJOR.
- Núcleo curto, sempre carregado: segurança, legibilidade, clean, dry, comentários, tipagem, e a regra "antes de criar um padrão, procure o equivalente no repo".
- Um arquivo por domínio, carregado pela tabela de roteamento da master-review: front, a11y, ux, queries, migrations, contratos, resiliência, observabilidade, ia, modularidade, arquitetura.
- Agnóstica: sem empresa, design system ou ferramenta. Da skill da empresa entram só os aprendizados que valem em qualquer codebase (ternário aninhado, arquivo acima de 200 linhas, nome na língua do negócio, campo de DTO renomeado como breaking change, nome de rota igual à chave usada).
- Cada regra aponta o especialista de origem e a categoria.
- Orçamento: núcleo com até 150 linhas, cada arquivo de domínio com até 120, cada arquivo `learned/` com até 80. Arquivo acima do teto passa por consolidação: regras parecidas viram uma só. A consolidação nunca remove regra de categoria que gera BLOCKER.
- `ux.md`: antes de escrever a tela, o implementador escreve o job to be done e o caminho A→B e conta os passos. A tela é feita primeiro para 375 px.

### 11.2 Ciclo de aprendizado

- Identidade do erro: especialista + categoria.
- Gatilho: 3 ocorrências da mesma identidade no ledger, em pelo menos 2 tasks diferentes. Configurável.
- Com o gatilho:
  1. Sem regra: cria a regra, com o erro real como exemplo.
  2. Regra existe, arquivo de domínio não carregou: corrige o roteamento.
  3. Regra existe e carregou: reescreve a regra mais concreta, com as ocorrências reais como exemplo.
- Antes de criar, procura regra parecida e reescreve em vez de duplicar.
- Destino: genérica → `learned/global.md`; de uma empresa → `learned/company-<nome>.md`; de um repo só → `learned/repo-<nome>.md`.
- A atualização é automática. Toda regra nova ou reescrita aparece nas decisões do HTML da feature, com o achado de origem.
- Regra aprendida não edita arquivo versionado. Ela vai para `~/.claude/code-guard/learned/`: `global.md`, `company-<nome>.md` ou `repo-<nome>.md`. A `code-guard` carrega esses arquivos junto com os dela, pelo contexto da task. Regra reescrita substitui a original pela categoria. Assim a regra vale na hora, sem branch, sem merge e sem entrar no MR do time.
- A skill da empresa não tem git. Regra da empresa fica em `learned/company-<empresa>.md`, carregado em repo da empresa.
- Promover regras aprendidas para os arquivos versionados da `code-guard` é tarefa manual do Marcelo.

## 12. HTML da feature

- Mockup aprovado: `docs/specs/2026-10-21-dev-tracker-mockup.html`.
- Seções, de cima para baixo: cabeçalho (status, branch, fontes, checkpoint, comando de pausa), 4 números (tasks concluídas, workers ativos, processos pesados, gates), workers agora, grafo com gates, caminho crítico e clusters, tabela de tasks (card no celular), gates, decisões, aprendizado da `code-guard`, custo por modelo e por review.
- Um script determinístico gera o `tracker.html` a partir do `state.json` a cada checkpoint. Zero token por atualização.
- Nos marcos (task concluída ou bloqueada, gate, pausa, retomada, fim), um Haiku medium escreve o bloco "Situação agora" no topo: 3 a 5 linhas com o que avançou, o que travou e o que vem a seguir. Decisão do Marcelo, 21/10.
- A página se atualiza sozinha sem perder a rolagem.
- O /dev imprime o caminho do HTML no começo da feature. O Marcelo abre.
- Custo: se o Claude Code não expuser tokens por agente, o `costs.jsonl` registra contagem de agentes e duração, e o HTML diz que é aproximação.

## 13. Repositório `cunha-harness`

```
README.md
install.sh              # cria symlink de cada pasta em ~/.claude/skills/
dev/
master-review/
code-guard/
review-roast/
review-ux/
review-arquitetura/
review-a11y/  review-clean/  review-comentarios/  review-contratos/  review-dry/
review-front/  review-ia/  review-legibilidade/  review-migrations/  review-modularidade/
review-observabilidade/  review-queries/  review-resiliencia/  review-seguranca/  review-tipagem/
test-audit/
docs/specs/
```

- O repo é público. Todo conteúdo sobe anonimizado: nomes de repo, design system e empresa viram nomes genéricos (`web-app`, `api-bff`, design system externo). Antes de cada commit e do push, os termos de `~/.claude/overlays/forbidden-terms.txt` precisam voltar vazios.
- A regra continua, só o exemplo muda. Exemplo: "componente de design system externo com defeito vira handoff para o repo do DS" fica na `review-a11y`.
- O que só vale para a empresa sai dos `review-*` e vai para `~/.claude/overlays/<empresa>.md`, fora do repo. A master-review e a `code-guard` carregam esse arquivo quando o remote do git bate com `~/.claude/overlays/overlays.json`. Exemplo: o termo de domínio que a empresa usa para o usuário final.
- A skill da empresa fica fora do repo.

- Instalação por symlink: `~/.claude/skills/<skill> → ~/cunha-harness/<skill>`. Antes de trocar uma pasta existente por symlink, o `install.sh` faz backup em `~/.claude/skills-backup/<data>/` e confere que o conteúdo é igual.
- Branch de trabalho: `feat/dev-pipeline`. Nada vai para `main`.

## 14. Decisões tomadas por Claude (conferir)

1. MST só no grafo de afinidade. O "o que já pode começar" sai da ordenação topológica do grafo de dependências.
2. Prioridade pela maior `caminho_à_frente`.
3. Rubricas de complexidade e risco (seção 6.2) e `custo = complexidade × risco`.
4. Distância de afinidade por Jaccard de arquivos; corte em 0,8; cluster com até 4 tasks.
5. Regras de colocação de gate (seção 6.5), com no máximo 6 tasks entre gates.
6. Execução começa sem esperar aprovação do plano.
7. Worker = vaga de pipeline; processos pesados limitados a 2.
8. Passos 1 e 2 podem rodar antes das dependências fecharem; passo 3 em diante só depois.
9. Empilhamento de branch dentro do cluster; review antecipada quando o lote bloqueia task pronta.
10. Falha de implementação: 2 tentativas Sonnet, 1 reavaliação Opus, depois bloqueio para o Marcelo.
11. Push e MR pedem confirmação. A próxima feature começa sem esperar.
12. Lean: piso MAJOR, roast só em risco alto, visual só iPhone SE.
13. Roast e ux em Sonnet; arquitetura em Haiku.
14. Gatilho de aprendizado: 3 ocorrências em 2 tasks.
15. HTML local gerado por script, sem Artifact.
16. Regra aprendida vai para `~/.claude/code-guard/learned/`, fora de arquivo versionado.
17. Replanejamento por instrução em linguagem natural no `/dev resume`.
18. Revisão visual obrigatória em task com UI; sem ela a task bloqueia. Run config por repo coletada na Fase 1.
19. Orçamento de linhas da `code-guard` e consolidação quando estoura.
20. Feature com vários repos: uma task toca um repo só; gate roda uma full por repo; 1 MR por repo com a ordem de deploy.
21. Conteúdo da empresa retirado dos `review-*` vai para `~/.claude/overlays/<empresa>.md`, carregado por remote do git.

## 15. Deixado para o construtor

- Mecânica git de worktrees, empilhamento e integração de lote.
- Linguagem dos scripts (trava de processo pesado, render do HTML, escrita atômica).
- Mecanismo de auto-atualização do HTML.
- Tamanho do swarm Haiku por task, até 3.
- Implementação da emulação do iPhone SE pelo protocolo do Chrome.
- Formato exato de `state.json` e `plan.json`.
- Captura de tokens por agente, se o Claude Code expuser.
