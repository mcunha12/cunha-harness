# Layout de estado

```
~/.claude/dev/
  features/<feature-slug>/
    state.json        # fonte da verdade; só devstate.py escreve
    spec.md           # Fase 1
    plan.json         # Fase 2; devgraph.py analyze preenche "analysis"
    decisions.jsonl   # uma decisão por linha
    costs.jsonl       # um registro por agente
    tasks/<id>/scope.md, reading.md, plan.md, steps.json, result.json
    final-tests/<repo>.md
    reviews/<gate>.md
    situation.json    # bloco "Situação agora", escrito pelo Haiku nos marcos
    tracker.html      # gerado; nunca edite
  repos/<repo>/run.json
  heavy/slot-N/       # trava de processo pesado
```

Escrita sempre atômica (arquivo temporário + rename), pelo `devstate.py`.

## plan.json

```json
{
  "feature": "lembrete-aula",
  "repos": ["api-bff", "web-app"],
  "tasks": [
    {"id": "T1", "title": "Tabela de preferências", "description": "…", "done_when": "…",
     "repo": "api-bff", "files_hint": ["db/migrations/001.sql"], "read_list": ["src/reminders/"],
     "complexity": 3, "risk": 5, "depends_on": [], "changes_behavior": true, "has_ui": false}
  ],
  "gates": [{"id": "G1", "title": "gate final", "waits_for": ["T5"]}],
  "analysis": {"costs": {}, "path_ahead": {}, "critical_path": [], "clusters": {}, "task_cluster": {}}
}
```

- Um gate só, o final. Nenhuma task depende dele.
- Uma task toca um repo só.
- `changes_behavior`: a task entra nos testes finais.

## state.json

```json
{
  "feature": "lembrete-aula",
  "title": "Lembrete de aula ao vivo por e-mail",
  "phase": "requirements | planning | execution | paused | done",
  "repos": {"api-bff": {"path": "/abs/path", "feature_branch": "feat/lembrete-aula", "base": "main"}},
  "tasks": {"T1": {"status": "pending | implemented | done | blocked", "steps_done": [1, 2],
                   "step_running": null, "branch": "dev/lembrete-aula/T1", "worktree": null,
                   "stack_on": null, "block_reason": null, "outputs": {"1": "tasks/T1/scope.md"}}},
  "gates": {"G1": {"status": "pending | testing | tested | running | passed | blocked", "report": null}},
  "workers": [{"slot": 1, "assignment": null, "started_at": null}],
  "reviews": [{"id": "R1", "kind": "full", "tasks": ["T1"], "report": "reviews/G1.md", "tokens": null}],
  "checkpoint": {"at": "2026-10-21T14:32:00", "note": "T3 passo 5 concluído"},
  "paused": null,
  "baseline_failures": ["src/test/a.test.ts > caso"]
}
```

- `implemented` = passos obrigatórios concluídos. `done` = a task entrou na branch da feature, por merge logo depois do `implemented`.
- Passos obrigatórios: 1, 2, 3, 5; sem o 1 quando a complexidade é até 3. O passo 4 não existe desde 07/11/2026.
- Gate: `pending` → `testing` (testes finais) → `tested` → `running` (master-review e QA) → `passed` ou `blocked`. `/dev stop` devolve `testing` a `pending` e `running` a `tested`.
- `workers`: o slot nasce no primeiro uso. O total de slots livres vem do `capacity.py`.

## Logs

- `decisions.jsonl`: `{"id": "D1", "text": "…", "origin": "fonte | código | resposta | agendador | code-guard", "at": "…"}`.
- `costs.jsonl`: `{"agent_role": "step-1", "model": "opus", "task": "T1", "tokens": 1234, "duration_ms": 5000}`. Use o uso de tokens que a notificação do agente traz; sem ele, `tokens: null` e só a duração.

## run.json (por repo)

```json
{"start": "npm run dev", "url": "http://localhost:3000", "login": {"user": "teste@exemplo.com", "password_env": "DEV_LOGIN_PASSWORD"},
 "backend": "api-bff da branch da feature ou URL de preprod"}
```

Senha só por variável de ambiente. Nunca grave senha no arquivo.

## Comandos do devstate.py

```
devstate.py init <dir> <feature> <repos.json>
devstate.py step-started <dir> <task> <step> <slot> [--force]   # exit 3 = passo já feito ou rodando
devstate.py step-done <dir> <task> <step> [output]
devstate.py task-status <dir> <task> <pending|implemented|done|blocked> [motivo]
devstate.py gate-status <dir> <gate> <pending|testing|tested|running|passed|blocked> [relatório]
devstate.py worker <dir> <slot> '<assignment json>' | null
devstate.py reset-steps <dir> <task> <from_step>
devstate.py phase <dir> <requirements|planning|execution|done>
devstate.py pause <dir> <motivo> | resume <dir>
devstate.py baseline <dir> '<json-list>'
devstate.py decision <dir> '<json>' | cost <dir> '<json>'
devstate.py hash <repo_path> <arquivo>... | stale <repo_path> <hashes.json>
```
