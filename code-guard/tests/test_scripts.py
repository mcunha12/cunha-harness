import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

from ledger import identity  # noqa: E402


def finding(severity, verification, category="catch-engolido", agent="review-resiliencia"):
    return {"id": "RES-001", "agent": agent, "severity": severity, "category": category, "verification": verification,
            "location": {"repo": "api-bff", "file": "src/x.ts", "lines": "1-2"}, "problem": "erro some"}


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.env = dict(os.environ, CODE_GUARD_HOME=self.home)

    def run_ledger(self, *args):
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, "ledger.py"), *args],
                                capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def append(self, findings, task):
        path = os.path.join(self.home, "f.json")
        with open(path, "w") as f:
            json.dump(findings, f)
        self.run_ledger("append", "--findings", path, "--repo", "api-bff", "--feature", "x", "--task", task,
                        "--loaded-domains", "resiliencia")

    def lines(self):
        with open(os.path.join(self.home, "ledger.jsonl")) as f:
            return [json.loads(x) for x in f if x.strip()]

    def triggers(self):
        return json.loads(self.run_ledger("triggers"))

    def test_identity(self):
        self.assertEqual(identity("review-seguranca", "BOLA/IDOR"), "review-seguranca:bola-idor")

    def test_append_only_confirmed_blocker_major(self):
        self.append([finding("MAJOR", "confirmado"), finding("MINOR", "confirmado"), finding("MAJOR", "descartado")], "T1")
        self.assertEqual(len(self.lines()), 1)

    def test_trigger_needs_two_tasks(self):
        for _ in range(3):
            self.append([finding("MAJOR", "confirmado")], "T1")
        self.assertEqual(self.triggers(), [])
        self.append([finding("MAJOR", "confirmado")], "T2")
        result = self.triggers()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["identity"], "review-resiliencia:catch-engolido")
        self.assertTrue(result[0]["domain_loaded"])

    def test_corrupted_line_is_skipped(self):
        self.append([finding("MAJOR", "confirmado")], "T1")
        with open(os.path.join(self.home, "ledger.jsonl"), "a") as f:
            f.write('{"truncad\n')
        self.append([finding("MAJOR", "confirmado")], "T2")
        self.append([finding("MAJOR", "confirmado")], "T2")
        self.assertEqual(len(self.triggers()), 1)

    def test_processed_waits_for_new_threshold(self):
        for task in ("T1", "T1", "T2"):
            self.append([finding("MAJOR", "confirmado")], task)
        self.run_ledger("mark-processed", "--identity", "review-resiliencia:catch-engolido", "--action", "created")
        self.assertEqual(self.triggers(), [])
        for task in ("T3", "T3", "T4"):
            self.append([finding("MAJOR", "confirmado")], task)
        self.assertEqual(len(self.triggers()), 1)


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "domains"))

    def check(self):
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, "check_budget.py"), self.root],
                                capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout or "[]")

    def write(self, name, lines):
        with open(os.path.join(self.root, name), "w") as f:
            f.write("\n".join(lines) + "\n")

    def test_budget_ok(self):
        self.write("core.md", ["# Núcleo", "- [RES] Faz X. — origem: review-resiliencia/catch-engolido"])
        self.assertEqual(self.check(), (0, []))

    def test_budget_over(self):
        self.write("core.md", ["linha"] * 151)
        code, issues = self.check()
        self.assertEqual(code, 1)
        self.assertIn("over_budget", [i["code"] for i in issues])

    def test_budget_missing_origin(self):
        self.write("domains/front.md", ["- [FRT] Faz X."])
        code, issues = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(issues[0]["code"], "missing_origin")


class OverlayTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        with open(os.path.join(self.home, "overlays.json"), "w") as f:
            json.dump({"overlays": [{"name": "acme", "remote_contains": ["acme"], "file": "acme.md",
                                     "learned": "company-acme.md", "skill": "vibecode-acme"}]}, f)
        self.repo = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", self.repo], check=True)

    def match(self):
        result = subprocess.run([sys.executable, os.path.join(SCRIPTS, "overlay.py"), "match", self.repo],
                                capture_output=True, text=True, env=dict(os.environ, OVERLAYS_HOME=self.home))
        return json.loads(result.stdout)

    def test_overlay_match(self):
        subprocess.run(["git", "-C", self.repo, "remote", "add", "origin", "https://gitlab.com/acme/x.git"], check=True)
        self.assertEqual(self.match()["name"], "acme")

    def test_overlay_no_match(self):
        subprocess.run(["git", "-C", self.repo, "remote", "add", "origin", "https://github.com/other/x.git"], check=True)
        self.assertEqual(self.match(), {})


if __name__ == "__main__":
    unittest.main()
