import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(ROOT, "install.sh")


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "repo")
        for name in ("a", "b"):
            os.makedirs(os.path.join(self.repo, name))
            open(os.path.join(self.repo, name, "SKILL.md"), "w").close()
        os.makedirs(os.path.join(self.repo, "docs"))
        self.skills = os.path.join(self.tmp, "skills")
        os.makedirs(self.skills)
        self.backup = os.path.join(self.tmp, "backup")

    def install(self, *args):
        env = dict(os.environ, SKILLS_DIR=self.skills, BACKUP_DIR=self.backup, REPO_DIR=self.repo)
        return subprocess.run(["bash", INSTALL, *args], capture_output=True, text=True, env=env)

    def test_install_creates_symlinks(self):
        self.assertEqual(self.install().returncode, 0)
        for name in ("a", "b"):
            link = os.path.join(self.skills, name)
            self.assertTrue(os.path.islink(link))
            self.assertEqual(os.path.realpath(link), os.path.realpath(os.path.join(self.repo, name)))
        self.assertFalse(os.path.exists(os.path.join(self.skills, "docs")))

    def test_install_backs_up_real_dir_before_linking(self):
        os.makedirs(os.path.join(self.skills, "b"))
        with open(os.path.join(self.skills, "b", "x"), "w") as f:
            f.write("local")
        self.assertEqual(self.install().returncode, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.backup, "b", "x")))
        self.assertTrue(os.path.islink(os.path.join(self.skills, "b")))

    def test_install_is_idempotent(self):
        self.install()
        second = self.install()
        self.assertEqual(second.returncode, 0)
        self.assertFalse(os.path.exists(self.backup))
        self.assertIn("ok a", second.stdout)
        self.assertIn("ok b", second.stdout)

    def test_second_backup_in_same_dir_does_not_nest(self):
        os.makedirs(os.path.join(self.skills, "b"))
        self.install()
        os.remove(os.path.join(self.skills, "b"))
        os.makedirs(os.path.join(self.skills, "b"))
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(sorted(os.listdir(self.backup)), ["b", "b.1"])
        self.assertFalse(os.path.exists(os.path.join(self.backup, "b", "b")))

    def test_install_sets_versioned_hooks_path(self):
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        os.makedirs(os.path.join(self.repo, ".githooks"))
        self.install()
        result = subprocess.run(["git", "-C", self.repo, "config", "core.hooksPath"], capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), ".githooks")

    def test_dry_run_changes_nothing(self):
        result = self.install("--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(os.listdir(self.skills), [])


if __name__ == "__main__":
    unittest.main()
