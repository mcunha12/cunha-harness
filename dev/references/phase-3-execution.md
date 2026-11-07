# Fase 3 — Execução

## 1. Agendador

`devgraph.py next` decide, nesta ordem:

0. `merge` de toda task `implemented`. Não ocupa worker: o orquestrador faz na hora.
1. task pronta (dependências satisfeitas), pela maior `caminho_à_frente`, a partir do primeiro passo pendente;
2. `tests`: testes finais, quando todas as tasks estão `done` e o gate final está `pending`;
3. `gate`: gate final com QA, quando o gate está `tested`;
4. passo 1 de task futura (escopo antecipado), só sem arquivo em comum com task em andamento. O passo 2 espera a task ficar pronta: leitura de código com dependência aberta envelhece antes do passo 3 (feature pedido-na-secretaria, 21/10/2026: T2 a T4 releram tudo depois que a T1 mudou o contrato).

Dependência satisfeita: task `done`, ou task `implemented` do mesmo cluster (empilhamento). Gate intermediário de plano anterior a 07/11/2026 não roda: ele vale como passado quando as tasks dele fecham.

## 2. Pipeline de uma task

| Passo | O que faz | Saída |
|---|---|---|
| 1 Escopo | fecha entrega e `done_when`; só complexidade 4 e 5 | `tasks/<id>/scope.md` |
| 2 Leitura | lê `read_list`, fatos com `arquivo:linha` e hash | `tasks/<id>/reading.md` |
| 3 Avaliação | arquivos, mudança, comportamentos para os testes finais, verificação, fluxo de QA, modelo do passo 5 | `tasks/<id>/plan.md`, `tasks/<id>/steps.json` com UI |
| 5 Implementação | code-guard carregada, sem teste novo, até type-check, lint e testes existentes verdes | commits + `result.json` |

O passo 4 (testes antes do código) saiu em 07/11/2026. O passo 5 mantém o número para não quebrar estados antigos.

- Passos 1 e 2 rodam em paralelo no mesmo slot.
- Complexidade até 3: não há passo 1. O passo 3 grava `scope.md` e `plan.md` (`devgraph.required_steps`).
- `devstate.py step-started` recusa (exit 3) passo já feito ou rodando. Antes de disparar de novo, confira se o arquivo de saída já existe. Refazer de propósito: `--force`.
- Base fresca: antes do passo 3 de cada task e antes dos testes finais, rode `git merge-base --is-ancestor <base> <branch da feature>`. Se a base andou, junte a base na branch da feature na hora e rode os testes da área. Se a base já entrou na `main`, a base passa a ser a `main`. Em ranking-fellowship a base andou duas vezes e o conflito apareceu só no fim, em 6 arquivos.
- Dado pessoal: o passo 5 e os testes finais rodam `python3 ~/.claude/skills/dev/scripts/fixture_pii.py <worktree> <base da worktree>` antes do commit. Exit 1 bloqueia o commit até trocar o dado por pseudônimo (`Aluno Exemplo NN`, `@exemplo.com`, `Cidade Exemplo N`/`ZZ`, `11900xxxxxx`). Em ranking-fellowship o dado pessoal foi achado 3 vezes, sempre na review.
- Antes do passo 5, crie a worktree: `git worktree add <repo>/.worktrees/<task> -b dev/<slug>/<task> <base da task>`. Base da task: `stack_on` quando houver (branch da dependência), senão a branch da feature.
- Worktree nova sem mudança de `package.json`: `ln -s <repo>/node_modules <worktree>/node_modules`.
- Modelo do passo 5: a primeira linha do `plan.md` (`modelo: haiku` ou `modelo: sonnet — <motivo>`). Sonnet vira decisão em `decisions.jsonl` e vai no assignment como `"model": "sonnet"`.
- Falha: o passo 5 não fecha o verde em 2 tentativas → o passo 3 roda de novo uma vez com o erro e pode subir o passo 5 para Sonnet `medium` → nova falha: `devstate.py task-status <dir> <task> blocked "<motivo>"`. Os workers seguem nas outras tasks.

## 3. Branches

Task `implemented` vira assignment `merge`: merge da branch da task na branch da feature, `devstate.py task-status <dir> <task> done`, `git worktree remove`. Nenhuma task tem review própria, em nenhum risco. O gate final revisa o diff inteiro.

## 4. Testes finais

Rodam quando todas as tasks estão `done` (assignment `tests`).

1. `devstate.py gate-status <dir> <gate> testing`.
2. Em cada repo, crie a worktree a partir da branch da feature: `git worktree add <repo>/.worktrees/tests -b dev/<slug>/tests <branch da feature>`. Na retomada, a branch já existe: `git worktree add <repo>/.worktrees/tests dev/<slug>/tests`.
3. Dispare na mesma mensagem um agente por repo, com `prompts/final-tests.md`.
4. Cada agente grava `final-tests/<repo>.md`. Faça merge de `dev/<slug>/tests` na branch da feature e `git worktree remove`.
5. Todos os repos fechados: `devstate.py gate-status <dir> <gate> tested`.

Critério de entrada de cada teste: a tabela "Classify every test case" da /test-audit. Entra só o veredito "Behavior": integração ou E2E com dado real anonimizado e resultado observável, ou unit de função pura de cálculo ou parsing com a lista de modos de falha. Teste que a /test-audit apagaria não é escrito. Cada teste novo passa no código da feature e falha no código da base.

## 5. Gate final com QA

`devstate.py gate-status <dir> <gate> running` → `master-review --base <base> --spec <dir>/spec.md` (full) em cada repo, na branch da feature → correção → `passed` ou `blocked`. Gate bloqueado vai para o Marcelo.

- Review total: todos os especialistas que o diff pede, no diff inteiro da feature. Feature com vários repos: uma review por repo, com os outros repos em `related_repos`.
- QA: o passo 8b da master-review, com os `tasks/*/steps.json` gravados no passo 3. Build de produção, servidor e navegador rodam dentro de `heavy_lock.sh --kind qa`. Regras do "Fast QA" do `~/.claude/CLAUDE.md`.
- `fixture_pii.py` e a baseline de falhas rodam antes dos especialistas. O que eles acham não é reportado de novo.
- O test-audit da master-review roda sem o item 1 do Mode B (ordem dos commits): no /dev, os testes entram depois do código.
- O gate passa quando a review termina sem BLOCKER e sem MAJOR depois da correção.
- Registre a review: `reviews/<gate>.md` e o item em `state.reviews` com `kind: "full"` (via decisão de custo com `agent_role: "review"`).

## 6. Fim da feature

1. Gate final passa.
2. Mode B da /test-audit no diff da feature, em cada repo, sem o item 1.
3. Mostre o resumo e peça confirmação para push da branch e abertura de 1 MR por repo. Cada MR cita os outros e a ordem de deploy (quem fornece o contrato sobe primeiro).
4. Retro: dispare um agente `model: "haiku"`, `effort: "medium"` com `prompts/retro.md`. Ele grava `<dir>/retro.md`. Cada checagem que ele propõe passa pelo nível 1 do ciclo de aprendizado da `code-guard` (`diff_checks.py add-check`, que recusa o que não dispara num erro real). Regras sem efeito e custos viram decisões (`origin: "code-guard"`), sem remoção automática.
5. `devstate.py phase <dir> done`. A próxima feature da fila começa sem esperar a confirmação, a partir da base, ou da branch da feature de que depende.
