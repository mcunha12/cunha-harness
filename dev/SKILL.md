---
name: dev
description: Pipeline de desenvolvimento ponta a ponta, do pedido ao MR, com estado salvo para pausar e retomar. Use com /dev <pedido>, /dev, /dev stop, /dev resume <feature> [instrução], ou quando o Marcelo pedir para desenvolver uma feature a partir de um prompt, link do Jira, link do Notion ou arquivo.
argument-hint: "[<pedido> | stop | resume <feature> [instrução]]"
model: opus
---

# /dev

A sessão principal é o orquestrador. Ela guarda estado, chama os scripts e dispara os agentes. O conteúdo de cada passo vive em arquivo.

## 1. Comandos

| Comando | Efeito |
|---|---|
| `/dev <pedido>` | Fase 1 (requisitos) para todas as features do pedido, depois a primeira feature. |
| `/dev` | Lista as features em `~/.claude/dev/features/`: fase, repos, último checkpoint. |
| `/dev stop` | Para a feature ativa com segurança. Ver `references/pause-resume.md`. |
| `/dev resume <feature> [instrução]` | Retoma. Com instrução, replaneja antes. Ver `references/pause-resume.md`. |

## 2. Regras invioláveis

1. Tudo do `~/.claude/CLAUDE.md` vale aqui e em todo subagent: STE Operacional, comentário one-liner, testes só dos arquivos alterados com workers limitados, releitura antes de escrever em arquivo que outra pessoa ou sessão pode ter tocado. Todo prompt de UI carrega as regras de UI (headless no `agent-browser`, iPhone SE 375×667 primeiro, tablet 768×1024 depois, desktop 1280×720 por último, fluxo real de cliques, print conferido).
2. Nada em `main` ou `master`: commit, push e merge só em branch de feature ou de task.
3. Só a sessão principal dispara agentes. Subagent não dispara subagent.
4. Todo agente grava a saída no arquivo indicado e devolve só o caminho e até 5 linhas de resumo.
5. Todo estado passa por `scripts/devstate.py`. Nunca edite `state.json` à mão.
6. Todo comando pesado passa por `scripts/heavy_lock.sh`, com 1 slot por tipo na máquina inteira: `--kind build` (type-check, lint, testes, build, `npm install`) e `--kind qa` (build de produção do QA, servidor do app e navegador headless). Sem `--kind`, o tipo é `build`.
7. Push e abertura de MR pedem confirmação do Marcelo.
8. Ao Marcelo vão só os marcos: task `done` ou `blocked`, gate com status novo, decisão que muda o quê, pedido de confirmação. Notificação de especialista ou de passo não vira mensagem: ela vai para o estado e para o tracker.
9. O orquestrador manda no andamento. Ele nunca devolve "rode /dev resume" ao Marcelo: a feature na fila começa sozinha quando a que ela espera fecha. Decisão de como fazer (layout, nome de componente, ordem de tasks) é dele e vai ao Marcelo em uma linha, sem pedir confirmação. Ao Marcelo vai só o que muda o quê (escopo, regra de negócio, dado).
10. Uma feature por vez, com o máximo de subagents em paralelo dentro dela (26/10/2026). Nenhum agente trabalha para outra feature enquanto a ativa não fecha, nem leitura ou preparo de retomada: a fila só anda quando a ativa chega a `done`. Dentro da feature ativa, todo trabalho sem dependência aberta sai na mesma mensagem: passos de tasks diferentes, prints de antes na base enquanto a task implementa, scan dos especialistas, descrição do PR, seed para teste manual. O modelo de cada agente segue a seção 5. O número de workers de task sai do `scripts/capacity.py` (seção 4). Agente que só lê, mede ou escreve fora do repo não ocupa worker.
11. Sem review por task e sem gate intermediário (07/11/2026). A única review é o gate final: /master-review full com QA, depois de todas as tasks e dos testes finais.
12. Testes só no fim da feature (07/11/2026): depois de todas as tasks, antes do gate final. Entra só teste com veredito "Behavior" na tabela da /test-audit. No /dev, esta regra substitui o Mode A da /test-audit e o item da code-guard que pede testes antes do código.

## 3. Fluxo

1. Fase 1, requisitos: `references/phase-1-requirements.md`.
2. Fase 2, plano: `references/phase-2-planning.md`.
3. Fase 3, execução: `references/phase-3-execution.md`. Ela fecha com os testes finais e o gate final com QA.

Uma feature por vez, do começo ao fim. As outras ficam na fila com a spec pronta.

Fila entre features, inclusive de outra sessão:

1. `devstate.py wait <dir> <dir da feature esperada>` grava a espera.
2. Dispare em background: `until python3 ~/.claude/skills/dev/scripts/devstate.py ready <dir>; do sleep 300; done`.
3. Quando o loop sair, comece a Fase 2 da feature na hora, sem perguntar.

## 4. Loop do orquestrador (Fase 3)

```
enquanto o gate final não passou:
    capacidade = capacity.py → workers
    livres = capacidade - workers ocupados
    devgraph.py next plan.json state.json --free <livres>   → lista de assignments
    para cada merge: merge na branch da feature, devstate.py task-status <dir> <task> done, git worktree remove
    para cada outro assignment: devstate.py worker <dir> <slot> '<assignment>' e dispare em background
    ao receber a notificação de um agente:
        devstate.py step-done / task-status / gate-status conforme o resultado
        devstate.py cost <dir> '{"agent_role": ..., "model": ..., "task": ..., "tokens": ..., "duration_ms": ...}'
        devstate.py worker <dir> <slot> null
        volte ao topo
```

`python3 ~/.claude/skills/dev/scripts/capacity.py` devolve `{"workers", "cores", "mem_free_gb", "limited_by"}`. A conta: núcleos menos 2 (slots de build e de QA), limitada pela memória livre menos 2 GB a 0,25 GB por worker, com piso de 1. Rode a cada volta do loop: a conta acompanha a carga da máquina e das outras sessões. Ela limita só o próximo disparo; worker que já roda segue até o fim. O slot de worker nasce em `state.json` no primeiro uso.

Nenhum slot fica livre enquanto `next` devolver trabalho e a capacidade permitir. Cada `devstate.py` regrava o `tracker.html`.

Marcos (task `done` ou `blocked`, gate com status novo, pausa, retomada, fim da feature): dispare em background um agente `model: "haiku"`, `effort: "medium"` com `prompts/situation.md`. Ele grava `situation.json` e o bloco "Situação agora" aparece no topo do tracker. Esse agente não ocupa worker. O resto da página continua com o script, sem token.

## 5. Modelos e esforço

Padrão: plano e review em Opus 5.5 `xhigh`; todo o resto em Haiku 5.5 `medium`. O Opus pode subir uma tarefa de Haiku para Sonnet `medium` quando julgar necessário: lógica nova não trivial, 5 ou mais regras de negócio, ou falha repetida no Haiku. Toda subida vira decisão em `decisions.jsonl` com o motivo (`origin: "agendador"`) e vai no assignment como `"model": "sonnet"`.

| Passo | Agent tool |
|---|---|
| 1 Escopo (só complexidade 4 e 5) | `model: "opus"`, `effort: "xhigh"`, prompt `prompts/step-1-scope.md` |
| 2 Leitura | swarm de até 3 agentes `model: "haiku"`, `effort: "medium"`, prompt `prompts/step-2-reading.md` |
| 3 Avaliação | `model: "opus"`, `effort: "xhigh"`, prompt `prompts/step-3-evaluation.md`. Em complexidade até 3 ele também grava o `scope.md`. Ele escolhe o modelo do passo 5 |
| 5 Implementação | `model: "haiku"`, `effort: "medium"`; `model: "sonnet"`, `effort: "medium"` quando o passo 3 escolher. Prompt `prompts/step-5-implementation.md` |
| Testes finais | um agente por repo, `model: "haiku"`, `effort: "medium"`, ou Sonnet `medium` por decisão do orquestrador. Prompt `prompts/final-tests.md` |
| Gate final | Skill `master-review` full com `--base <base> --spec <dir>/spec.md`, uma por repo, na sessão principal. A verificação de BLOCKER e MAJOR é do orquestrador (Opus). Scan e correção em Haiku `medium`; o orquestrador sobe para Sonnet `medium` o lote de correção que pedir. Roast, UX e Spec seguem em Sonnet `medium`, escolha da própria master-review |
| Situação e retro | `model: "haiku"`, `effort: "medium"` |

`subagent_type: "general-purpose"` e `run_in_background: true` em todos.

## 6. Arquivos

| Caminho | Conteúdo |
|---|---|
| `references/state-layout.md` | pastas, schemas de `plan.json`, `state.json`, logs e `run.json` |
| `references/pause-resume.md` | `/dev stop` e `/dev resume` |
| `references/phase-*.md` | as três fases |
| `prompts/step-*.md` | prompts dos passos 1, 2, 3 e 5 |
| `prompts/final-tests.md` | testes finais de um repo, com os critérios da /test-audit |
| `prompts/retro.md` | retro do fim da feature |
| `prompts/situation.md` | bloco "Situação agora" do tracker, só nos marcos |
| `scripts/devgraph.py` | `validate`, `analyze`, `next` |
| `scripts/devstate.py` | estado atômico, checkpoints, logs, hash de leitura |
| `scripts/capacity.py` | número de workers de task pelos núcleos e pela memória livre |
| `scripts/fixture_pii.py` | barra dado pessoal em teste e fixture do diff (e-mail de provedor público, cidade/UF real, nome com sobrenome, telefone fora da faixa fictícia) |
| `scripts/heavy_lock.sh` | trava global de processo pesado: 1 slot de `build` e 1 de `qa` |
| `scripts/render_tracker.py` | `tracker.html` a partir do estado |
| `scripts/tracker_server.py` | servidor local do tracker em `http://localhost:4777` (porta em `DEV_TRACKER_PORT`), atualização ao vivo |

Caminho dos scripts depois do install: `~/.claude/skills/dev/scripts/`.
