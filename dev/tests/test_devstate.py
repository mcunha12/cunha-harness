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

    def test_step_done_marks_step_and_checkpoint(self):
        s = devstate.step_started(self.state, "T3", 4, 1)
        s = devstate.step_done(s, "T3", 4, "tasks/T3/plan.md")
        self.assertIn(4, s["tasks"]["T3"]["steps_done"])
        self.assertIsNone(s["tasks"]["T3"]["step_running"])
        self.assertEqual(s["checkpoint"]["note"], "T3 passo 4 concluído")

    def test_task_implemented_after_required_steps(self):
        s = self.state
        for step in (1, 2, 3, 5):
            s = devstate.step_done(s, "T3", step, None, required=[1, 2, 3, 5])
        self.assertEqual(s["tasks"]["T3"]["status"], "implemented")

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

    def test_pause_clears_running_steps_and_workers(self):
        self.state["phase"] = "execution"
        s = devstate.step_started(self.state, "T3", 4, 1)
        s = devstate.pause(s, "stop")
        self.assertIsNone(s["tasks"]["T3"]["step_running"])
        self.assertTrue(all(w["assignment"] is None for w in s["workers"]))

    def test_reset_steps_drops_steps_from_n_and_reopens_task(self):
        s = self.state
        for step in (1, 2, 3, 4, 5):
            s = devstate.step_done(s, "T3", step, f"s{step}")
        s = devstate.set_task_status(s, "T3", "done")
        s = devstate.reset_steps(s, "T3", 2)
        self.assertEqual(s["tasks"]["T3"]["steps_done"], [1])
        self.assertEqual(s["tasks"]["T3"]["status"], "pending")
        self.assertNotIn("2", s["tasks"]["T3"]["outputs"])

    def test_step_started_refuses_step_already_done(self):
        s = devstate.step_done(self.state, "T3", 1, "tasks/T3/scope.md")
        with self.assertRaises(devstate.StepConflict):
            devstate.step_started(s, "T3", 1, 1)

    def test_step_started_refuses_step_already_running(self):
        s = devstate.step_started(self.state, "T3", 2, 1)
        with self.assertRaises(devstate.StepConflict):
            devstate.step_started(s, "T3", 2, 2)

    def test_step_started_force_reopens(self):
        s = devstate.step_done(self.state, "T3", 1, "tasks/T3/scope.md")
        s = devstate.step_started(s, "T3", 1, 1, force=True)
        self.assertEqual(s["tasks"]["T3"]["step_running"], 1)

    def test_baseline_failures_recorded(self):
        s = devstate.set_baseline(self.state, ["src/test/a.test.ts > caso x", "src/test/b.test.ts"])
        self.assertEqual(s["baseline_failures"], ["src/test/a.test.ts > caso x", "src/test/b.test.ts"])
        self.assertIn("baseline", s["checkpoint"]["note"])

    def test_stale_files(self):
        with open(os.path.join(self.tmp, "a.txt"), "w") as f:
            f.write("1")
        hashes = devstate.hash_files(self.tmp, ["a.txt"])
        with open(os.path.join(self.tmp, "a.txt"), "w") as f:
            f.write("2")
        self.assertEqual(devstate.stale_files(self.tmp, hashes), ["a.txt"])


if __name__ == "__main__":
    unittest.main()
