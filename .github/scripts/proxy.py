import os
import secrets
import socket
import select
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PASSWORD = os.environ.get("PROXY_PASSWORD", "")
AUTH_REQUIRED = bool(PASSWORD)
UPSTREAM_HOST = os.environ.get("UPSTREAM_HOST", "127.0.0.1")
UPSTREAM_PORT = int(os.environ.get("UPSTREAM_PORT", "3000"))

sessions = {}

FAVICON_SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
                b'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
                b'<stop offset="0" stop-color="#6d5cff"/><stop offset="1" stop-color="#22d3ee"/>'
                b'</linearGradient></defs>'
                b'<rect width="24" height="24" rx="6" fill="url(#g)"/>'
                b'<path d="M12 19s5-2.3 5-6.3V8.2L12 6 7 8.2v4.5C7 16.7 12 19 12 19z" '
                b'fill="none" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/>'
                b'<path d="m10.2 12.2 1.4 1.4 2.4-2.4" fill="none" stroke="#fff" '
                b'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>')

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ghBrowser - Sign In</title>
<link rel="icon" href="/favicon.ico">
<style>
:root{--bg:#060a14;--card:rgba(255,255,255,.06);--stroke:rgba(255,255,255,.12);
--txt:#f2f5ff;--mut:rgba(242,245,255,.55);--acc1:#6d5cff;--acc2:#22d3ee}
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;
background:var(--bg);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--txt);overflow:hidden}
.bg{position:fixed;inset:0;z-index:-1;overflow:hidden}
.blob{position:absolute;width:60vmax;height:60vmax;border-radius:50%;filter:blur(90px);opacity:.35}
.b1{background:#4c1d95;top:-20vmax;left:-15vmax;animation:drift 18s ease-in-out infinite alternate}
.b2{background:#0e7490;bottom:-25vmax;right:-15vmax;animation:drift 22s ease-in-out infinite alternate-reverse}
.b3{background:#166534;top:40%;left:60%;width:35vmax;height:35vmax;opacity:.22;animation:drift 26s ease-in-out infinite alternate}
@keyframes drift{from{transform:translate(0,0) scale(1)}to{transform:translate(6vmax,4vmax) scale(1.15)}}
.card{width:400px;max-width:100%;background:var(--card);border:1px solid var(--stroke);border-radius:24px;
padding:44px 38px 34px;backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
box-shadow:0 30px 80px rgba(0,0,0,.55),inset 0 1px 0 rgba(255,255,255,.08);animation:rise .5s ease}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.ring{width:76px;height:76px;margin:0 auto 18px;border-radius:22px;display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,var(--acc1),var(--acc2));box-shadow:0 12px 30px rgba(109,92,255,.45)}
.ring svg{width:38px;height:38px;stroke:#fff}
h1{text-align:center;font-size:27px;font-weight:800;letter-spacing:.3px}
.sub{text-align:center;color:var(--mut);font-size:13.5px;margin-top:7px}
.pills{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:20px 0 26px}
.pill{font-size:11.5px;font-weight:600;padding:6px 12px;border-radius:999px;letter-spacing:.2px;
border:1px solid rgba(34,211,238,.35);background:rgba(34,211,238,.1);color:#a5f3fc}
.pill.green{border-color:rgba(74,222,128,.35);background:rgba(74,222,128,.1);color:#bbf7d0}
label{display:block;font-size:12px;font-weight:700;color:var(--mut);margin-bottom:9px;text-transform:uppercase;letter-spacing:1.4px}
.field{position:relative}
input{width:100%;padding:15px 48px 15px 16px;background:rgba(0,0,0,.3);border:1px solid var(--stroke);
border-radius:12px;color:var(--txt);font-size:16px;outline:none;transition:border-color .2s,box-shadow .2s}
input:focus{border-color:var(--acc1);box-shadow:0 0 0 3px rgba(109,92,255,.25)}
input::placeholder{color:rgba(242,245,255,.28)}
.eye{position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;
padding:8px;border-radius:8px;color:var(--mut);font-size:16px;line-height:1}
.eye:hover{color:#fff;background:rgba(255,255,255,.08)}
.caps{display:none;font-size:12.5px;color:#fbbf24;margin-top:8px}
.error{display:none;background:rgba(251,113,133,.12);border:1px solid rgba(251,113,133,.4);color:#fda4af;
padding:11px 14px;border-radius:10px;font-size:13.5px;margin:0 0 18px}
.error.show{display:block;animation:shake .4s ease}
@keyframes shake{0%,100%{transform:none}20%,60%{transform:translateX(-7px)}40%,80%{transform:translateX(7px)}}
button.go{width:100%;padding:15px;margin-top:20px;background:linear-gradient(135deg,var(--acc1),#a855f7 55%,var(--acc2));
border:none;border-radius:12px;color:#fff;font-size:16px;font-weight:700;cursor:pointer;
display:flex;align-items:center;justify-content:center;gap:10px;transition:transform .15s,opacity .2s}
button.go:hover{opacity:.92}button.go:active{transform:scale(.98)}button.go:disabled{opacity:.7;cursor:wait}
.spin{display:none;width:18px;height:18px;border-radius:50%;border:2.5px solid rgba(255,255,255,.35);
border-top-color:#fff;animation:rot .7s linear infinite}
button.go.loading .spin{display:block}
@keyframes rot{to{transform:rotate(360deg)}}
.foot{text-align:center;margin-top:22px;font-size:12px;color:rgba(242,245,255,.32)}
@media(max-width:440px){.card{padding:36px 26px 28px}}
</style>
</head>
<body>
<div class="bg"><div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div></div>
<div class="card">
<div class="ring"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-3.6 8-10V5l-8-3-8 3v7c0 6.4 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg></div>
<h1>ghBrowser</h1>
<p class="sub">Family Safe &bull; Private Cloud Browser</p>
<div class="pills"><span class="pill">AdGuard Family DNS</span><span class="pill green">NSFW blocked</span><span class="pill">SafeSearch on</span></div>
<div class="error" id="error">Invalid password. Try again.</div>
<form id="form">
<div class="form-group">
<label for="password">Password</label>
<div class="field">
<input type="password" id="password" placeholder="Enter password" autocomplete="current-password" autofocus required>
<button type="button" class="eye" id="eye" title="Show password">&#128065;</button>
</div>
<div class="caps" id="caps">Caps Lock is on</div>
</div>
<button type="submit" class="go" id="go"><span class="spin"></span><span id="goTxt">Unlock Browser</span></button>
</form>
<div class="foot">Filtered &amp; encrypted session</div>
</div>
<script>
(function(){
var f=document.getElementById('form'),pw=document.getElementById('password'),
err=document.getElementById('error'),go=document.getElementById('go'),
txt=document.getElementById('goTxt'),eye=document.getElementById('eye'),
caps=document.getElementById('caps');
eye.addEventListener('click',function(){
var show=pw.type==='password';pw.type=show?'text':'password';
eye.innerHTML=show?'&#128064;':'&#128065;';pw.focus();});
pw.addEventListener('keyup',function(e){
try{caps.style.display=e.getModifierState&&e.getModifierState('CapsLock')?'block':'none';}catch(_){}});
function fail(){err.classList.remove('show');void err.offsetWidth;err.classList.add('show');
go.classList.remove('loading');txt.textContent='Unlock Browser';go.disabled=false;}
f.addEventListener('submit',async function(e){
e.preventDefault();err.classList.remove('show');
go.classList.add('loading');txt.textContent='Unlocking\u2026';go.disabled=true;
try{
var r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw.value})});
var d=await r.json();
if(d.ok){txt.textContent='Welcome';window.location.href='/';}
else fail();
}catch(_){fail();}});
})();
</script>
</body>
</html>"""

def is_valid_session(cookie_header):
    if not cookie_header:
        return False
    for c in cookie_header.split(";"):
        c = c.strip()
        if c.startswith("session="):
            return c.split("=", 1)[1] in sessions
    return False

def build_raw_request(method, path, headers, body=b""):
    raw = f"{method} {path} HTTP/1.1\r\n"
    for k, v in headers.items():
        raw += f"{k}: {v}\r\n"
    raw += "\r\n"
    return raw.encode() + body

def raw_tunnel(client_sock, method, path, headers, body=b""):
    upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upstream.connect((UPSTREAM_HOST, UPSTREAM_PORT))
    req = build_raw_request(method, path, headers, body)
    upstream.sendall(req)

    socks = [client_sock, upstream]
    try:
        while True:
            r, _, x = select.select(socks, [], socks, 60)
            if x:
                break
            if not r:
                break
            for s in r:
                data = s.recv(65536)
                if not data:
                    return
                if s is client_sock:
                    upstream.sendall(data)
                else:
                    client_sock.sendall(data)
    except Exception:
        pass
    finally:
        upstream.close()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[proxy] {args[0]}")

    def _cookie(self):
        return self.headers.get("Cookie", "")

    def _forward(self, method):
        is_ws = "upgrade" in self.headers.get("Connection", "").lower()
        body = b""
        cl = int(self.headers.get("Content-Length", 0))
        if cl:
            body = self.rfile.read(cl)

        fwd_headers = {}
        for k in self.headers:
            if k.lower() not in ("host", "cookie", "transfer-encoding"):
                fwd_headers[k] = self.headers[k]
        fwd_headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"

        if is_ws:
            raw_tunnel(self.connection, method, self.path, fwd_headers, body)
            self.close_connection = True
            return

        import http.client
        conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=10)
        conn.request(method, self.path, body=body, headers=fwd_headers)
        resp = conn.getresponse()

        self.send_response(resp.status)
        skip = {"transfer-encoding", "connection"}
        for k, v in resp.getheaders():
            if k.lower() not in skip:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp.read())
        conn.close()

    def do_GET(self):
        p = urlparse(self.path).path

        if p == "/auth/login":
            data = LOGIN_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
            return

        if p == "/favicon.ico":
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(FAVICON_SVG)))
            self.end_headers()
            self.wfile.write(FAVICON_SVG)
            return

        if AUTH_REQUIRED and not is_valid_session(self._cookie()):
            self.send_response(302)
            self.send_header("Location", "/auth/login")
            self.end_headers()
            return

        self._forward("GET")

    def do_POST(self):
        p = urlparse(self.path).path

        if p == "/auth/login":
            if not AUTH_REQUIRED:
                # passwordless mode: instantly "logged in"
                resp = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(resp))
                self.end_headers()
                self.wfile.write(resp)
                return
            cl = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(cl).decode()
            data = json.loads(body)
            if data.get("password") == PASSWORD:
                token = secrets.token_hex(32)
                sessions[token] = True
                resp = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(resp))
                self.send_header("Set-Cookie",
                    f"session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400")
                self.end_headers()
                self.wfile.write(resp)
            else:
                resp = b'{"ok":false}'
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(resp))
                self.end_headers()
                self.wfile.write(resp)
            return

        if not is_valid_session(self._cookie()):
            if not AUTH_REQUIRED:
                self._forward("POST")
                return
            resp = b'{"ok":false}'
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(resp))
            self.end_headers()
            self.wfile.write(resp)
            return

        self._forward("POST")

    def do_PUT(self):    self._forward("PUT")
    def do_DELETE(self): self._forward("DELETE")
    def do_PATCH(self):  self._forward("PATCH")
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

class ThreadedHTTPServer(HTTPServer):
    def process_request(self, request, client_address):
        t = threading.Thread(target=self.process_request_thread, args=(request, client_address))
        t.daemon = True
        t.start()

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

if __name__ == "__main__":
    print(f"[proxy] Starting on :8080 -> {UPSTREAM_HOST}:{UPSTREAM_PORT} (auth: {'password' if AUTH_REQUIRED else 'NONE - open access'})")
    server = ThreadedHTTPServer(("0.0.0.0", 8080), Handler)
    server.daemon_threads = True
    server.serve_forever()
