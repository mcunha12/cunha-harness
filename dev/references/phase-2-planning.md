# Fase 2 — Plano da feature

Roda quando a feature começa: `devstate.py phase <dir> planning`. Nunca roda antes: o código envelhece.

1. Revalidação. Cruze os arquivos que as features anteriores alteraram (`git diff --name-only` das branches delas) com o mapeamento desta feature. Com interseção, as decisões da spec que dependem desses arquivos voltam ao Marcelo.
2. Branches. Crie `feat/<slug>` em cada repo a partir da base e registre em `state.json`.
3. Baseline de falhas. Rode uma vez, na base, os testes da área que a feature toca (via `heavy_lock.sh`, workers limitados). Grave os que já falham: `devstate.py baseline <dir> '<json-list>'`. Task, testes finais e gate não reinvestigam essas falhas.
4. Plano. Dispare 1 agente Opus `high` com `prompts/plan-feature.md`. Ele lê o código uma vez e grava `plan.json`, `plan.md` e o `steps.json` de cada task com UI. O baseline e o plano podem rodar na mesma mensagem.
5. Conferência. Leia o `plan.json`:
   - toda task toca um repo só;
   - `depends_on` cita só tasks anteriores na lista;
   - toda task com `has_ui` tem `tasks/<id>/steps.json`.

   Erro: devolva ao mesmo agente (SendMessage) com a lista do que corrigir.
6. `devstate.py phase <dir> execution`. A execução começa sem esperar aprovação. Ao Marcelo vai 1 linha: número de tasks, repos e o tipo de gate (lean ou full).

## Notas do plano

O plano escolhe o modelo de cada task e os overrides da review. O risco escolhe o tipo de gate.

| Nota | Complexidade | Risco |
|---|---|---|
| 1 | 1 arquivo, mudança local | copy, estilo, sem lógica |
| 2 | 2 a 3 arquivos no mesmo módulo | UI com lógica local |
| 3 | 4 a 8 arquivos ou 2 módulos | regra de negócio coberta por teste existente |
| 4 | 9 a 15 arquivos, 3+ módulos ou lógica nova não trivial | contrato entre serviços, autenticação, dinheiro, dado de usuário |
| 5 | mais de 15 arquivos ou mudança transversal | migration de schema, dado irreversível, segurança |

Modelo da task (tabela da SKILL.md, seção 4):

- Lógica: `haiku` `medium`. `sonnet` `medium` com complexidade 4 ou 5, lógica nova não trivial ou 5 ou mais regras de negócio.
- UI: `sonnet` `medium`. `sonnet` `high` ou `opus` `medium` com tela nova, estado de tela complexo ou animação.
- Task com lógica e UI conta como UI.

Review:

- Alguma task com risco 4 ou 5: o gate é a `master-review` full. Senão, `--lean`.
- Tema crítico ou de alta complexidade: o plano grava o override daquele tema (`high` ou `xhigh`) com o motivo. Exemplo: migration irreversível → `migrations:xhigh`; mudança de autorização → `seguranca:high`.
- Scan da review: `low` só em diff pequeno sem tema crítico; senão `medium`.
