---
name: dev
description: Pipeline de desenvolvimento ponta a ponta, do pedido ao MR, com estado salvo para pausar e retomar. Use com /dev <pedido>, /dev, /dev stop, /dev resume <feature> [instrução], ou quando o Marcelo pedir para desenvolver uma feature a partir de um prompt, link do Jira, link do Notion ou arquivo.
argument-hint: "[<pedido> | stop | resume <feature> [instrução]]"
model: opus
effort: medium
---

# /dev

A sessão principal é o orquestrador. Ela guarda o estado, dispara os agentes e faz os merges. O conteúdo de cada fase vive em `references/`.

## 1. Comandos

| Comando | Efeito |
|---|---|
| `/dev <pedido>` | Fase 1 para todas as features do pedido, depois a primeira feature. |
| `/dev` | Lista as features em `~/.claude/dev/features/`: fase, repos, último checkpoint. |
| `/dev stop` | Para a feature ativa com segurança. Ver `references/pause-resume.md`. |
| `/dev resume <feature> [instrução]` | Retoma. Com instrução, refaz o plano antes. Ver `references/pause-resume.md`. |

A retro saiu do /dev (09/11/2026). O Marcelo chama a skill `/retro <feature>` quando quiser.

## 2. Regras invioláveis

1. As regras de `references/regras-globais.md` valem aqui e em todo subagent: escrita, código e git, testes, UI e QA, custo. Todo prompt de subagent cita o arquivo; todo prompt de UI carrega a seção "UI e QA". O `~/.claude/CLAUDE.md` de quem roda a /dev vale por cima.
2. Nada em `main` ou `master`: commit, push e merge só em branch de feature ou de task.
3. Só a sessão principal dispara agentes. Subagent não dispara subagent.
4. Todo agente grava a saída no arquivo indicado e devolve só o caminho e até 5 linhas de resumo.
5. Todo estado passa por `scripts/devstate.py`. Nunca edite `state.json` à mão.
6. Todo comando pesado passa por `scripts/heavy_lock.sh`: `--kind build` (type-check, lint, testes, build, `npm install`) e `--kind qa` (build de produção do QA, servidor e navegador). 1 slot por tipo na máquina.
7. Push e abertura de MR pedem confirmação do Marcelo.
8. Ao Marcelo vão só os marcos: task `done` ou `blocked`, gate com status novo, decisão que muda o quê, pedido de confirmação. Cada marco é 1 linha, escrita pelo orquestrador.
9. O orquestrador manda no andamento. A feature na fila começa sozinha quando a que ela espera fecha. Decisão de como fazer vai ao Marcelo em 1 linha, sem pedir confirmação. Pergunta só o que muda o quê (escopo, regra de negócio, dado).
10. Uma feature por vez. Até 3 tasks em paralelo dentro dela. Agente que só lê ou escreve fora do repo não conta no teto.
11. Uma review só: o gate final, depois das tasks e dos testes finais.
12. Testes só no fim da feature, com veredito "Behavior" na tabela da /test-audit. No /dev, esta regra substitui o Mode A da /test-audit e o item da code-guard que pede testes antes do código.
13. Impeccable: repo com `PRODUCT.md` ou `DESIGN.md` na raiz tem setup. Com setup, plano, task de UI e gate usam os recursos dele (`references/impeccable.md`). Sem setup, o /dev segue sem ele e avisa o Marcelo em 1 linha que `/impeccable init` cria o setup. O /dev nunca roda o `init`. Exceção: toda proposta de UI do brainstorm passa pelo Impeccable, com ou sem setup.
14. Brainstorm: todo `/dev <pedido>` passa pelo `references/brainstorm.md` na Fase 1 (cópia adaptada da `superpowers:brainstorming`; não carregue a skill da superpowers) para fechar regras de negócio, pontas soltas e propostas de UI. Nenhuma feature entra na Fase 2 sem a `spec.md` aprovada pelo Marcelo.

## 3. Fluxo

1. Fase 1, requisitos e brainstorm: `references/phase-1-requirements.md`.
2. Fase 2, plano: `references/phase-2-planning.md`.
3. Fase 3, execução, testes finais e gate: `references/phase-3-execution.md`.
4. Antes da primeira task, um agente carrega a skill `code-guard` com a união dos domínios do plano, mais overlay e regras aprendidas, e grava `<feature_dir>/guard.md` só com as regras (sem explicação). As tasks leem esse arquivo e não carregam a skill.
5. O orquestrador lê só o JSON que cada agente devolve. Não abre arquivo de código nem log inteiro.

Custo de contexto e modelo mais barato: `references/regras-globais.md`, seção 5.

Fila entre features, inclusive de outra sessão:

1. `devstate.py wait <dir> <dir da feature esperada>` grava a espera.
2. Dispare em background: `until python3 ~/.claude/skills/dev/scripts/devstate.py ready <dir>; do sleep 300; done`.
3. Quando o loop sair, comece a Fase 2 da feature na hora, sem perguntar.

## 4. Modelos e esforço (fixos, 12/11/2026)

Esta tabela vale sobre o modelo da sessão, o `~/.claude/CLAUDE.md`, `references/regras-globais.md` e a memória. Toda chamada Agent passa `model` e `effort` explícitos.

| Trabalho | Padrão | Quando o plano decide outro |
|---|---|---|
| Orquestrador | a sessão, `model: opus` e `effort: medium` no frontmatter | não muda |
| Mapeamento do código (Fase 1) | `haiku`, `medium` | o orquestrador usa `low` em pedido de 1 módulo |
| Brainstorm (Fase 1) | o orquestrador, na conversa | não muda |
| Builder check da spec (Fase 1) | `opus`, `medium` | não muda |
| Plano da feature (Fase 2), `prompts/plan-feature.md` | `opus`, `high` | não muda |
| Task de lógica, `prompts/task.md` | `haiku`, `medium` | `sonnet`, `medium` |
| Task de UI, `prompts/task.md` | `sonnet`, `medium` | `opus`, `low` |
| Resumo da code-guard (Fase 3, antes da 1ª task) | `haiku`, `low` | não muda |
| Testes finais, 1 por repo, `prompts/final-tests.md` | `haiku`, `medium` | `sonnet`, `medium` |
| Gate final | Skill `master-review` com a tabela de modelos dela: `--lean` por padrão, full quando alguma task tem risco 4 ou 5, `--overrides` do plano | o plano grava os overrides por tema |

`subagent_type: "general-purpose"` e `run_in_background: true` em todos. Todo modelo acima do padrão vira decisão em `decisions.jsonl` com o motivo.

Ao receber a notificação de cada agente, grave o custo: `devstate.py cost <dir> '{"agent_role": ..., "model": ..., "task": ..., "tokens": ..., "duration_ms": ...}'`.

## 5. Arquivos

| Caminho | Conteúdo |
|---|---|
| `references/phase-*.md` | as três fases |
| `references/impeccable.md` | uso do Impeccable no plano, na task e no gate |
| `references/state-layout.md` | pastas e schemas de `plan.json` e `state.json` |
| `references/pause-resume.md` | `/dev stop` e `/dev resume` |
| `prompts/plan-feature.md` | plano da feature inteira |
| `prompts/task.md` | implementação de uma task |
| `prompts/final-tests.md` | testes finais de um repo |
| `scripts/devstate.py` | estado atômico, checkpoints, fila, decisões e custos |
| `scripts/fixture_pii.py` | barra dado pessoal em teste e fixture |
| `scripts/heavy_lock.sh` | trava global de processo pesado |
