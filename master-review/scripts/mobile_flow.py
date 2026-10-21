#!/usr/bin/env python3
"""Fluxo real de cliques em Chrome headless com emulação de aparelho via CDP (stdlib apenas)."""
import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

CHROME = os.environ.get("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
DEVICES = {
    "iphone-se": {"width": 375, "height": 667, "dpr": 2, "mobile": True,
                  "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                        "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"},
    "desktop": {"width": 1440, "height": 900, "dpr": 1, "mobile": False, "ua": None},
}


class WebSocket:
    def __init__(self, url):
        rest = url.split("://", 1)[1]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                   f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(request.encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("handshake encerrado")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.split(b"\r\n", 1)[0].decode())
        self.buffer = head.split(b"\r\n\r\n", 1)[1]

    def _exact(self, n):
        while len(self.buffer) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("conexão encerrada")
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def send(self, text):
        payload = text.encode()
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def recv(self):
        message = b""
        while True:
            b1, b2 = self._exact(2)
            opcode, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            data = self._exact(n)
            if opcode == 0x8:
                raise ConnectionError("websocket fechado")
            if opcode in (0x1, 0x0):
                message += data
                if b1 & 0x80:
                    return message.decode()

    def close(self):
        self.sock.close()


class Page:
    def __init__(self, ws):
        self.ws, self.next_id, self.events = ws, 0, []

    def call(self, method, **params):
        self.next_id += 1
        self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.next_id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    def wait_event(self, name, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for i, ev in enumerate(self.events):
                if ev.get("method") == name:
                    return self.events.pop(i)
            self.events.append(json.loads(self.ws.recv()))
        raise TimeoutError(name)

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"].get("text", expression))
        return result.get("result", {}).get("value")


def launch_chrome():
    profile = tempfile.mkdtemp(prefix="mobile-flow-")
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                             "--remote-debugging-port=0", "--remote-allow-origins=*", f"--user-data-dir={profile}",
                             "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    port_file = os.path.join(profile, "DevToolsActivePort")
    deadline = time.time() + 20
    while not (os.path.exists(port_file) and open(port_file).read().strip()):
        if time.time() > deadline:
            proc.kill()
            raise TimeoutError("Chrome não abriu a porta de debug")
        time.sleep(0.1)
    port = int(open(port_file).read().split()[0])
    return proc, profile, port


def page_ws_url(port):
    deadline = time.time() + 10
    while time.time() < deadline:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list") as resp:
            pages = [t for t in json.load(resp) if t.get("type") == "page"]
        if pages:
            return pages[0]["webSocketDebuggerUrl"]
        time.sleep(0.2)
    raise TimeoutError("nenhuma aba encontrada")


def wait_selector(page, selector, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page.evaluate(f"!!document.querySelector({json.dumps(selector)})"):
            return True
        time.sleep(0.2)
    return False


def shoot(page, out, name, full=False):
    params = {"format": "png"}
    if full:
        params["captureBeyondViewport"] = True
    data = page.call("Page.captureScreenshot", **params)["data"]
    path = os.path.join(out, f"{name}.png")
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))
    return path


def run_step(page, out, step):
    try:
        return _run_step(page, out, step)
    except Exception as exc:  # passo quebrado vira ok false e o fluxo segue
        return {**step, "ok": False, "error": str(exc)}


def _run_step(page, out, step):
    sel = json.dumps
    for key in ("click", "text"):
        if key in step and not page.evaluate(f"!!document.querySelector({sel(step[key])})"):
            return {**step, "ok": False, "error": "seletor não encontrado"}
    if "type" in step and not page.evaluate(f"!!document.querySelector({sel(step['type'][0])})"):
        return {**step, "ok": False, "error": "seletor não encontrado"}
    if "click" in step:
        page.evaluate(f"document.querySelector({sel(step['click'])}).click()")
        time.sleep(0.3)
    elif "type" in step:
        target, text = step["type"]
        page.evaluate(f"document.querySelector({sel(target)}).focus()")
        page.call("Input.insertText", text=text)
    elif "wait" in step:
        if isinstance(step["wait"], (int, float)):
            time.sleep(step["wait"] / 1000)
        elif not wait_selector(page, step["wait"]):
            return {**step, "ok": False}
    elif "text" in step:
        return {**step, "ok": True, "value": page.evaluate(f"document.querySelector({sel(step['text'])})?.textContent")}
    elif "shot" in step:
        return {**step, "ok": True, "path": shoot(page, out, step["shot"], step.get("full", False))}
    return {**step, "ok": True}


def run(url, out, device, steps):
    os.makedirs(out, exist_ok=True)
    spec = DEVICES[device]
    proc, profile, port = launch_chrome()
    ws = None
    try:
        ws = WebSocket(page_ws_url(port))
        page = Page(ws)
        page.call("Page.enable")
        page.call("Emulation.setDeviceMetricsOverride", width=spec["width"], height=spec["height"],
                  deviceScaleFactor=spec["dpr"], mobile=spec["mobile"])
        if spec["mobile"]:
            page.call("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
            page.call("Emulation.setUserAgentOverride", userAgent=spec["ua"])
        page.call("Page.navigate", url=url)
        page.wait_event("Page.loadEventFired")
        results = [run_step(page, out, s) for s in (steps or [{"shot": "inicial"}])]
        report = {"device": device, "url": url,
                  "viewport": {"width": spec["width"], "height": spec["height"], "dpr": spec["dpr"]},
                  "scroll_width": page.evaluate("document.documentElement.scrollWidth"), "steps": results}
    finally:
        if ws:
            ws.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
    with open(os.path.join(out, "report.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--device", choices=sorted(DEVICES), default="iphone-se")
    parser.add_argument("--steps")
    args = parser.parse_args(argv)
    steps = None
    if args.steps:
        with open(args.steps) as f:
            steps = json.load(f)
    report = run(args.url, args.out, args.device, steps)
    print(json.dumps({"scroll_width": report["scroll_width"], "viewport": report["viewport"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
