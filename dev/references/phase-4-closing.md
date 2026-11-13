# Fase 4 — Fechamento

Objetivo: nenhuma pendência fora de issue, e nenhuma worktree ou branch da feature no disco depois do deploy.

## 1. Pendências viram issue (antes do MR)

Pendência é tudo que a feature deixa para depois:

- achado do gate que ficou (MINOR, NIT, BLOCKER ou MAJOR com `gate-status blocked` aceito pelo Marcelo);
- task `blocked`;
- item fora de escopo ou ponta solta registrada na `spec.md` ou em `decisions.jsonl`;
- passo manual de deploy que o MR não executa (migration, edge function, segredo, card do Metabase).

Regras:

1. Toda pendência vira 1 issue no host do repo: `gh issue create` (GitHub) ou `glab issue create` (GitLab). Uma pendência por issue.
2. Título no imperativo. Corpo: o quê, onde (`arquivo:linha`), por quê, critério de pronto, link da feature (`spec.md`).
3. Pendência de outro repo vai para a issue do repo dono.
4. O MR leva a seção `## Pendências` com a lista das issues (`#12`, `Closes` nunca). Sem pendência, a seção diz "Nenhuma".
5. Grave: `devstate.py close <dir> <repo> '{"issues": ["#12", "#13"]}'`.

As issues são criadas junto com o pedido de confirmação do MR (regra 7): o Marcelo confirma MR e issues de uma vez.

## 2. Scout do MR

Logo depois de abrir o MR de cada repo:

1. `devstate.py close <dir> <repo> '{"mr": "<número>", "head_sha": "<sha pushado>", "status": "watching"}'`.
2. Dispare em background, um por repo: `scripts/mr_scout.sh <repo_path> <número>`. Não faça poll; a notificação chega na saída.
3. Na saída do scout:
   - `0` (mergeado, CI verde): siga para a prova de deploy.
   - `3` (fechado sem merge): `close ... '{"status": "closed"}'`, avise o Marcelo em 1 linha, não limpe.
   - `4` (CI vermelho no merge): `close ... '{"status": "ci_failed"}'`, avise o Marcelo, não limpe.

## 3. Prova de deploy

Merge não é deploy. A limpeza só roda com o conteúdo provado em produção.

1. O plano grava em `plan.json` o `deploy_check` de cada repo: o comando ou a consulta que prova a versão em produção (tabela da migration via `to_regclass`, versão da edge function, SHA do build publicado, endpoint que devolve o campo novo).
2. Rode o `deploy_check` com um agente `haiku` `low`. Passo manual pendente (migration, edge) já tem issue pela seção 1; ele não bloqueia a limpeza do código, que já está no `main`.
3. Deploy não provado em 24 h: `close ... '{"status": "deploy_pending"}'`, avise o Marcelo, não limpe.

## 4. Limpeza

Com MR mergeado, CI verde e deploy provado:

1. `scripts/cleanup.sh <repo_path> <slug> <head_sha>`. O script remove as worktrees de `feat/<slug>` e `dev/<slug>/*`, apaga as branches locais e a remota e roda `git worktree prune`.
2. O script recusa (saída 5) quando a branch local tem commit fora do MR ou o checkout tem mudança não commitada. Nesse caso: abra MR de follow-up com o commit órfão e volte ao passo 2. Nunca force.
3. `devstate.py close <dir> <repo> '{"status": "cleaned"}'`. Marco ao Marcelo: 1 linha por repo.
4. Feature com todos os repos `cleaned`: apague `node_modules`, `.next` e `dist` que tenham ficado em `<repo>/.worktrees/`, se a pasta ainda existir.
