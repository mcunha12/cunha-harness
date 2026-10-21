# Fase 3 — Execução

## 1. Agendador

`devgraph.py next` decide, nesta ordem:

0. `merge` de toda task de risco baixo ou médio `implemented`. Não ocupa worker: o orquestrador faz na hora.
1. task pronta (dependências satisfeitas), pela maior `caminho_à_frente`, a partir do primeiro passo pendente;
2. review lean pendente (só task de risco alto);
3. gate com todas as tasks `done`;
4. passo 1 de task futura (escopo antecipado), só sem arquivo em comum com task em andamento. O passo 2 espera a task ficar pronta: leitura de código com dependência aberta envelhece antes do passo 3 (feature pedido-na-secretaria, 21/10/2026: T2 a T4 releram tudo depois que a T1 mudou o contrato).

Dependência satisfeita: task `done`; gate `passed`; ou task `implemented` do mesmo cluster e de risco abaixo de 4 (empilhamento).

## 2. Pipeline de uma task

| Passo | O que faz | Saída |
|---|---|---|
| 1 Escopo | fecha entrega e `done_when`; só complexidade 4 e 5 | `tasks/<id>/scope.md` |
| 2 Leitura | lê `read_list`, fatos com `arquivo:linha` e hash | `tasks/<id>/reading.md` |
| 3 Avaliação | arquivos, mudança, casos de teste, verificação | `tasks/<id>/plan.md` |
| 4 Testes | Mode A da /test-audit, commit `test:` | commit |
| 5 Implementação | code-guard carregada, até o verde | commits + `result.json` |

- Passos 1 e 2 rodam em paralelo no mesmo slot.
- Complexidade até 3: não há passo 1. O passo 3 grava `scope.md` e `plan.md` (`devgraph.required_steps`).
- `devstate.py step-started` recusa (exit 3) passo já feito ou rodando. Antes de disparar de novo, confira se o arquivo de saída já existe. Refazer de propósito: `--force`.
- Base fresca: antes do passo 3 de cada task e antes do gate, rode `git merge-base --is-ancestor <base> <branch da feature>`. Se a base andou, junte a base na branch da feature na hora e rode os testes da área. Se a base já entrou na `main`, a base passa a ser a `main`. Em ranking-fellowship a base andou duas vezes e o conflito apareceu só no fim, em 6 arquivos.
- Dado pessoal em teste: o passo 4 e o passo 5 rodam `python3 ~/.claude/skills/dev/scripts/fixture_pii.py <worktree> <base da task>` antes do commit. Exit 1 bloqueia o commit até trocar o dado por pseudônimo (`Aluno Exemplo NN`, `@exemplo.com`, `Cidade Exemplo N`/`ZZ`, `11900xxxxxx`). Em ranking-fellowship o dado pessoal foi achado 3 vezes, sempre na review.
- `changes_behavior` falso pula o passo 4.
- Antes do passo 4, crie a worktree: `git worktree add <repo>/.worktrees/<task> -b dev/<slug>/<task> <base da task>`. Base da task: `stack_on` quando houver (branch da dependência), senão a branch da feature.
- Worktree nova sem mudança de `package.json`: `ln -s <repo>/node_modules <worktree>/node_modules`.
- Falha: o Sonnet não fecha o verde em 2 tentativas → o passo 3 roda de novo uma vez com o erro → nova falha: `devstate.py task-status <dir> <task> blocked "<motivo>"`. Os workers seguem nas outras tasks.

## 3. Review lean e branches

- Task de risco alto (4 ou 5): review lean logo após o passo 5, só no diff dela, com `--roast`, na worktree dela.
- Risco baixo ou médio (1 a 3): sem review lean. Assignment `merge`: merge da branch na branch da feature, `task-status done`, `git worktree remove`. O gate revisa o diff inteiro. Medido em pedido-na-secretaria: as reviews lean de risco 2 e 3 custaram 3,1 M tokens (34% da feature) e acharam 2 MAJOR; o gate achou outros 5 sozinho.
- `master-review --lean --base <branch da feature> --spec <dir>/spec.md --roast --only <até 5 especialistas>`. Escolha os 5 pelo diff (o que o código toca: fronteira, banco, UI, auth). `spec`, `roast`, `test-audit` e as checagens determinísticas ficam fora da conta. Cada especialista custa 65 a 100 mil tokens quase fixos (skill, referências e diff), qualquer que seja o tamanho do diff. Os fixers editam o working tree; commite as correções como `fix(review): …`.
- Passou (zero BLOCKER e MAJOR): merge da branch na branch da feature, `devstate.py task-status <dir> <task> done`, `git worktree remove`.
- MAJOR que os fixers não resolveram, revisão visual pendente em task com UI, ou lacuna de especialista: `task-status blocked`. A task não entra na branch da feature.
- Registre a review: `reviews/<id>.md` e o item em `state.reviews` (via decisão de custo com `agent_role: "review"`).

## 4. Gate

`devstate.py gate-status <dir> <gate> running` → `master-review --base <base> --spec <dir>/spec.md` (full) em cada repo, na branch da feature → correção → `passed` ou `blocked`. Gate bloqueado vai para o Marcelo; os workers seguem no que não depende dele.

Escopo do gate:

- Arquivos de task sem review lean (risco 1 a 3): full, com os especialistas que o diff pede.
- Arquivos de task com review lean (risco 4 e 5): só as costuras. Passe `reviews/*.md` como "já decidido" e rode só `contratos`, `resiliencia`, `spec` e `test-audit`, com o foco em contrato entre camadas (card, tela, função), ordem de deploy e regressão do comportamento antigo. Medido em ranking-fellowship: o gate full custou 935 mil tokens; dos 9 MAJOR dele, 2 eram novos e os dois eram costura.
- `fixture_pii.py` e a baseline de falhas rodam antes dos especialistas; o que eles acham não é reportado de novo.

## 5. Fim da feature

1. Gate final passa.
2. Mode B da /test-audit no diff da feature, em cada repo.
3. Mostre o resumo e peça confirmação para push da branch e abertura de 1 MR por repo. Cada MR cita os outros e a ordem de deploy (quem fornece o contrato sobe primeiro).
4. Retro: dispare um agente `model: "haiku"`, `effort: "medium"` com `prompts/retro.md`. Ele grava `<dir>/retro.md`. Cada checagem que ele propõe passa pelo nível 1 do ciclo de aprendizado da `code-guard` (`diff_checks.py add-check`, que recusa o que não dispara num erro real). Regras sem efeito e custos viram decisões (`origin: "code-guard"`), sem remoção automática.
5. `devstate.py phase <dir> done`. A próxima feature da fila começa sem esperar a confirmação, a partir da base, ou da branch da feature de que depende.
