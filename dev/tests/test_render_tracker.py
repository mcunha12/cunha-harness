import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import devgraph  # noqa: E402
from render_tracker import render, render_dir  # noqa: E402

CHROME = os.environ.get("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
FLOW = os.path.join(ROOT, "master-review", "scripts", "mobile_flow.py")


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name)) as f:
        return json.load(f)


class RenderTrackerTest(unittest.TestCase):
    def setUp(self):
        self.plan = devgraph.analyze(fixture("plan-lembrete.json"))
        self.state = fixture("state-mockup.json")

    def test_render_fixture_shows_tasks_workers_and_critical_path(self):
        html = render(self.plan, self.state, [], [], [])
        for t in self.plan["tasks"]:
            self.assertIn(t["title"], html)
        self.assertIn("1 / 4", html)
        self.assertIn("caminho crítico (custo 48)", html)
        HTMLParser().feed(html)

    def test_worker_shows_opus_effort_of_the_task(self):
        state = copy.deepcopy(self.state)
        state["workers"][0]["assignment"]["from_step"] = 3
        state["tasks"]["T3"]["step_running"] = 3
        self.assertIn("avaliação · Opus medium", render(self.plan, state, [], [], []))
        next(t for t in self.plan["tasks"] if t["id"] == "T3")["opus_effort"] = "xhigh"
        self.assertIn("avaliação · Opus xhigh", render(self.plan, state, [], [], []))

    def test_render_requirements_phase_without_plan(self):
        state = copy.deepcopy(self.state)
        state.update(phase="requirements", tasks={}, gates={})
        html = render(None, state, [], [], [])
        self.assertIn("Requisitos", html)

    def test_render_dir_shows_situation_block(self):
        tmp = tempfile.mkdtemp()
        for name, data in (("plan.json", self.plan), ("state.json", self.state),
                           ("situation.json", {"at": "2026-10-21T15:10:00",
                                               "lines": ["T3 em implementação.", "T2 aguarda o cluster A."]})):
            with open(os.path.join(tmp, name), "w") as f:
                json.dump(data, f)
        with open(render_dir(tmp)) as f:
            html = f.read()
        self.assertIn("Situação agora", html)
        self.assertIn("T2 aguarda o cluster A.", html)
        self.assertLess(html.index("Situação agora"), html.index("Workers agora"))

    def test_corrupted_ledger_line_does_not_break_render(self):
        tmp = tempfile.mkdtemp()
        home = os.path.join(tmp, "cg")
        os.makedirs(home)
        with open(os.path.join(home, "ledger.jsonl"), "w") as f:
            f.write('{"feature": "lembrete-aula", "identity": "a:b", "task": "T1", "problem": "p"}\n{"truncad')
        for name, data in (("plan.json", self.plan), ("state.json", self.state)):
            with open(os.path.join(tmp, name), "w") as f:
                json.dump(data, f)
        os.environ["CODE_GUARD_HOME"] = home
        try:
            with open(render_dir(tmp)) as f:
                self.assertIn("a:b", f.read())
        finally:
            del os.environ["CODE_GUARD_HOME"]

    def test_heavy_kpi_uses_configured_slots_and_live_pids(self):
        tmp = tempfile.mkdtemp()
        for i, pid in ((1, os.getpid()), (2, 999999)):
            os.makedirs(os.path.join(tmp, f"slot-{i}"))
            with open(os.path.join(tmp, f"slot-{i}", "pid"), "w") as f:
                f.write(str(pid))
        os.environ.update(DEV_HEAVY_DIR=tmp, DEV_HEAVY_SLOTS="3")
        try:
            from render_tracker import heavy_status
            self.assertEqual(heavy_status(), (1, 3))
        finally:
            del os.environ["DEV_HEAVY_DIR"], os.environ["DEV_HEAVY_SLOTS"]

    @unittest.skipUnless(os.path.exists("/usr/bin/python3"), "sem python do sistema")
    def test_scripts_compile_on_system_python(self):
        scripts = [os.path.join(ROOT, d, "scripts", n) for d, n in (
            ("dev", "devgraph.py"), ("dev", "devstate.py"), ("dev", "render_tracker.py"),
            ("master-review", "mobile_flow.py"), ("code-guard", "ledger.py"),
            ("code-guard", "check_budget.py"), ("code-guard", "overlay.py"))]
        result = subprocess.run(["/usr/bin/python3", "-c",
                                 "import ast,sys\nfor p in sys.argv[1:]: ast.parse(open(p).read(), p)", *scripts],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_render_dir_writes_file(self):
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "plan.json"), "w") as f:
            json.dump(self.plan, f)
        with open(os.path.join(tmp, "state.json"), "w") as f:
            json.dump(self.state, f)
        path = render_dir(tmp)
        self.assertTrue(os.path.isfile(os.path.join(tmp, "tracker.html")))
        self.assertEqual(path, os.path.join(tmp, "tracker.html"))

    @unittest.skipUnless(os.path.exists(CHROME), "Chrome ausente")
    def test_no_horizontal_overflow_on_iphone_se(self):
        tmp = tempfile.mkdtemp()
        page = os.path.join(tmp, "tracker.html")
        with open(page, "w") as f:
            f.write(render(self.plan, self.state, [], [], []))
        out = os.path.join(tmp, "shots")
        subprocess.run([sys.executable, FLOW, "--url", "file://" + page, "--out", out, "--device", "iphone-se"],
                       check=True, capture_output=True, timeout=90)
        with open(os.path.join(out, "report.json")) as f:
            self.assertEqual(json.load(f)["scroll_width"], 375)
        shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
