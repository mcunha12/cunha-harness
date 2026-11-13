# Layout de estado

```
~/.claude/dev/
  features/<feature-slug>/
    state.json        # fonte da verdade; só devstate.py escreve
    spec.md           # Fase 1
    plan.json         # Fase 2, estrutura das tasks
    plan.md           # Fase 2, uma seção por task
    decisions.jsonl   # uma decisão por linha
    costs.jsonl       # um registro por agente
    tasks/<id>/steps.json, result.json
    final-tests/<repo>.md
    reviews/<repo>.md
  repos/<repo>/run.json
  heavy/slot-N/       # trava de processo pesado
```

Escrita sempre atômica (arquivo temporário + rename), pelo `devstate.py`.

## plan.json

```json
{
  "feature": "lembrete-aula",
  "gate": "lean",
  "deploy_check": {"api-bff": "curl -s https://…/health | grep <sha>"},
  "review": {"scan_effort": "medium",
             "overrides": {"migrations": {"effort": "xhigh", "motivo": "migration apaga coluna"}}},
  "tasks": [
    {"id": "T1", "title": "Tabela de preferências", "repo": "api-bff",
     "files": ["db/migrations/001.sql"], "depends_on": [],
     "complexity": 3, "risk": 5, "model": "haiku", "effort": "medium",
     "has_ui": false, "changes_behavior": true}
  ]
}
```

- Ordem da lista = ordem de execução. `depends_on` cita só tasks anteriores.
- `gate`: `full` se alguma task tem risco 4 ou 5; senão `lean`.
- `model` e `effort`: regras de `phase-2-planning.md`, "Notas do plano".
- `review.overrides`: vira `--overrides tema:esforço` no gate.
- `changes_behavior`: a task entra nos testes finais.
- `deploy_check`: `{"<repo>": "<comando ou consulta>"}`, no topo do `plan.json`. O comando ou consulta que prova a versão em produção. Usado na Fase 4.

## state.json

```json
{
  "feature": "lembrete-aula",
  "phase": "requirements | planning | execution | paused | done",
  "repos": {"api-bff": {"path": "/abs/path", "feature_branch": "feat/lembrete-aula", "base": "main", "impeccable": false}},
  "tasks": {"T1": {"status": "pending | running | implemented | done | blocked", "attempts": 1, "block_reason": null}},
  "gates": {"final": {"status": "pending | testing | tested | running | passed | blocked", "report": null}},
  "checkpoint": {"at": "2026-11-09T14:32:00", "note": "T3 done"},
  "paused": null,
  "waits_for": null,
  "baseline_failures": ["src/test/a.test.ts > caso"]
}
```

- `attempts` sobe a cada `task-status running`. A tentativa 2 roda em Sonnet.
- `implemented` = a task commitou e ficou verde. `done` = a task entrou na branch da feature.
- Gate: `pending` → `testing` → `tested` → `running` → `passed` ou `blocked`. `pause` devolve `testing` a `pending` e `running` a `tested`.

## Logs

- `decisions.jsonl`: `{"id": "D1", "text": "…", "origin": "fonte | código | resposta | orquestrador | impeccable", "at": "…"}`.
- `costs.jsonl`: `{"agent_role": "task", "model": "haiku", "task": "T1", "tokens": 1234, "duration_ms": 5000}`. Use o uso de tokens da notificação do agente; sem ele, `tokens: null`.

## run.json (por repo)

```json
{"start": "npm run dev", "url": "http://localhost:3000", "login": {"user": "teste@exemplo.com", "password_env": "DEV_LOGIN_PASSWORD"},
 "backend": "api-bff da branch da feature ou URL de preprod"}
```

Senha só por variável de ambiente.

## Comandos do devstate.py

```
devstate.py init <dir> <feature> <repos.json>
devstate.py task-status <dir> <task> <pending|running|implemented|done|blocked> [motivo]
devstate.py gate-status <dir> <gate> <pending|testing|tested|running|passed|blocked> [relatório]
devstate.py phase <dir> <requirements|planning|execution|done>
devstate.py pause <dir> <motivo> | resume <dir>
devstate.py wait <dir> <dir da feature esperada> | ready <dir>
devstate.py close <dir> <repo> '{"mr": "12", "head_sha": "…", "issues": ["#3"], "status": "watching | closed | ci_failed | deploy_pending | cleaned"}'
devstate.py baseline <dir> '<json-list>'
devstate.py decision <dir> '<json>' | cost <dir> '<json>'
```
