import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from validate_skills import load_skills, route, validate  # noqa: E402


class ValidateSkillsTest(unittest.TestCase):
    def test_repo_skills_are_valid(self):
        self.assertEqual(validate(ROOT), [])

    def test_detects_name_mismatch_and_missing_reference(self):
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "foo"))
        with open(os.path.join(root, "foo", "SKILL.md"), "w") as f:
            f.write("---\nname: bar\ndescription: faz algo\n---\n\nLeia `references/x.md`.\n")
        codes = sorted(e["code"] for e in validate(root))
        self.assertEqual(codes, ["missing_reference", "name_mismatch"])

    def test_cli_exit_code(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "validate_skills.py"), ROOT],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)


class RoutingTest(unittest.TestCase):
    def test_each_prompt_routes_to_its_skill(self):
        skills = load_skills(ROOT)
        with open(os.path.join(ROOT, "tests", "routing.json")) as f:
            cases = json.load(f)
        misses = []
        for expected, prompts in cases.items():
            for prompt in prompts:
                top = route(prompt, skills)[0]
                if top != expected:
                    misses.append(f"{prompt!r} → {top} (esperado {expected})")
        self.assertEqual(misses, [])


if __name__ == "__main__":
    unittest.main()
