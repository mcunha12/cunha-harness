# Pausa e retomada

## /dev stop

1. Leia `state.json` da feature ativa.
2. Pare cada agente rodando (TaskStop).
   - Plano, gate: só leem. Recomeçam na retomada.
   - Task ou testes finais: no lugar onde rodavam (branch da feature ou worktree), `git add -u` e `git add -- <arquivos novos da task ou testes novos>`, depois `git commit -m "wip: <task ou tests>"`. Nunca `git add -A`. Com worktree, `git worktree remove`; a branch da task fica.
3. `devstate.py pause <dir> "<motivo>"`. O `pause` devolve task `running` a `pending`, gate `testing` a `pending` e gate `running` a `tested`.
4. Diga ao Marcelo onde a feature parou (o `checkpoint`) e o comando para retomar.

## /dev resume <feature> [instrução]

0. Feature pausada antes de 09/11/2026 (sem `plan.md`): rode a Fase 2, passo 4, de novo. O plano novo mantém as tasks `done` e planeja só o que falta.
1. Com instrução ("tira o T7", "junta T2 e T3"): altere o `plan.json` e o `plan.md` da task tocada, confira as regras da Fase 2 (passo 5), mostre a diferença e registre a decisão com `origin: "resposta"`. Task `done` que a mudança toca volta a `pending`.
2. Base andou (`git merge-base --is-ancestor <base> feat/<slug>` falha): junte a base na branch da feature em cada repo e rode o type-check e os testes da área, via `heavy_lock.sh`. Conflito ou teste vermelho: pare e mostre ao Marcelo.
3. Commit `wip:`: leia o diff e decida continuar daquele código ou descartar (`git reset --hard` para o commit anterior ao `wip:`, só na branch onde ele está). A task redisparada recebe o diff aproveitado no prompt.
4. `devstate.py resume <dir>` e volte ao loop da Fase 3.
