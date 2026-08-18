#!/usr/bin/env python3
import http.server
import http.cookies
import socket
import select
import os
import sys
import urllib.request

PORT = 8080
BACKEND = "127.0.0.1:3000"
PASSWORD = os.environ.get("BASIC_AUTH_PASSWORD", "")
TIMEOUT = 30

LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ghBrowser - Sign In</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);font-family:'Segoe UI',system-ui,sans-serif;color:#fff}
.card{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);
border-radius:20px;padding:48px 40px;width:400px;box-shadow:0 25px 60px rgba(0,0,0,.5)}
.logo{text-align:center;margin-bottom:36px}
.logo svg{width:64px;height:64px;margin-bottom:16px}
.logo h1{font-size:28px;font-weight:700}
.logo p{color:rgba(255,255,255,.5);font-size:14px;margin-top:6px}
.form-group{margin-bottom:20px}
label{display:block;font-size:13px;color:rgba(255,255,255,.6);margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}
input{width:100%;padding:14px 16px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.15);
border-radius:10px;color:#fff;font-size:16px;outline:none;transition:border-color .2s}
input:focus{border-color:#7c5cfc}
input::placeholder{color:rgba(255,255,255,.3)}
button{width:100%;padding:14px;background:linear-gradient(135deg,#7c5cfc,#a855f7);border:none;border-radius:10px;
color:#fff;font-size:16px;font-weight:600;cursor:pointer;margin-top:8px;transition:opacity .2s}
button:hover{opacity:.9}
.error{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);color:#f87171;padding:10px 14px;
border-radius:8px;font-size:14px;margin-bottom:16px;display:%s}
.badge{text-align:center;margin-top:24px;font-size:12px;color:rgba(255,255,255,.3)}
</style>
</head>
<body>
<div class="card">
<div class="logo">
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
<path d="M2 12h20"/>
<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
</svg>
<h1>ghBrowser</h1>
<p>Private Cloud Browser</p>
</div>
<div class="error" id="error">Invalid password. Try again.</div>
<form method="POST" action="/auth">
<div class="form-group">
<label>Password</label>
<input type="password" name="password" placeholder="Enter password" autofocus required>
</div>
<button type="submit">Sign In</button>
</form>
<div class="badge">End-to-end encrypted session</div>
</div>
</body>
</html>"""


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _get_cookie(self):
        cookie = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return cookie.get("session") and cookie["session"].value == "ok"

    def _send_login(self, error=False):
        page = LOGIN_PAGE % ("block" if error else "none")
        self.send_response(401)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", len(page))
        self.end_headers()
        self.wfile.write(page.encode())

    def _do_auth(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        if f"password={PASSWORD}" in body:
            self.send_response(302)
            self.send_header("Set-Cookie", "session=ok; Path=/; HttpOnly; SameSite=Strict; Max-Age=3600")
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_response(302)
            self.send_header("Location", "/?error=1")
            self.end_headers()

    def _proxy_http(self):
        url = f"http://{BACKEND}{self.path}"
        body = None
        if "Content-Length" in self.headers:
            body = self.rfile.read(int(self.headers["Content-Length"]))

        headers = {}
        for key in self.headers:
            if key.lower() not in ("host", "cookie", "connection"):
                headers[key] = self.headers[key]
        headers["Host"] = BACKEND

        req = urllib.request.Request(url, data=body, headers=headers, method=self.command)
        try:
            resp = urllib.request.urlopen(req, timeout=TIMEOUT)
            self.send_response(resp.status)
            for key, val in resp.headers.items():
                if key.lower() not in ("transfer-encoding", "connection"):
                    self.send_header(key, val)
            self.end_headers()
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode())

    def _proxy_websocket(self):
        host, port = BACKEND.split(":")
        backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend.settimeout(TIMEOUT)
        try:
            backend.connect((host, int(port)))
        except Exception:
            self.send_response(502)
            self.end_headers()
            return

        req = f"{self.command} {self.path} HTTP/1.1\r\n"
        for key in self.headers:
            val = self.headers[key]
            if key.lower() == "host":
                val = BACKEND
            req += f"{key}: {val}\r\n"
        req += "\r\n"
        backend.sendall(req.encode())

        client = self.connection
        client.setblocking(False)
        backend.setblocking(False)

        try:
            while True:
                readable, _, _ = select.select([client, backend], [], [], TIMEOUT)
                if not readable:
                    break
                for sock in readable:
                    try:
                        data = sock.recv(65536)
                        if not data:
                            return
                        if sock is client:
                            backend.sendall(data)
                        else:
                            client.sendall(data)
                    except (BlockingIOError, ConnectionError):
                        return
        finally:
            backend.close()

    def _proxy(self):
        if self._get_cookie():
            upgrade = self.headers.get("Upgrade", "").lower()
            if upgrade == "websocket":
                self._proxy_websocket()
            else:
                self._proxy_http()
        else:
            error = "?" in self.path and "error=1" in self.path
            self._send_login(error)

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        if self.path == "/auth":
            self._do_auth()
        else:
            self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def do_PATCH(self):
        self._proxy()

    def do_OPTIONS(self):
        self._proxy()


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    print(f"Auth proxy on :{PORT}, backend: {BACKEND}")
    server.serve_forever()
