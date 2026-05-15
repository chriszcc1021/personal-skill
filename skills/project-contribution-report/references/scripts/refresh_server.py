#!/usr/bin/env python3
"""
fastpublish-refresh: minimal stdlib HTTP server with SSE progress.
Listens on 127.0.0.1:8081, exposes:
  POST /refresh      -> start a refresh job, returns {job_id}
  GET  /refresh/<id> -> SSE stream of progress events
  GET  /healthz      -> ok
"""
import http.server, socketserver, json, threading, subprocess, time, uuid, os, queue, sys
from pathlib import Path

REPO_DIR    = Path("/var/www/fastpublish-src/fastpublish")
SCRIPT_DIR  = Path("/var/www/fastpublish-src/scripts")
PUBLISH_DIR = Path("/var/www/fastpublish")
TOKEN_FILE  = Path("/var/www/fastpublish-src/.token")
COOLDOWN_S  = 20  # min seconds between refreshes

JOBS = {}        # job_id -> {"q": Queue, "done": bool, "ok": bool}
LAST_RUN = [0.0]
LOCK = threading.Lock()

def steps():
    return [
        ("git",     "git pull (latest commits)",      ["git", "-C", str(REPO_DIR), "pull", "--ff-only"]),
        ("analyze", "scan repo + score contributors", ["python3", str(SCRIPT_DIR / "analyze.py")]),
        ("build",   "render report HTML",             ["python3", str(SCRIPT_DIR / "build_html.py")]),
        ("publish", "copy to /var/www/fastpublish",   ["cp", str(SCRIPT_DIR / "report_v8.html"),
                                                              str(PUBLISH_DIR / "index.html")]),
    ]

def run_job(job_id):
    q = JOBS[job_id]["q"]
    total = len(steps())
    try:
        for i, (key, label, cmd) in enumerate(steps()):
            q.put({"type": "step", "i": i, "total": total, "key": key, "label": label, "status": "running"})
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                q.put({"type": "step", "i": i, "total": total, "key": key, "status": "fail",
                       "err": (r.stderr or r.stdout)[-400:]})
                q.put({"type": "done", "ok": False})
                JOBS[job_id]["done"] = True; JOBS[job_id]["ok"] = False
                return
            q.put({"type": "step", "i": i, "total": total, "key": key, "status": "ok"})
        q.put({"type": "done", "ok": True, "ts": time.strftime("%Y-%m-%d %H:%M GMT+8")})
        JOBS[job_id]["done"] = True; JOBS[job_id]["ok"] = True
    except Exception as e:
        q.put({"type": "done", "ok": False, "err": str(e)[:200]})
        JOBS[job_id]["done"] = True; JOBS[job_id]["ok"] = False

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **k):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), a[0] % a[1:]))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200); self._cors()
            self.send_header("Content-Type","text/plain"); self.end_headers()
            self.wfile.write(b"ok"); return
        if self.path.startswith("/refresh/"):
            job_id = self.path.split("/")[-1]
            if job_id not in JOBS:
                self.send_response(404); self._cors(); self.end_headers(); return
            self.send_response(200); self._cors()
            self.send_header("Content-Type","text/event-stream")
            self.send_header("Cache-Control","no-cache")
            self.send_header("X-Accel-Buffering","no")
            self.end_headers()
            q = JOBS[job_id]["q"]
            try:
                while True:
                    try:
                        ev = q.get(timeout=60)
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n"); self.wfile.flush(); continue
                    self.wfile.write(("data: " + json.dumps(ev) + "\n\n").encode()); self.wfile.flush()
                    if ev.get("type") == "done": break
            except (BrokenPipeError, ConnectionResetError): pass
            return
        self.send_response(404); self._cors(); self.end_headers()

    def do_POST(self):
        if self.path != "/refresh":
            self.send_response(404); self._cors(); self.end_headers(); return
        with LOCK:
            elapsed = time.time() - LAST_RUN[0]
            if elapsed < COOLDOWN_S:
                self.send_response(429); self._cors()
                self.send_header("Content-Type","application/json"); self.end_headers()
                self.wfile.write(json.dumps({"error": f"cooldown, wait {int(COOLDOWN_S-elapsed)}s"}).encode())
                return
            LAST_RUN[0] = time.time()
            job_id = uuid.uuid4().hex[:12]
            JOBS[job_id] = {"q": queue.Queue(), "done": False, "ok": None}
            threading.Thread(target=run_job, args=(job_id,), daemon=True).start()
            # cleanup old jobs (keep last 8)
            old = [k for k, v in JOBS.items() if v["done"]]
            for k in old[:-8]: JOBS.pop(k, None)
        self.send_response(200); self._cors()
        self.send_header("Content-Type","application/json"); self.end_headers()
        self.wfile.write(json.dumps({"job_id": job_id}).encode())

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True; allow_reuse_address = True

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8081"))
    with ThreadedTCPServer(("127.0.0.1", port), H) as srv:
        print(f"refresh-server listening on 127.0.0.1:{port}", flush=True)
        srv.serve_forever()
