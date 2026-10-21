import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

from devgraph import (affinity_clusters, critical_path, jaccard_distance, next_assignments,  # noqa: E402
                      path_ahead, task_cost, validate)


def load_fixture(name):
    with open(os.path.join(HERE, "fixtures", name)) as f:
        return json.load(f)


def chain_plan(n, gate_waits):
    tasks = []
    for i in range(1, n + 1):
        deps = [f"T{i - 1}"] if i > 1 else []
        tasks.append({"id": f"T{i}", "title": f"t{i}", "repo": "r", "files_hint": [], "complexity": 1,
                      "risk": 1, "depends_on": deps, "changes_behavior": False, "has_ui": False})
    return {"feature": "x", "repos": ["r"], "tasks": tasks,
            "gates": [{"id": "G1", "title": "fim", "waits_for": gate_waits}]}


class DevgraphCoreTest(unittest.TestCase):
    def setUp(self):
        self.plan = load_fixture("plan-lembrete.json")

    def task(self, tid):
        return next(t for t in self.plan["tasks"] if t["id"] == tid)

    def test_fixture_is_valid(self):
        self.assertEqual(validate(self.plan), [])

    def test_cost(self):
        self.assertEqual(task_cost(self.task("T1")), 15)
        self.assertEqual(task_cost(self.task("T4")), 2)

    def test_path_ahead(self):
        self.assertEqual(path_ahead(self.plan), {"T1": 48, "T2": 21, "T3": 33, "T4": 23, "T5": 21, "G1": 12,
                                                 "T6": 12, "T7": 8, "T8": 4, "G2": 0})

    def test_critical_path(self):
        self.assertEqual(critical_path(self.plan), ["T1", "T3", "T5", "G1", "T6", "T8", "G2"])

    def test_cycle(self):
        plan = copy.deepcopy(self.plan)
        self.task_in(plan, "T1")["depends_on"] = ["T2"]
        self.assertIn({"code": "cycle", "nodes": ["T1", "T2", "T1"]}, validate(plan))

    def test_unknown_dependency(self):
        plan = copy.deepcopy(self.plan)
        extra = copy.deepcopy(self.task("T4"))
        extra.update(id="T9", depends_on=["T99"])
        plan["tasks"].append(extra)
        plan["gates"][1]["waits_for"].append("T9")
        self.assertIn({"code": "unknown_dependency", "node": "T9", "dep": "T99"}, validate(plan))

    def test_missing_final_gate(self):
        plan = copy.deepcopy(self.plan)
        plan["gates"] = [g for g in plan["gates"] if g["id"] != "G2"]
        self.assertIn("missing_final_gate", [e["code"] for e in validate(plan)])

    def test_too_many_tasks_between_gates(self):
        self.assertIn({"code": "too_many_tasks_between_gates", "gate": "G1", "count": 7},
                      validate(chain_plan(7, ["T7"])))

    def test_invalid_score(self):
        plan = copy.deepcopy(self.plan)
        self.task_in(plan, "T1")["risk"] = 6
        self.assertIn({"code": "invalid_score", "task": "T1", "field": "risk"}, validate(plan))

    @staticmethod
    def task_in(plan, tid):
        return next(t for t in plan["tasks"] if t["id"] == tid)


class AffinityTest(unittest.TestCase):
    def setUp(self):
        self.plan = load_fixture("plan-lembrete.json")

    def test_jaccard(self):
        self.assertAlmostEqual(jaccard_distance({"a", "b"}, {"b", "c"}), 2 / 3, places=4)

    def test_jaccard_empty(self):
        self.assertEqual(jaccard_distance(set(), set()), 1.0)

    def test_fixture_clusters(self):
        self.assertEqual(affinity_clusters(self.plan),
                         {"A": ["T1", "T2", "T3"], "B": ["T4", "T5"], "C": ["T6", "T7", "T8"]})

    def test_max_size(self):
        plan = chain_plan(5, ["T5"])
        for t in plan["tasks"]:
            t["files_hint"] = ["shared.ts"]
        clusters = affinity_clusters(plan)
        self.assertLessEqual(max(len(v) for v in clusters.values()), 4)
        self.assertEqual(sum(len(v) for v in clusters.values()), 5)

    def test_cross_repo_never_clusters(self):
        plan = chain_plan(2, ["T2"])
        plan["tasks"][0].update(repo="a", files_hint=["x.ts"])
        plan["tasks"][1].update(repo="b", files_hint=["x.ts"])
        self.assertEqual(len(affinity_clusters(plan)), 2)


def free_worker(state, slot=1):
    state["workers"][slot - 1]["assignment"] = None


def set_task(state, tid, status, steps=(1, 2, 3, 4, 5)):
    state["tasks"][tid].update(status=status, steps_done=list(steps), step_running=None)


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        self.plan = load_fixture("plan-lembrete.json")
        self.state = load_fixture("state-mockup.json")

    def fresh_state(self):
        state = copy.deepcopy(self.state)
        for tid in state["tasks"]:
            set_task(state, tid, "pending", ())
        for w in state["workers"]:
            w["assignment"] = None
        return state

    def test_mockup_moment_fills_with_pre_reads(self):
        self.assertEqual(next_assignments(self.plan, self.state, 3),
                         [{"kind": "pre_read", "task": "T5", "steps": [1, 2]},
                          {"kind": "pre_read", "task": "T6", "steps": [1, 2]},
                          {"kind": "pre_read", "task": "T7", "steps": [1, 2]}])

    def test_cluster_batch_when_last_task_implemented(self):
        state = copy.deepcopy(self.state)
        free_worker(state)
        set_task(state, "T3", "implemented")
        self.assertEqual(next_assignments(self.plan, state, 1),
                         [{"kind": "review_lean", "tasks": ["T2", "T3"], "roast": False}])

    def test_high_risk_reviewed_alone(self):
        state = self.fresh_state()
        set_task(state, "T1", "implemented")
        self.assertIn({"kind": "review_lean", "tasks": ["T1"], "roast": True}, next_assignments(self.plan, state, 4))

    def test_no_stacking_on_high_risk(self):
        state = self.fresh_state()
        set_task(state, "T1", "implemented")
        kinds = [(a["kind"], a.get("task")) for a in next_assignments(self.plan, state, 4)]
        self.assertNotIn(("task", "T2"), kinds)

    def test_early_review_when_dependent_waits(self):
        state = self.fresh_state()
        set_task(state, "T1", "done")
        set_task(state, "T4", "done")
        set_task(state, "T3", "implemented")
        state["tasks"]["T2"].update(steps_done=[1, 2], step_running=3)
        self.assertIn({"kind": "review_lean", "tasks": ["T3"], "roast": False}, next_assignments(self.plan, state, 4))

    def test_gate_ready(self):
        state = self.fresh_state()
        for tid in ("T1", "T2", "T3", "T4", "T5"):
            set_task(state, tid, "done")
        self.assertIn({"kind": "gate", "gate": "G1"}, next_assignments(self.plan, state, 4))

    def test_stack_inside_cluster(self):
        plan = copy.deepcopy(self.plan)
        plan["tasks"][0]["risk"] = 3
        state = self.fresh_state()
        set_task(state, "T1", "implemented")
        self.assertIn({"kind": "task", "task": "T2", "from_step": 1, "stack_on": "T1"},
                      next_assignments(plan, state, 4))

    def test_priority_by_path_ahead(self):
        state = self.fresh_state()
        set_task(state, "T1", "done")
        tasks = [a["task"] for a in next_assignments(self.plan, state, 4) if a["kind"] == "task"]
        self.assertLess(tasks.index("T3"), tasks.index("T2"))

    def test_pre_read_skips_files_of_task_assigned_in_same_batch(self):
        plan = copy.deepcopy(self.plan)
        plan["tasks"][1]["files_hint"] = list(plan["tasks"][0]["files_hint"])
        plan["analysis"] = {}
        state = self.fresh_state()
        out = next_assignments(plan, state, 4)
        self.assertIn({"kind": "task", "task": "T1", "from_step": 1, "stack_on": None}, out)
        self.assertNotIn("T2", [a.get("task") for a in out if a["kind"] == "pre_read"])

    def test_no_slots(self):
        self.assertEqual(next_assignments(self.plan, self.state, 0), [])


if __name__ == "__main__":
    unittest.main()
