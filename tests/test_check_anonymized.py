import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "scripts", "check-anonymized.sh")


class CheckAnonymizedTest(unittest.TestCase):
    # os testes usam um termo neutro (acmecorp) num FORBIDDEN_TERMS temporário; nenhum termo real entra no repo
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.terms = os.path.join(self.tmp, "terms.txt")
        with open(self.terms, "w") as f:
            f.write("acmecorp\n")

    def run_guard(self, content, terms=None):
        target = os.path.join(self.tmp, "file.md")
        with open(target, "w") as f:
            f.write(content)
        env = dict(os.environ, FORBIDDEN_TERMS=terms or self.terms)
        return subprocess.run(["bash", GUARD, target], capture_output=True, text=True, env=env)

    def test_guard_blocks_forbidden_term(self):
        result = self.run_guard("repo AcmeCorp-web\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("acmecorp", result.stdout.lower())

    def test_guard_passes_clean_file(self):
        result = self.run_guard("repo web-app\n")
        self.assertEqual(result.returncode, 0)

    def test_guard_checks_staged_content_not_working_tree(self):
        repo = os.path.join(self.tmp, "repo")
        subprocess.run(["git", "init", "-q", repo], check=True)
        target = os.path.join(repo, "a.md")
        with open(target, "w") as f:
            f.write("repo acmecorp-web\n")
        subprocess.run(["git", "-C", repo, "add", "a.md"], check=True)
        with open(target, "w") as f:
            f.write("repo web-app\n")
        env = dict(os.environ, FORBIDDEN_TERMS=self.terms)
        result = subprocess.run(["bash", GUARD], cwd=repo, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 1)

    def test_guard_fails_closed_without_terms_file(self):
        result = self.run_guard("repo web-app\n", terms=os.path.join(self.tmp, "missing.txt"))
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
