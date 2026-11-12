# Fase 3 — Execução

## 1. Loop do orquestrador

```
enquanto houver task pending ou running:
    prontas = tasks pending com todo depends_on em done, na ordem do plan.json
    dispare prontas até 3 tasks em running, na mesma mensagem
    ao receber a notificação de uma task:
        devstate.py cost
        implemented → merge na branch da feature, devstate.py task-status <dir> <task> done
        failed → regra de falha (seção 2)
```

## 2. Uma task

1. `devstate.py task-status <dir> <task> running`.
2. Lugar de trabalho:
   - só esta task rodando no repo: a task roda na branch da feature, sem worktree;
   - 2 ou mais tasks no mesmo repo ao mesmo tempo: `git worktree add <repo>/.worktrees/<task> -b dev/<slug>/<task> feat/<slug>`. Sem mudança de `package.json`, `ln -s <repo>/node_modules <worktree>/node_modules`. Em monorepo com workspace local, siga o `CLAUDE.md` do repo.
3. Dispare o agente com `prompts/task.md`. Modelo: os campos `model` e `effort` da task no `plan.json`.
4. `implemented`: com worktree, merge de `dev/<slug>/<task>` na branch da feature e `git worktree remove`. Depois `task-status done`.
5. Falha:
   - 1ª falha: redisparo um degrau acima, com o erro no prompt. Degraus: `haiku` `medium` → `sonnet` `medium` → `sonnet` `high` → `opus` `medium`. Registre a decisão.
   - 2ª falha: `devstate.py task-status <dir> <task> blocked "<motivo>"`. Avise o Marcelo. As outras tasks seguem.

## 3. Testes finais

Rodam quando todas as tasks estão `done`.

1. Base fresca: `git merge-base --is-ancestor <base> feat/<slug>` em cada repo. Se a base andou, junte a base na branch da feature e rode os testes da área. Conflito ou teste vermelho: pare e mostre ao Marcelo.
2. `devstate.py gate-status <dir> final testing`.
3. Dispare na mesma mensagem 1 agente por repo com `prompts/final-tests.md`. Cada um trabalha na branch da feature e grava `final-tests/<repo>.md`.
4. Todos os repos fechados: `devstate.py gate-status <dir> final tested`.

## 4. Gate final

1. `devstate.py gate-status <dir> final running`.
2. Em cada repo, na branch da feature: `master-review --lean --base <base> --spec <dir>/spec.md --overrides <review.overrides do plano>`. Com alguma task de risco 4 ou 5, a review é full (sem `--lean`). Passe `--scan-effort <review.scan_effort>`. Os modelos são os da tabela da master-review. Feature com vários repos: uma review por repo, com os outros em `related_repos`.
3. Antes dos especialistas rodam `fixture_pii.py` e, em repo com setup do Impeccable, o `impeccable detect` (`references/impeccable.md`). O que eles acham não é reportado de novo.
4. QA: passo 8b da master-review, com os `tasks/*/steps.json`, regras do "Fast QA" do `~/.claude/CLAUDE.md` com a prioridade de tela da spec no lugar da ordem fixa (fluxo inteiro no tamanho prioritário, screenshot das telas alteradas nos outros dois), dentro de `heavy_lock.sh --kind qa`.
5. O test-audit da master-review roda sem o item 1 do Mode B (ordem dos commits): no /dev, os testes entram depois do código.
6. Uma rodada de correção: lote com BLOCKER ou MAJOR em Sonnet `high`, conferido por Opus `high` (passo 11 da master-review). Sem BLOCKER e sem MAJOR depois dela: `gate-status passed`. O que sobrar: `gate-status blocked` e a lista vai ao Marcelo.
7. Grave o relatório em `reviews/<repo>.md`.

## 5. Fim da feature

1. Mostre o resumo e peça confirmação para push da branch e abertura de 1 MR por repo. Cada MR cita os outros e a ordem de deploy (quem fornece o contrato sobe primeiro).
2. `devstate.py phase <dir> done`. A próxima feature da fila começa sem esperar a confirmação.
