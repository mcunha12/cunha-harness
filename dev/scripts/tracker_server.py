#!/usr/bin/env python3
"""Servidor local do tracker: serve o tracker.html de cada feature e avisa o navegador quando ele muda (SSE)."""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
POLL_SECONDS = 0.5


def _features(root):
    return sorted(n for n in os.listdir(root) if SLUG.match(n) and os.path.isfile(os.path.join(root, n, "tracker.html")))


def _phase(root, slug):
    try:
        with open(os.path.join(root, slug, "state.json")) as f:
            return json.load(f).get("phase")
    except (OSError, ValueError):
        return None


def _tabs(root, current):
    open_ = [n for n in _features(root) if n == current or _phase(root, n) != "done"]
    if len(open_) < 2:
        return ""
    links = "".join(f'<a href="/f/{html.escape(n)}"{' aria-current="page"' if n == current else ""}>{html.escape(n)}</a>'
                    for n in open_)
    return f'<nav class="tabs" aria-label="Features">{links}</nav>'


def make_handler(root):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, content_type="text/html; charset=utf-8"):
            data = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _tracker(self, slug):
            if not SLUG.match(slug or ""):
                return None
            path = os.path.join(root, slug, "tracker.html")
            return path if os.path.isfile(path) else None

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/health":
                return self._send(200, "ok", "text/plain")
            if parsed.path == "/":
                return self._send(200, self._index())
            if parsed.path.startswith("/f/"):
                path = self._tracker(urllib.parse.unquote(parsed.path[3:]).strip("/"))
                if not path:
                    return self._send(404, "feature não encontrada", "text/plain; charset=utf-8")
                slug = os.path.basename(os.path.dirname(path))
                with open(path) as f:
                    return self._send(200, f.read().replace("<main>", "<main>" + _tabs(root, slug), 1))
            if parsed.path == "/events":
                slug = urllib.parse.parse_qs(parsed.query).get("f", [""])[0]
                path = self._tracker(slug)
                if not path:
                    return self._send(404, "feature não encontrada", "text/plain; charset=utf-8")
                return self._stream(path)
            return self._send(404, "não encontrado", "text/plain; charset=utf-8")

        def _index(self):
            names = _features(root)
            items = "".join(f'<li><a href="/f/{html.escape(n)}">{html.escape(n)}</a></li>' for n in names) or "<li>nenhuma feature</li>"
            return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Features</title>'
                    f'<meta name="viewport" content="width=device-width, initial-scale=1">'
                    f'<style>body{{font:16px system-ui;margin:0;padding:16px}}</style></head>'
                    f'<body><h1>Features do /dev</h1><ul>{items}</ul></body></html>')

        def _stream(self, path):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            # a lista de features entra na assinatura para a aba de uma feature nova aparecer sem F5
            def signature(previous):
                mtime = os.path.getmtime(path) if os.path.exists(path) else previous[0]
                return mtime, _features(root)

            last = signature((None, None))
            beat = time.time()
            try:
                while True:
                    time.sleep(POLL_SECONDS)
                    current = signature(last)
                    if current != last:
                        last = current
                        self.wfile.write(b"data: update\n\n")
                        self.wfile.flush()
                    elif time.time() - beat > 15:
                        beat = time.time()
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.path.expanduser("~/.claude/dev/features"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DEV_TRACKER_PORT", "4777")))
    args = parser.parse_args(argv)
    os.makedirs(args.root, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.root))
    server.daemon_threads = True
    print(f"http://localhost:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
