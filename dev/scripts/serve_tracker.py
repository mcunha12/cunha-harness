#!/usr/bin/env python3
"""Serve ~/.claude/dev/features em localhost e recarrega o tracker.html sozinho quando o arquivo muda."""
import http.server
import os
import sys
import urllib.parse

ROOT = os.path.expanduser("~/.claude/dev/features")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

# Pergunta o mtime a cada 1,5 s e recarrega mantendo a rolagem.
RELOAD = b"""<script>(()=>{const p=location.pathname;let m=null;
const k='scroll:'+p;try{const y=sessionStorage.getItem(k);if(y)scrollTo(0,+y)}catch(e){}
setInterval(async()=>{try{const r=await fetch('/__mtime?f='+encodeURIComponent(p),{cache:'no-store'});
const t=await r.text();if(m!==null&&t!==m){try{sessionStorage.setItem(k,scrollY)}catch(e){}location.reload()}m=t}catch(e){}},1500)})()</script>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass

    def _path(self, url_path):
        full = os.path.realpath(os.path.join(ROOT, url_path.lstrip("/")))
        return full if full.startswith(os.path.realpath(ROOT)) else None

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/__mtime":
            f = self._path(urllib.parse.parse_qs(url.query).get("f", [""])[0])
            body = str(os.path.getmtime(f)).encode() if f and os.path.isfile(f) else b"0"
            return self._send(body, "text/plain")
        f = self._path(urllib.parse.unquote(url.path))
        if f and f.endswith(".html") and os.path.isfile(f):
            with open(f, "rb") as fh:
                html = fh.read()
            html = html.replace(b"</body>", RELOAD + b"</body>") if b"</body>" in html else html + RELOAD
            return self._send(html, "text/html; charset=utf-8")
        return super().do_GET()

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}/")
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
