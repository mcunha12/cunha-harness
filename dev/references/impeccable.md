# Impeccable no /dev

Vale só para repo com setup: `PRODUCT.md` ou `DESIGN.md` na raiz. O `state.json` guarda isso em `repos.<repo>.impeccable`. Launcher: `~/.claude/skills/impeccable/scripts/impeccable`, com o cwd no repo.

| Fase | Quem | O que faz |
|---|---|---|
| Requisitos | orquestrador | lê o `PRODUCT.md`: público, modo de cada tela (Operate, Read, Persuade, Experience), restrições. Entra na spec |
| Brainstorm | orquestrador | toda proposta de UI passa por `context`, `shape` e, no mockup, `craft-floor` e `detect`. Vale também sem setup. Procedimento em `references/brainstorm.md`, seção "Propostas de UI com Impeccable" |
| Plano | agente do plano | roda `impeccable context --target <rota ou arquivo>` uma vez por tela tocada. Em cada task com UI, o `plan.md` registra o modo da tela, os tokens e componentes do `DESIGN.md` que a task usa e o comando do Impeccable que guia a mudança (`layout`, `clarify`, `adapt`, `polish`, `typeset`, `onboard`, `harden`), quando houver |
| Task com UI | agente da task | carrega a skill `impeccable`: roda o `context` com o `--target` do plano, lê a referência do comando indicado e lê `reference/craft-floor.md` antes de editar UI. Usa só tokens e componentes do `DESIGN.md`. Antes do commit, roda `impeccable detect <arquivos de UI alterados>` e zera os achados |
| Gate | orquestrador | roda `impeccable detect` nos arquivos de UI do diff antes dos especialistas. Os achados entram na coleta da master-review como MAJOR confirmado. O `review-ux` recebe o `PRODUCT.md` e o `DESIGN.md` como referência |

Regras:

- Task que cria token ou componente novo registra no `DESIGN.md` na mesma task. Token fora do `DESIGN.md` sem esse registro é MAJOR no gate.
- Diretiva `CONTEXT_STALE` do `context`: vai para `decisions.jsonl` e para o resumo final. O /dev não conserta drift.
- O /dev não roda `critique` nem `audit` do Impeccable: o gate já cobre UX, a11y e front com os especialistas da master-review.
- Sem setup: só a linha "Brainstorm" da tabela roda. A task de UI segue `references/unslop.md` mesmo sem setup.
- Prioridade de tela: a spec define qual tamanho vem primeiro (mobile, tablet ou desktop). Mockup, task de UI e QA seguem essa ordem no lugar da ordem fixa do `~/.claude/CLAUDE.md`.
