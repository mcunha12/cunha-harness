#!/usr/bin/env python3
"""Grafo de tasks do /dev: validação, custo, caminho crítico, clusters e agendador."""
import json
import os
import sys

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
    print(f"comando desconhecido: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
