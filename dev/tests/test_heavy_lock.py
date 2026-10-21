import os
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = os.path.join(os.path.dirname(HERE), "scripts", "heavy_lock.sh")


class HeavyLockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = dict(os.environ, DEV_HEAVY_DIR=os.path.join(self.tmp, "heavy"), DEV_HEAVY_SLOTS="2")

    def test_max_two_concurrent(self):
        log = os.path.join(self.tmp, "log")
        cmd = f"echo start >> {log}; sleep 1; echo end >> {log}"
        procs = [subprocess.Popen(["bash", LOCK, "sh", "-c", cmd], env=self.env) for _ in range(4)]
        codes = [p.wait(timeout=30) for p in procs]
        self.assertEqual(codes, [0, 0, 0, 0])
        running, peak = 0, 0
        with open(log) as f:
            for line in f:
                running += 1 if line.strip() == "start" else -1
                peak = max(peak, running)
        self.assertEqual(peak, 2)

    def test_exit_code_propagates(self):
        result = subprocess.run(["bash", LOCK, "sh", "-c", "exit 7"], env=self.env)
        self.assertEqual(result.returncode, 7)

    def test_reclaims_slot_of_dead_pid(self):
        dead = subprocess.Popen(["true"])
        dead.wait()
        for i in (1, 2):
            slot = os.path.join(self.env["DEV_HEAVY_DIR"], f"slot-{i}")
            os.makedirs(slot)
            with open(os.path.join(slot, "pid"), "w") as f:
                f.write(str(dead.pid))
        start = time.time()
        result = subprocess.run(["bash", LOCK, "true"], env=self.env, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertLess(time.time() - start, 5)


if __name__ == "__main__":
    unittest.main()
