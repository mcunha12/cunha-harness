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

    def test_stale_files(self):
        with open(os.path.join(self.tmp, "a.txt"), "w") as f:
            f.write("1")
        hashes = devstate.hash_files(self.tmp, ["a.txt"])
        with open(os.path.join(self.tmp, "a.txt"), "w") as f:
            f.write("2")
        self.assertEqual(devstate.stale_files(self.tmp, hashes), ["a.txt"])


if __name__ == "__main__":
    unittest.main()
