"""Minimal Chrome DevTools Protocol client (no third-party deps)."""
import base64, json, os, socket, ssl, struct, sys, time, urllib.request


class WS:
    def __init__(self, url):
        # ws://host:port/path
        assert url.startswith("ws://")
        rest = url[5:]
        hostport, _, path = rest.partition("/")
        path = "/" + path
        host, _, port = hostport.partition(":")
        port = int(port or 80)
        self.sock = socket.create_connection((host, port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("handshake failed")
            buf += chunk
        head, _, self.rest = buf.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise RuntimeError("handshake rejected: " + head.decode("latin1"))

    def _recv_exact(self, n):
        while len(self.rest) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("socket closed")
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def recv_frame(self):
        b1, b2 = self._recv_exact(2)
        fin = b1 & 0x80
        opcode = b1 & 0x0F
        masked = b2 & 0x80
        ln = b2 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", self._recv_exact(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", self._recv_exact(8))[0]
        mask = self._recv_exact(4) if masked else None
        data = self._recv_exact(ln)
        if mask:
            data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
        return opcode, fin, data

    def send_text(self, text):
        payload = text.encode()
        header = bytearray([0x81])
        n = len(payload)
        mask = os.urandom(4)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        header += mask
        masked = bytes(c ^ mask[i % 4] for i, c in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class CDP:
    def __init__(self, ws_url):
        self.ws = WS(ws_url)
        self.id = 0

    def call(self, method, params=None, timeout=60):
        self.id += 1
        mid = self.id
        self.ws.send_text(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        buf = b""
        msg_op = 0
        while time.time() < deadline:
            op, fin, data = self.ws.recv_frame()
            if op == 0x8:
                raise RuntimeError("ws closed")
            if op == 0x9:  # ping -> pong
                continue
            buf += data
            if not fin:
                continue
            try:
                msg = json.loads(buf.decode())
            except Exception:
                buf = b""
                continue
            buf = b""
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(json.dumps(msg["error"]))
                return msg.get("result")
        raise TimeoutError(method)


def targets(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10) as r:
        return json.loads(r.read().decode())


def pick_page(port, prefer="127.0.0.1"):
    ts = [t for t in targets(port) if t.get("type") == "page"]
    for t in ts:
        if prefer in (t.get("url") or ""):
            return t
    return ts[0] if ts else None


def evaluate(page, expr, await_promise=False):
    c = CDP(page["webSocketDebuggerUrl"])
    try:
        res = c.call("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise,
            "userGesture": True,
        }, timeout=120)
        return res
    finally:
        c.close()


def screenshot(page, path):
    c = CDP(page["webSocketDebuggerUrl"])
    try:
        res = c.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False}, timeout=60)
        with open(path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        return path
    finally:
        c.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9333
    print(json.dumps(targets(port), ensure_ascii=False, indent=2))
