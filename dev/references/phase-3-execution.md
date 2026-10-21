# Fase 3 — Execução

## 1. Agendador

`devgraph.py next` decide, nesta ordem:

1. task pronta (dependências satisfeitas), pela maior `caminho_à_frente`, a partir do primeiro passo pendente;
2. review lean pendente;
3. gate com todas as tasks `done`;
4. passos 1 e 2 de task futura (leitura antecipada), só sem arquivo em comum com task em andamento.

Dependência satisfeita: task `done`; gate `passed`; ou task `implemented` do mesmo cluster e de risco abaixo de 4 (empilhamento).

## 2. Pipeline de uma task

| Passo | O que faz | Saída |
|---|---|---|
| 1 Escopo | fecha entrega e `done_when` | `tasks/<id>/scope.md` |
| 2 Leitura | lê `read_list`, fatos com `arquivo:linha` e hash | `tasks/<id>/reading.md` |
| 3 Avaliação | arquivos, mudança, casos de teste, verificação | `tasks/<id>/plan.md` |
| 4 Testes | Mode A da /test-audit, commit `test:` | commit |
| 5 Implementação | code-guard carregada, até o verde | commits + `result.json` |

- Passos 1 e 2 rodam em paralelo no mesmo slot.
- `changes_behavior` falso pula o passo 4.
- Antes do passo 4, crie a worktree: `git worktree add <repo>/.worktrees/<task> -b dev/<slug>/<task> <base da task>`. Base da task: `stack_on` quando houver (branch da dependência), senão a branch da feature.
- Worktree nova sem mudança de `package.json`: `ln -s <repo>/node_modules <worktree>/node_modules`.
- Falha: o Sonnet não fecha o verde em 2 tentativas → o passo 3 roda de novo uma vez com o erro → nova falha: `devstate.py task-status <dir> <task> blocked "<motivo>"`. Os workers seguem nas outras tasks.

## 3. Review lean e branches

- Task de risco alto: review lean logo após o passo 5, só no diff dela, com `--roast`.
- Risco baixo ou médio: entra no lote do cluster; a review roda quando todas as tasks do cluster estão `implemented` ou `done`, no diff combinado. Se um dependente de fora do cluster ou um gate espera só por ela, a review do lote roda já.
- Rode a review no diretório do lote: para uma task, a worktree dela; para um lote, uma worktree de integração com as branches do lote mescladas.
- `master-review --lean --base <branch da feature> --spec <dir>/spec.md [--roast]`. Os fixers editam o working tree; commite as correções como `fix(review): …`.
- Passou (zero BLOCKER e MAJOR): merge da branch na branch da feature, `devstate.py task-status <dir> <task> done`, `git worktree remove`.
- MAJOR que os fixers não resolveram, revisão visual pendente em task com UI, ou lacuna de especialista: `task-status blocked`. A task não entra na branch da feature.
- Registre a review: `reviews/<id>.md` e o item em `state.reviews` (via decisão de custo com `agent_role: "review"`).

## 4. Gate

`devstate.py gate-status <dir> <gate> running` → `master-review --base <base> --spec <dir>/spec.md` (full) em cada repo, na branch da feature → correção → `passed` ou `blocked`. Gate bloqueado vai para o Marcelo; os workers seguem no que não depende dele.

## 5. Fim da feature

1. Gate final passa.
2. Mode B da /test-audit no diff da feature, em cada repo.
3. Mostre o resumo e peça confirmação para push da branch e abertura de 1 MR por repo. Cada MR cita os outros e a ordem de deploy (quem fornece o contrato sobe primeiro).
4. Retro: dispare um agente `model: "haiku"`, `effort: "medium"` com `prompts/retro.md`. Ele grava `<dir>/retro.md`. Cada checagem que ele propõe passa pelo nível 1 do ciclo de aprendizado da `code-guard` (`diff_checks.py add-check`, que recusa o que não dispara num erro real). Regras sem efeito e custos viram decisões (`origin: "code-guard"`), sem remoção automática.
5. `devstate.py phase <dir> done`. A próxima feature da fila começa sem esperar a confirmação, a partir da base, ou da branch da feature de que depende.
