import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

from capacity import task_workers  # noqa: E402


class TaskWorkersTest(unittest.TestCase):
    def test_build_and_qa_keep_two_cores(self):
        self.assertEqual(task_workers(cores=8, mem_free_gb=16)["workers"], 6)

    def test_free_memory_limits_workers(self):
        self.assertEqual(task_workers(cores=8, mem_free_gb=2.8)["workers"], 3)

    def test_never_below_one_worker(self):
        self.assertEqual(task_workers(cores=2, mem_free_gb=0.5)["workers"], 1)


if __name__ == "__main__":
    unittest.main()
