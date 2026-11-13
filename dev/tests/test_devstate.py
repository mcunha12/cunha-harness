import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import devstate  # noqa: E402


class DevstateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = devstate.init(self.tmp, "x", {"r": {"path": self.tmp, "feature_branch": "feat/x", "base": "main"}})
        self.state["tasks"]["T3"] = devstate.new_task_state()

    def test_atomic_write_keeps_old_file_on_failure(self):
        path = os.path.join(self.tmp, "s.json")
        devstate.atomic_write_json(path, {"a": 1})
        with mock.patch("devstate.json.dump", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                devstate.atomic_write_json(path, {"a": 2})
        with open(path) as f:
            self.assertEqual(json.load(f), {"a": 1})
        self.assertEqual([n for n in os.listdir(self.tmp) if n.endswith(".tmp")], [])

    def test_close_merges_repo_entry(self):
        s = devstate.set_closing(self.state, "r", {"mr": "!1", "status": "watching"})
        s = devstate.set_closing(s, "r", {"status": "cleaned"})
        self.assertEqual(s["closing"]["r"]["mr"], "!1")
        self.assertEqual(s["closing"]["r"]["status"], "cleaned")

    def test_pause_and_resume(self):
        self.state["phase"] = "execution"
        s = devstate.pause(self.state, "stop")
        self.assertEqual(s["phase"], "paused")
        self.assertEqual(s["paused"]["reason"], "stop")
        s = devstate.resume(s)
        self.assertEqual(s["phase"], "execution")
        self.assertIsNone(s["paused"])

    def test_wait_queues_feature_behind_another(self):
        dep = tempfile.mkdtemp()
        devstate._save(dep, devstate.init(dep, "dep", {}))
        s = devstate.wait_for(self.state, dep)
        self.assertEqual(s["waits_for"], dep)
        self.assertIn("dep", s["checkpoint"]["note"])
        self.assertFalse(devstate.is_ready(s))
        devstate._save(dep, devstate.set_phase(devstate.load(dep), "done"))
        self.assertTrue(devstate.is_ready(s))

    def test_feature_without_wait_is_ready(self):
        self.assertTrue(devstate.is_ready(self.state))

    def test_ready_cli_exit_code_follows_dependency(self):
        dep = tempfile.mkdtemp()
        devstate._save(dep, devstate.init(dep, "dep", {}))
        devstate._save(self.tmp, self.state)
        self.assertEqual(devstate.main(["devstate.py", "wait", self.tmp, dep]), 0)
        self.assertEqual(devstate.main(["devstate.py", "ready", self.tmp]), 1)
        devstate._save(dep, devstate.set_phase(devstate.load(dep), "done"))
        self.assertEqual(devstate.main(["devstate.py", "ready", self.tmp]), 0)

    def test_set_phase(self):
        s = devstate.set_phase(self.state, "execution")
        self.assertEqual(s["phase"], "execution")
        self.assertEqual(devstate.resume(devstate.pause(s, "stop"))["phase"], "execution")

    def test_stop_returns_running_task_to_pending_via_cli(self):
        devstate._save(self.tmp, devstate.set_phase(self.state, "execution"))
        self.assertEqual(devstate.main(["devstate.py", "task-status", self.tmp, "T3", "running"]), 0)
        self.assertEqual(devstate.main(["devstate.py", "pause", self.tmp, "stop"]), 0)
        self.assertEqual(devstate.load(self.tmp)["tasks"]["T3"]["status"], "pending")

    def test_redispatch_counts_attempts_via_cli(self):
        devstate._save(self.tmp, self.state)
        for _ in range(2):
            devstate.main(["devstate.py", "task-status", self.tmp, "T3", "running"])
        self.assertEqual(devstate.load(self.tmp)["tasks"]["T3"]["attempts"], 2)

    def test_pause_reopens_final_tests_and_gate(self):
        self.state["phase"] = "execution"
        self.state["gates"] = {"G1": {"status": "testing", "report": None}}
        self.assertEqual(devstate.pause(self.state, "stop")["gates"]["G1"]["status"], "pending")
        self.state["gates"] = {"G1": {"status": "running", "report": None}}
        self.assertEqual(devstate.pause(self.state, "stop")["gates"]["G1"]["status"], "tested")

    def test_baseline_failures_recorded(self):
        s = devstate.set_baseline(self.state, ["src/test/a.test.ts > caso x", "src/test/b.test.ts"])
        self.assertEqual(s["baseline_failures"], ["src/test/a.test.ts > caso x", "src/test/b.test.ts"])
        self.assertIn("baseline", s["checkpoint"]["note"])

    def test_cost_refuses_aggregate_gate_line_and_duplicates(self):
        ok = {"agent_role": "scan", "model": "haiku", "task": "gate", "tokens": 10, "duration_ms": 5}
        self.assertIsNone(devstate.cost_error(self.tmp, ok))
        self.assertIn("duration_ms", devstate.cost_error(self.tmp, dict(ok, duration_ms=0)))
        devstate.append_jsonl(os.path.join(self.tmp, "costs.jsonl"), ok)
        self.assertIn("idêntica", devstate.cost_error(self.tmp, ok))


if __name__ == "__main__":
    unittest.main()
