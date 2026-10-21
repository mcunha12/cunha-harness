#!/usr/bin/env python3
"""Grafo de tasks do /dev: validação, custo, caminho crítico, clusters e agendador."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MAX_TASKS_BETWEEN_GATES = 6


def load_plan(path):
    with open(path) as f:
        return json.load(f)


def _tasks(plan):
    return {t["id"]: t for t in plan.get("tasks", [])}


def _gates(plan):
    return {g["id"]: g for g in plan.get("gates", [])}


def _deps(plan):
    deps = {tid: list(t.get("depends_on", [])) for tid, t in _tasks(plan).items()}
    deps.update({gid: list(g.get("waits_for", [])) for gid, g in _gates(plan).items()})
    return deps


def _dependents(plan):
    deps = _deps(plan)
    out = {n: [] for n in deps}
    for node, ds in deps.items():
        for d in ds:
            if d in out:
                out[d].append(node)
    return out


def _ancestors(deps, node, seen=None):
    seen = set() if seen is None else seen
    for d in deps.get(node, []):
        if d in deps and d not in seen:
            seen.add(d)
            _ancestors(deps, d, seen)
    return seen


def _find_cycles(deps):
    cycles, state, stack = [], {}, []

    def visit(node):
        state[node] = "open"
        stack.append(node)
        for d in deps.get(node, []):
            if d not in deps:
                continue
            if state.get(d) == "open":
                cycles.append(stack[stack.index(d):] + [d])
            elif d not in state:
                visit(d)
        stack.pop()
        state[node] = "closed"

    for node in deps:
        if node not in state:
            visit(node)
    return cycles


OPUS_EFFORTS = ("medium", "xhigh")


def task_cost(task):
    if "waits_for" in task:
        return 0
    return task["complexity"] * task["risk"]


def validate(plan):
    errors = []
    tasks, gates, deps = _tasks(plan), _gates(plan), _deps(plan)
    for tid, t in tasks.items():
        if not t.get("repo"):
            errors.append({"code": "missing_repo", "task": tid})
        for field in ("complexity", "risk"):
            value = t.get(field)
            if not isinstance(value, int) or not 1 <= value <= 5:
                errors.append({"code": "invalid_score", "task": tid, "field": field})
        if t.get("opus_effort", "medium") not in OPUS_EFFORTS:
            errors.append({"code": "invalid_opus_effort", "task": tid})
    for node, ds in deps.items():
        for d in ds:
            if d not in deps:
                errors.append({"code": "unknown_dependency", "node": node, "dep": d})
    cycles = _find_cycles(deps)
    errors.extend({"code": "cycle", "nodes": c} for c in cycles)
    if cycles:
        return errors
    dependents = _dependents(plan)
    all_tasks = set(tasks)
    has_final = any(not dependents[g] and all_tasks <= _ancestors(deps, g) for g in gates)
    if tasks and not has_final:
        errors.append({"code": "missing_final_gate"})
    for gid in gates:
        anc = _ancestors(deps, gid)
        covered = set()
        for other in anc & set(gates):
            covered |= _ancestors(deps, other)
        count = len((anc & all_tasks) - covered)
        if count > MAX_TASKS_BETWEEN_GATES:
            errors.append({"code": "too_many_tasks_between_gates", "gate": gid, "count": count})
    return errors


def path_ahead(plan):
    nodes = {**_tasks(plan), **_gates(plan)}
    dependents = _dependents(plan)
    memo = {}

    def walk(node):
        if node not in memo:
            after = [walk(d) for d in dependents.get(node, [])]
            memo[node] = task_cost(nodes[node]) + max(after, default=0)
        return memo[node]

    for node in nodes:
        walk(node)
    return memo


def critical_path(plan):
    ahead = path_ahead(plan)
    if not ahead:
        return []
    deps, dependents = _deps(plan), _dependents(plan)
    roots = [n for n in deps if not deps[n]]
    current = min(roots, key=lambda n: (-ahead[n], n))
    path = [current]
    while dependents[current]:
        current = min(dependents[current], key=lambda n: (-ahead[n], n))
        path.append(current)
    return path


def jaccard_distance(a, b):
    union = set(a) | set(b)
    if not union:
        return 1.0
    return 1 - len(set(a) & set(b)) / len(union)


def affinity_clusters(plan, cut=0.8, max_size=4):
    tasks = plan.get("tasks", [])
    order = [t["id"] for t in tasks]
    edges = []
    for i, a in enumerate(tasks):
        for b in tasks[i + 1:]:
            same_repo = a.get("repo") == b.get("repo")
            dist = jaccard_distance(a.get("files_hint", []), b.get("files_hint", [])) if same_repo else 1.0
            edges.append((dist, order.index(a["id"]), order.index(b["id"])))
    parent = {tid: tid for tid in order}
    size = {tid: 1 for tid in order}

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # Kruskal; aresta >= cut fica cortada e o teto de tamanho impede componente grande
    for dist, i, j in sorted(edges):
        if dist >= cut:
            break
        ra, rb = root(order[i]), root(order[j])
        if ra != rb and size[ra] + size[rb] <= max_size:
            parent[rb] = ra
            size[ra] += size[rb]
    groups = {}
    for tid in order:
        groups.setdefault(root(tid), []).append(tid)
    labels = {}
    for tid in order:
        r = root(tid)
        if r not in labels:
            labels[r] = _label(len(labels))
    return {labels[r]: members for r, members in sorted(groups.items(), key=lambda kv: order.index(kv[1][0]))}


def _label(index):
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def analyze(plan):
    clusters = affinity_clusters(plan)
    plan["analysis"] = {
        "costs": {t["id"]: task_cost(t) for t in plan.get("tasks", [])},
        "path_ahead": path_ahead(plan),
        "critical_path": critical_path(plan),
        "clusters": clusters,
        "task_cluster": {tid: label for label, members in clusters.items() for tid in members},
    }
    return plan


HIGH_RISK = 4


def required_steps(task):
    return [1, 2, 3, 5] if not task.get("changes_behavior", True) else [1, 2, 3, 4, 5]


def _in_flight(state):
    busy_tasks, busy_gates = set(), set()
    for w in state.get("workers", []):
        a = w.get("assignment") or {}
        if a.get("task"):
            busy_tasks.add(a["task"])
        busy_tasks.update(a.get("tasks", []))
        if a.get("gate"):
            busy_gates.add(a["gate"])
    for tid, ts in state.get("tasks", {}).items():
        if ts.get("step_running") is not None:
            busy_tasks.add(tid)
    for gid, gs in state.get("gates", {}).items():
        if gs.get("status") == "running":
            busy_gates.add(gid)
    return busy_tasks, busy_gates


def next_assignments(plan, state, free_slots):
    if free_slots <= 0:
        return []
    tasks, gates = _tasks(plan), _gates(plan)
    analysis = plan.get("analysis") or {}
    ahead = analysis.get("path_ahead") or path_ahead(plan)
    cluster_of = analysis.get("task_cluster") or {
        tid: label for label, members in affinity_clusters(plan).items() for tid in members}
    tstate, gstate = state.get("tasks", {}), state.get("gates", {})
    busy_tasks, busy_gates = _in_flight(state)

    def status(tid):
        return tstate.get(tid, {}).get("status", "pending")

    def high_risk(tid):
        return tasks[tid]["risk"] >= HIGH_RISK

    def dep_ok(dep, tid):
        if dep in gates:
            return gstate.get(dep, {}).get("status") == "passed"
        if status(dep) == "done":
            return True
        return (status(dep) == "implemented" and cluster_of.get(dep) == cluster_of.get(tid)
                and not high_risk(dep) and dep not in busy_tasks)

    def stack_on(tid):
        stacked = [d for d in tasks[tid].get("depends_on", []) if d in tasks and status(d) == "implemented"]
        return stacked[-1] if stacked else None

    pending = [tid for tid in tasks if status(tid) == "pending" and tid not in busy_tasks]
    by_priority = sorted(pending, key=lambda tid: (-ahead.get(tid, 0), tid))
    ready = [tid for tid in by_priority if all(dep_ok(d, tid) for d in tasks[tid].get("depends_on", []))]
    out = []
    for tid in ready:
        done = set(tstate.get(tid, {}).get("steps_done", []))
        steps = [n for n in required_steps(tasks[tid]) if n not in done]
        out.append({"kind": "task", "task": tid, "from_step": steps[0] if steps else 5, "stack_on": stack_on(tid)})

    implemented = [tid for tid in tasks if status(tid) == "implemented" and tid not in busy_tasks]
    batches = []

    def add_batch(members):
        if members and members not in batches:
            batches.append(members)

    def cluster_batch(tid):
        label = cluster_of.get(tid)
        return [m for m in implemented if cluster_of.get(m) == label and not high_risk(m)]

    for tid in implemented:
        if high_risk(tid):
            add_batch([tid])
            continue
        members = [m for m in tasks if cluster_of.get(m) == cluster_of.get(tid)]
        if all(status(m) in ("implemented", "done") for m in members):
            add_batch(cluster_batch(tid))
            continue
        # review antecipada: alguém fora do cluster só espera por esta task
        for waiter, node in [(n, tasks.get(n) or gates.get(n)) for n in _dependents(plan).get(tid, [])]:
            if waiter in tasks and (cluster_of.get(waiter) == cluster_of.get(tid) or status(waiter) != "pending"):
                continue
            if waiter in gates and gstate.get(waiter, {}).get("status") != "pending":
                continue
            others = [d for d in (node.get("depends_on") or node.get("waits_for") or []) if d != tid]
            if all((status(d) == "done") if d in tasks else gstate.get(d, {}).get("status") == "passed"
                   for d in others):
                add_batch(cluster_batch(tid))
                break
    for members in batches:
        out.append({"kind": "review_lean", "tasks": members, "roast": any(high_risk(m) for m in members)})

    for gid, g in gates.items():
        if gstate.get(gid, {}).get("status", "pending") == "pending" and gid not in busy_gates \
                and all(status(t) == "done" for t in g.get("waits_for", []) if t in tasks) \
                and all(gstate.get(x, {}).get("status") == "passed" for x in g.get("waits_for", []) if x in gates):
            out.append({"kind": "gate", "gate": gid})

    busy_files = set()
    assigned = {a["task"] for a in out[:free_slots] if a["kind"] == "task"}
    for tid in busy_tasks | assigned:
        if tid in tasks:
            busy_files |= set(tasks[tid].get("files_hint", []))
    for tid in by_priority:
        if tid in ready:
            continue
        done = set(tstate.get(tid, {}).get("steps_done", []))
        steps = [n for n in (1, 2) if n not in done]
        if steps and not (set(tasks[tid].get("files_hint", [])) & busy_files):
            out.append({"kind": "pre_read", "task": tid, "steps": steps})
    return out[:free_slots]


def _write_json(path, data):
    try:
        from devstate import atomic_write_json
    except ImportError:
        tmp = f"{path}.tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return
    atomic_write_json(path, data)


def main(argv):
    if len(argv) < 3:
        print("uso: devgraph.py validate|analyze <plan.json> | next <plan.json> <state.json> --free N", file=sys.stderr)
        return 2
    cmd, plan_path = argv[1], argv[2]
    plan = load_plan(plan_path)
    if cmd == "validate":
        errors = validate(plan)
        print(json.dumps(errors, ensure_ascii=False))
        return 1 if errors else 0
    if cmd == "analyze":
        errors = validate(plan)
        if errors:
            print(json.dumps(errors, ensure_ascii=False))
            return 1
        _write_json(plan_path, analyze(plan))
        print(json.dumps(plan["analysis"], ensure_ascii=False))
        return 0
    if cmd == "next":
        with open(argv[3]) as f:
            state = json.load(f)
        free = int(argv[argv.index("--free") + 1]) if "--free" in argv else 1
        print(json.dumps(next_assignments(plan, state, free), ensure_ascii=False))
        return 0
    print(f"comando desconhecido: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
