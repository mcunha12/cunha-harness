---
name: dev
description: Pipeline de desenvolvimento ponta a ponta. Requisitos com perguntas, quebra em tasks com grafo de dependências e clusters de afinidade (MST), execução com até 4 workers (Opus escopo e avaliação, Haiku leitura, Sonnet testes e implementação), review lean por task ou cluster e full nos gates, estado salvo para pausar e retomar. Use com /dev <pedido>, /dev, /dev stop, /dev resume <feature> [instrução], ou quando o Marcelo pedir para desenvolver uma feature a partir de um prompt, link do Jira, link do Notion ou arquivo.
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

1. Tudo do `~/.claude/CLAUDE.md` vale aqui e em todo subagent: STE Operacional, comentário one-liner, testes só dos arquivos alterados com workers limitados, /test-audit antes de mudar comportamento, releitura antes de escrever em arquivo que outra pessoa ou sessão pode ter tocado. Todo prompt de UI carrega as regras de UI (headless, iPhone SE 375×667 primeiro, desktop 1440×900 depois, fluxo real de cliques, print conferido).
2. Nada em `main` ou `master`: commit, push e merge só em branch de feature ou de task.
3. Só a sessão principal dispara agentes. Subagent não dispara subagent.
4. Todo agente grava a saída no arquivo indicado e devolve só o caminho e até 5 linhas de resumo.
5. Todo estado passa por `scripts/devstate.py`. Nunca edite `state.json` à mão.
6. Todo comando pesado (`tsc`, testes, build, navegador, `npm install`) passa por `scripts/heavy_lock.sh`.
7. Push e abertura de MR pedem confirmação do Marcelo.

## 3. Fluxo

1. Fase 1, requisitos: `references/phase-1-requirements.md`.
2. Fase 2, plano: `references/phase-2-planning.md`.
3. Fase 3, execução: `references/phase-3-execution.md`.

Uma feature por vez, do começo ao fim. As outras ficam na fila com a spec pronta.

## 4. Loop do orquestrador (Fase 3)

```
enquanto o gate final não passou:
    livres = 4 - workers ocupados
    devgraph.py next plan.json state.json --free <livres>   → lista de assignments
    para cada assignment: devstate.py worker <dir> <slot> '<assignment>' e dispare em background
    ao receber a notificação de um agente:
        devstate.py step-done / task-status / gate-status conforme o resultado
        devstate.py cost <dir> '{"agent_role": ..., "model": ..., "task": ..., "tokens": ..., "duration_ms": ...}'
        devstate.py worker <dir> <slot> null
        volte ao topo
```

Nenhum slot fica livre enquanto `next` devolver trabalho. Cada `devstate.py` regrava o `tracker.html`.

Marcos (task `done` ou `blocked`, gate com status novo, pausa, retomada, fim da feature): dispare em background um agente `model: "haiku"`, `effort: "medium"` com `prompts/situation.md`. Ele grava `situation.json` e o bloco "Situação agora" aparece no topo do tracker. Esse agente não ocupa worker. O resto da página continua com o script, sem token.

## 5. Modelos e esforço

| Passo | Agent tool |
|---|---|
| 1 Escopo | `model: "opus"`, `effort: "xhigh"`, prompt `prompts/step-1-scope.md` |
| 2 Leitura | swarm de até 3 agentes `model: "haiku"`, `effort: "medium"`, prompt `prompts/step-2-reading.md` |
| 3 Avaliação | `model: "opus"`, `effort: "xhigh"`, prompt `prompts/step-3-evaluation.md` |
| 4 Testes | `model: "sonnet"`, `effort: "medium"`, prompt `prompts/step-4-tests.md` |
| 5 Implementação | `model: "sonnet"`, `effort: "medium"`, prompt `prompts/step-5-implementation.md` |
| 6 Review lean | Skill `master-review` com `--lean --base <branch da feature> --spec <dir>/spec.md [--roast]` |
| Gate | Skill `master-review` full com `--base <base> --spec <dir>/spec.md`, uma por repo |

`subagent_type: "general-purpose"` e `run_in_background: true` em todos.

## 6. Arquivos

| Caminho | Conteúdo |
|---|---|
| `references/state-layout.md` | pastas, schemas de `plan.json`, `state.json`, logs e `run.json` |
| `references/pause-resume.md` | `/dev stop` e `/dev resume` |
| `references/phase-*.md` | as três fases |
| `prompts/step-*.md` | prompts dos passos 1 a 5 |
| `prompts/retro.md` | retro do fim da feature (Haiku medium) |
| `prompts/situation.md` | bloco "Situação agora" do tracker (Haiku medium, só nos marcos) |
| `scripts/devgraph.py` | `validate`, `analyze`, `next` |
| `scripts/devstate.py` | estado atômico, checkpoints, logs, hash de leitura |
| `scripts/heavy_lock.sh` | trava global de 2 processos pesados (`DEV_HEAVY_SLOTS`) |
| `scripts/render_tracker.py` | `tracker.html` a partir do estado |
| `scripts/tracker_server.py` | servidor local do tracker em `http://localhost:4777` (porta em `DEV_TRACKER_PORT`), atualização ao vivo |

Caminho dos scripts depois do install: `~/.claude/skills/dev/scripts/`.
