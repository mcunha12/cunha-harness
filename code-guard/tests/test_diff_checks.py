import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "diff_checks.py")


def git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)


def write(repo, name, text):
    path = os.path.join(repo, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class DiffChecksTest(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.home = tempfile.mkdtemp()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        write(self.repo, "vitest.config.ts", "export default { test: { coverage: { thresholds: { lines: 80 } } } }\n")
        write(self.repo, "src/a.ts", "export const a = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feat")

    def run_checks(self):
        env = dict(os.environ, CODE_GUARD_HOME=self.home)
        result = subprocess.run([sys.executable, SCRIPT, "run", "--repo", self.repo, "--base", "main", "--uncommitted"],
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["findings"]

    def ids(self):
        return sorted({f["category"] for f in self.run_checks()})

    def test_flags_bar_weakening(self):
        write(self.repo, "src/a.ts", "// @ts-ignore\nexport const a: number = 'x'\n")
        write(self.repo, "src/a.test.ts", "it.skip('works', () => {})\n")
        write(self.repo, ".eslintrc.json", '{"rules": {"no-console": "off"}}\n')
        write(self.repo, "vitest.config.ts", "export default { test: { coverage: { thresholds: { lines: 70 } } } }\n")
        self.assertEqual(self.ids(), ["coverage-lowered", "lint-rule-weakened", "test-skip", "ts-suppress"])

    def test_reports_file_and_new_line_number(self):
        write(self.repo, "src/a.ts", "export const a = 1\n// @ts-ignore\nexport const b: number = 'x'\n")
        finding = self.run_checks()[0]
        self.assertEqual(finding["location"]["file"], "src/a.ts")
        self.assertEqual(finding["location"]["lines"], "2")
        self.assertEqual(finding["severity"], "MAJOR")

    def test_suppression_with_reason_is_allowed(self):
        write(self.repo, "src/a.ts", "// eslint-disable-next-line no-console -- log de auditoria exigido\nconsole.log(1)\n")
        self.assertEqual(self.ids(), [])

    def test_learned_check_runs(self):
        os.makedirs(os.path.join(self.home, "learned"))
        with open(os.path.join(self.home, "learned", "checks.json"), "w") as f:
            json.dump([{"id": "json-empty-on-error", "pattern": r"res\.end\(JSON\.stringify\(\[\]\)\)", "files": r"\.js$",
                        "message": "erro respondido como lista vazia", "origin": "review-resiliencia/catch-engolido"}], f)
        write(self.repo, "server.js", "try { x() } catch (e) {\n  res.end(JSON.stringify([]))\n}\n")
        self.assertEqual(self.ids(), ["json-empty-on-error"])

    def add_check(self, pattern):
        with open(os.path.join(self.home, "ledger.jsonl"), "w") as f:
            f.write(json.dumps({"identity": "review-resiliencia:catch-engolido",
                                "evidence": "} catch (err) {\n  res.end(JSON.stringify([]));\n}"}) + "\n")
        env = dict(os.environ, CODE_GUARD_HOME=self.home)
        return subprocess.run([sys.executable, SCRIPT, "add-check", "--id", "json-empty", "--pattern", pattern,
                               "--files", r"\.js$", "--message", "erro como lista vazia",
                               "--origin", "review-resiliencia/catch-engolido",
                               "--identity", "review-resiliencia:catch-engolido"], capture_output=True, text=True, env=env)

    def test_add_check_requires_match_on_real_occurrence(self):
        self.assertEqual(self.add_check(r"res\.end\(JSON\.stringify\(\[\]\)\)").returncode, 0)
        with open(os.path.join(self.home, "learned", "checks.json")) as f:
            self.assertEqual([c["id"] for c in json.load(f)], ["json-empty"])

    def test_add_check_rejects_pattern_without_real_match(self):
        self.assertEqual(self.add_check(r"nunca-aparece").returncode, 1)
        self.assertFalse(os.path.exists(os.path.join(self.home, "learned", "checks.json")))


if __name__ == "__main__":
    unittest.main()
