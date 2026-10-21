import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(os.path.dirname(HERE), "scripts", "tracker_server.py")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TrackerServerTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.feature = os.path.join(self.root, "lembrete-aula")
        os.makedirs(self.feature)
        self.write("<html><body><main>v1</main></body></html>")
        self.port = free_port()
        self.proc = subprocess.Popen([sys.executable, SERVER, "--root", self.root, "--port", str(self.port)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                urllib.request.urlopen(self.url("/health"), timeout=1)
                break
            except OSError:
                time.sleep(0.1)

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait(timeout=5)

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def write(self, html):
        with open(os.path.join(self.feature, "tracker.html"), "w") as f:
            f.write(html)

    def get(self, path):
        with urllib.request.urlopen(self.url(path), timeout=3) as resp:
            return resp.read().decode()

    def test_serves_feature_tracker(self):
        self.assertIn("v1", self.get("/f/lembrete-aula"))

    def test_index_lists_features(self):
        self.assertIn("/f/lembrete-aula", self.get("/"))

    def test_unknown_feature_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/f/nao-existe")
        self.assertEqual(ctx.exception.code, 404)

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError):
            self.get("/f/..%2F..%2Fetc")

    def test_event_stream_fires_on_change(self):
        events = []
        resp = urllib.request.urlopen(self.url("/events?f=lembrete-aula"), timeout=10)

        def read():
            for raw in resp:
                line = raw.decode().strip()
                if line.startswith("data:"):
                    events.append(line)
                    return

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        time.sleep(0.5)
        self.write("<html><body><main>v2</main></body></html>")
        reader.join(timeout=5)
        self.assertEqual(events, ["data: update"])


if __name__ == "__main__":
    unittest.main()
