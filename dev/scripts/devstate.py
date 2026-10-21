#!/usr/bin/env python3
"""Estado do /dev: escrita atômica, checkpoints, pausa e hash de leitura."""
import copy
import datetime
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WORKERS = 4


def _now():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def atomic_write_json(path, data):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
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
    return {"status": "pending", "steps_done": [], "step_running": None, "branch": None, "worktree": None,
            "stack_on": None, "block_reason": None, "outputs": {}}


def init(feature_dir, feature, repos):
    os.makedirs(feature_dir, exist_ok=True)
    return {"feature": feature, "phase": "requirements", "repos": repos, "tasks": {}, "gates": {},
            "workers": [{"slot": i, "assignment": None, "started_at": None} for i in range(1, WORKERS + 1)],
            "reviews": [], "checkpoint": {"at": _now(), "note": "feature criada"}, "paused": None}


def _checkpoint(state, note):
    state["checkpoint"] = {"at": _now(), "note": note}
    return state


def step_started(state, task, step, slot):
    s = copy.deepcopy(state)
    s["tasks"].setdefault(task, new_task_state())["step_running"] = step
    for w in s["workers"]:
        if w["slot"] == slot:
            w["assignment"] = w.get("assignment") or {"kind": "task", "task": task, "from_step": step}
            w["started_at"] = _now()
    return _checkpoint(s, f"{task} passo {step} iniciado")


def step_done(state, task, step, output=None, required=(1, 2, 3, 4, 5)):
    s = copy.deepcopy(state)
    ts = s["tasks"].setdefault(task, new_task_state())
    if step not in ts["steps_done"]:
        ts["steps_done"].append(step)
        ts["steps_done"].sort()
    ts["step_running"] = None
    if output:
        ts["outputs"][str(step)] = output
    if ts["status"] == "pending" and all(n in ts["steps_done"] for n in required):
        ts["status"] = "implemented"
    return _checkpoint(s, f"{task} passo {step} concluído")


def set_task_status(state, task, status, reason=None):
    s = copy.deepcopy(state)
    ts = s["tasks"].setdefault(task, new_task_state())
    ts["status"] = status
    ts["block_reason"] = reason
    return _checkpoint(s, f"{task} {status}" + (f": {reason}" if reason else ""))


def set_gate_status(state, gate, status, report=None):
    s = copy.deepcopy(state)
    s["gates"][gate] = {"status": status, "report": report}
    return _checkpoint(s, f"{gate} {status}")


def set_worker(state, slot, assignment):
    s = copy.deepcopy(state)
    for w in s["workers"]:
        if w["slot"] == slot:
            w["assignment"] = assignment
            w["started_at"] = _now() if assignment else None
    return s


def set_phase(state, phase):
    s = copy.deepcopy(state)
    s["phase"] = phase
    return _checkpoint(s, f"fase: {phase}")


def pause(state, reason):
    s = copy.deepcopy(state)
    for ts in s["tasks"].values():
        ts["step_running"] = None
    for w in s["workers"]:
        w["assignment"], w["started_at"] = None, None
    s["paused"] = {"at": _now(), "reason": reason, "phase_before": s["phase"]}
    s["phase"] = "paused"
    return _checkpoint(s, f"pausada: {reason}")


def resume(state):
    s = copy.deepcopy(state)
    before = (s.get("paused") or {}).get("phase_before", "execution")
    s["phase"] = "execution" if before == "paused" else before
    s["paused"] = None
    return _checkpoint(s, "retomada")


def hash_files(repo_path, files):
    out = {}
    for name in files:
        path = os.path.join(repo_path, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                out[name] = hashlib.sha256(f.read()).hexdigest()
    return out


def stale_files(repo_path, hashes):
    current = hash_files(repo_path, list(hashes))
    return [name for name, digest in hashes.items() if current.get(name) != digest]


def _required_for(feature_dir, task):
    try:
        with open(os.path.join(feature_dir, "plan.json")) as f:
            plan = json.load(f)
    except FileNotFoundError:
        return (1, 2, 3, 4, 5)
    from devgraph import required_steps
    for t in plan.get("tasks", []):
        if t["id"] == task:
            return required_steps(t)
    return (1, 2, 3, 4, 5)


def _save(feature_dir, state):
    atomic_write_json(state_path(feature_dir), state)
    try:
        from render_tracker import render_dir
        render_dir(feature_dir)
    except Exception as exc:  # o render nunca derruba o checkpoint
        print(f"render falhou: {exc}", file=sys.stderr)


USAGE = """uso: devstate.py <op> <feature_dir> ...
  init <dir> <feature> <repos.json>
  step-started <dir> <task> <step> <slot>
  step-done <dir> <task> <step> [output]
  task-status <dir> <task> <status> [reason]
  gate-status <dir> <gate> <status> [report]
  worker <dir> <slot> <assignment-json|null>
  phase <dir> <requirements|planning|execution|done>
  pause <dir> <reason> | resume <dir>
  decision <dir> <json> | cost <dir> <json>
  hash <repo_path> <file>... | stale <repo_path> <hashes.json>"""


def main(argv):
    if len(argv) < 3:
        print(USAGE, file=sys.stderr)
        return 2
    op, target, args = argv[1], argv[2], argv[3:]
    if op == "hash":
        print(json.dumps(hash_files(target, args)))
        return 0
    if op == "stale":
        with open(args[0]) as f:
            print(json.dumps(stale_files(target, json.load(f))))
        return 0
    if op == "init":
        with open(args[1]) as f:
            _save(target, init(target, args[0], json.load(f)))
        return 0
    if op in ("decision", "cost"):
        append_jsonl(os.path.join(target, "decisions.jsonl" if op == "decision" else "costs.jsonl"), json.loads(args[0]))
        _save(target, load(target))
        return 0
    state = load(target)
    if op == "step-started":
        state = step_started(state, args[0], int(args[1]), int(args[2]))
    elif op == "step-done":
        state = step_done(state, args[0], int(args[1]), args[2] if len(args) > 2 else None,
                          required=_required_for(target, args[0]))
    elif op == "task-status":
        state = set_task_status(state, args[0], args[1], args[2] if len(args) > 2 else None)
    elif op == "gate-status":
        state = set_gate_status(state, args[0], args[1], args[2] if len(args) > 2 else None)
    elif op == "worker":
        state = set_worker(state, int(args[0]), json.loads(args[1]))
    elif op == "phase":
        state = set_phase(state, args[0])
    elif op == "pause":
        state = pause(state, args[0] if args else "stop")
    elif op == "resume":
        state = resume(state)
    else:
        print(USAGE, file=sys.stderr)
        return 2
    _save(target, state)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
