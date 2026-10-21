import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

from devgraph import affinity_clusters, critical_path, jaccard_distance, path_ahead, task_cost, validate  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
