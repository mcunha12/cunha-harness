#!/usr/bin/env python3
"""Estado do /dev: escrita atômica, checkpoints, pausa e fila."""
import copy
import datetime
import json
import os
import sys
import tempfile

def _now():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def atomic_write_json(path, data):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def append_jsonl(path, record):
    with open(path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def state_path(feature_dir):
    return os.path.join(feature_dir, "state.json")


def load(feature_dir):
    with open(state_path(feature_dir)) as f:
        return json.load(f)


def new_task_state():
    return {"status": "pending", "attempts": 0, "block_reason": None}


def init(feature_dir, feature, repos):
    os.makedirs(feature_dir, exist_ok=True)
    return {"feature": feature, "phase": "requirements", "repos": repos, "tasks": {}, "gates": {},
            "checkpoint": {"at": _now(), "note": "feature criada"}, "paused": None}


def _checkpoint(state, note):
    state["checkpoint"] = {"at": _now(), "note": note}
    return state


def set_baseline(state, failures):
    s = copy.deepcopy(state)
    s["baseline_failures"] = list(failures)
    return _checkpoint(s, f"baseline: {len(failures)} falha(s) que já existem na base")


def set_task_status(state, task, status, reason=None):
    s = copy.deepcopy(state)
    ts = s["tasks"].setdefault(task, new_task_state())
    ts["status"] = status
    ts["block_reason"] = reason
    if status == "running":
        ts["attempts"] = ts.get("attempts", 0) + 1
    return _checkpoint(s, f"{task} {status}" + (f": {reason}" if reason else ""))


def set_gate_status(state, gate, status, report=None):
    s = copy.deepcopy(state)
    s["gates"][gate] = {"status": status, "report": report}
    return _checkpoint(s, f"{gate} {status}")


def set_phase(state, phase):
    s = copy.deepcopy(state)
    s["phase"] = phase
    return _checkpoint(s, f"fase: {phase}")


def set_closing(state, repo, info):
    s = copy.deepcopy(state)
    entry = s.setdefault("closing", {}).setdefault(repo, {})
    entry.update(info)
    entry["at"] = _now()
    return _checkpoint(s, f"fechamento {repo}: {entry.get('status')}")


REOPEN_ON_PAUSE = {"testing": "pending", "running": "tested"}


def pause(state, reason):
    s = copy.deepcopy(state)
    for ts in s["tasks"].values():
        if ts["status"] == "running":
            ts["status"] = "pending"
    # Testes finais e gate recomeçam na retomada; parados em "testing" ou "running", o agendador nunca os redispararia.
    for g in s["gates"].values():
        g["status"] = REOPEN_ON_PAUSE.get(g["status"], g["status"])
    s["paused"] = {"at": _now(), "reason": reason, "phase_before": s["phase"]}
    s["phase"] = "paused"
    return _checkpoint(s, f"pausada: {reason}")


def resume(state):
    s = copy.deepcopy(state)
    before = (s.get("paused") or {}).get("phase_before", "execution")
    s["phase"] = "execution" if before == "paused" else before
    s["paused"] = None
    return _checkpoint(s, "retomada")


def wait_for(state, dep_dir):
    s = copy.deepcopy(state)
    s["waits_for"] = dep_dir
    name = load(dep_dir).get("feature") or os.path.basename(os.path.normpath(dep_dir))
    return _checkpoint(s, f"na fila: espera {name}")


def is_ready(state):
    dep_dir = state.get("waits_for")
    if not dep_dir:
        return True
    try:
        return load(dep_dir).get("phase") == "done"
    except FileNotFoundError:
        return False


def _save(feature_dir, state):
    atomic_write_json(state_path(feature_dir), state)


def cost_error(feature_dir, record):
    missing = [k for k in ("agent_role", "model", "task", "tokens", "duration_ms") if k not in record]
    if missing:
        return f"faltam campos {missing}"
    if record["tokens"] > 0 and record["duration_ms"] <= 0:
        return "duration_ms 0 com tokens: grave a duração do agente, não um total somado"
    path = os.path.join(feature_dir, "costs.jsonl")
    if os.path.exists(path):
        with open(path) as f:
            last = [x for x in f.read().splitlines() if x.strip()][-1:]
        if last and json.loads(last[0]) == record:
            return "linha idêntica à anterior"
    return None


USAGE = """uso: devstate.py <op> <feature_dir> ...
  init <dir> <feature> <repos.json>
  task-status <dir> <task> <status> [reason]
  gate-status <dir> <gate> <status> [report]
  phase <dir> <requirements|planning|execution|done>
  pause <dir> <reason> | resume <dir>
  wait <dir> <dep_feature_dir> | ready <dir>  (exit 0 = pode começar)
  close <dir> <repo> <json>  (fechamento: mr, issues, status)
  baseline <dir> <json-list>  (testes que já falham na base)
  decision <dir> <json> | cost <dir> <json>"""


def main(argv):
    if len(argv) < 3:
        print(USAGE, file=sys.stderr)
        return 2
    op, target, args = argv[1], argv[2], argv[3:]
    if op == "init":
        with open(args[1]) as f:
            _save(target, init(target, args[0], json.load(f)))
        return 0
    if op == "cost":
        error = cost_error(target, json.loads(args[0]))
        if error:
            print(f"custo recusado: {error}", file=sys.stderr)
            return 2
    if op in ("decision", "cost"):
        append_jsonl(os.path.join(target, "decisions.jsonl" if op == "decision" else "costs.jsonl"), json.loads(args[0]))
        return 0
    state = load(target)
    if op == "ready":
        return 0 if is_ready(state) else 1
    if op == "baseline":
        state = set_baseline(state, json.loads(args[0]))
    elif op == "task-status":
        state = set_task_status(state, args[0], args[1], args[2] if len(args) > 2 else None)
    elif op == "gate-status":
        state = set_gate_status(state, args[0], args[1], args[2] if len(args) > 2 else None)
    elif op == "close":
        state = set_closing(state, args[0], json.loads(args[1]))
    elif op == "phase":
        state = set_phase(state, args[0])
    elif op == "pause":
        state = pause(state, args[0] if args else "stop")
    elif op == "resume":
        state = resume(state)
    elif op == "wait":
        state = wait_for(state, args[0])
    else:
        print(USAGE, file=sys.stderr)
        return 2
    _save(target, state)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
