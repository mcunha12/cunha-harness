import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "mobile_flow.py")
FLOW = "file://" + os.path.join(HERE, "fixtures", "flow.html")
CHROME = os.environ.get("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def run_flow(out, *args):
    result = subprocess.run([sys.executable, SCRIPT, "--url", FLOW, "--out", out, *args],
                            capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    with open(os.path.join(out, "report.json")) as f:
        return json.load(f)


@unittest.skipUnless(os.path.exists(CHROME), "Chrome ausente")
class MobileFlowTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def test_iphone_se_viewport_and_no_overflow(self):
        report = run_flow(self.out, "--device", "iphone-se")
        self.assertEqual(report["viewport"], {"width": 375, "height": 667, "dpr": 2})
        self.assertEqual(report["scroll_width"], 375)
        self.assertEqual(png_size(os.path.join(self.out, "inicial.png")), (750, 1334))

    def test_click_path(self):
        steps = os.path.join(self.out, "steps.json")
        with open(steps, "w") as f:
            json.dump([{"click": "#go"}, {"text": "#out"}, {"shot": "depois"}], f)
        report = run_flow(self.out, "--device", "iphone-se", "--steps", steps)
        self.assertEqual(report["steps"][1]["value"], "clicado")
        self.assertTrue(os.path.exists(os.path.join(self.out, "depois.png")))

    def test_missing_selector_marks_step_and_keeps_report(self):
        steps = os.path.join(self.out, "steps.json")
        with open(steps, "w") as f:
            json.dump([{"click": "#nao-existe"}, {"shot": "depois"}], f)
        report = run_flow(self.out, "--device", "iphone-se", "--steps", steps)
        self.assertFalse(report["steps"][0]["ok"])
        self.assertTrue(report["steps"][1]["ok"])

    def test_desktop(self):
        report = run_flow(self.out, "--device", "desktop")
        self.assertEqual(report["viewport"]["width"], 1440)


if __name__ == "__main__":
    unittest.main()
