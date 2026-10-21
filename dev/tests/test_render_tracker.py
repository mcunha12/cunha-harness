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
