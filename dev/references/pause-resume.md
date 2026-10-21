# Pausa e retomada

## /dev stop

1. Leia `state.json` da feature ativa.
2. Para cada worker ocupado:
   - passo 1, 2, 3, review ou gate (só leem): pare o agente (TaskStop). O passo recomeça na retomada.
   - passo 4 ou 5 (editam código): pare o agente e, na worktree da task, `git add -A && git commit -m "wip: <task> passo <n>"`. Depois `git worktree remove <worktree>`. A branch da task fica.
3. `devstate.py worker <dir> <slot> null` para cada slot e `devstate.py pause <dir> "<motivo>"`.
4. Diga ao Marcelo onde a feature parou (o `checkpoint` do estado) e o comando para retomar.

A branch da feature só recebe task revisada. Parar no meio nunca a quebra.

## /dev resume <feature> [instrução]

0. Com instrução em linguagem natural ("tira o T7", "junta T2 e T3", "gate depois do T5"):
   1. altere o `plan.json`;
   2. `devgraph.py validate plan.json` até voltar `[]`;
   3. `devgraph.py analyze plan.json`;
   4. mostre a diferença (tasks, dependências, gates, caminho crítico);
   5. task `done` que a mudança toca volta a partir do passo 3: `devstate.py reset-steps <dir> <task> 3`; task com commit `wip:` que a mudança toca: o Opus decide se aproveita o diff;
   6. registre a mudança em `decisions.jsonl` com `origin: "resposta"`.
1. Base andou (`git fetch` e `git merge-base` diferente do registrado): faça merge da base na branch da feature em cada repo e rode de novo os testes das tasks `done`, via `heavy_lock.sh`. Conflito ou teste vermelho: pare e mostre ao Marcelo.
2. Leitura velha: para cada task com `reading.md`, `devstate.py stale <repo> <hashes>`; arquivo na lista → `devstate.py reset-steps <dir> <task> 2`.
3. Commit `wip:`: o Opus lê o diff e decide continuar daquele código ou descartar (`git reset --hard` na branch da task para o commit anterior ao `wip:`, só nessa branch).
4. Recrie as worktrees das tasks em andamento.
5. `devstate.py resume <dir>` e volte ao loop do orquestrador.
