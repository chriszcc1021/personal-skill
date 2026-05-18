#!/usr/bin/env python3
"""OpenClaw Console - 纯 stdlib HTTP 服务器"""
import os, json, subprocess, time, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import socketserver

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
AGENT_DIR = Path(os.environ.get("OPENCLAW_AGENT_DIR", "/home/openclaw/.openclaw/agents/main"))
SESSIONS_INDEX = AGENT_DIR / "sessions" / "sessions.json"
SESSIONS_DIR = AGENT_DIR / "sessions"
SGT = timezone(timedelta(hours=8))
PORT = int(os.environ.get("CONSOLE_PORT", "8088"))

_HINT_CACHE: dict = {}  # {sessionId: (mtime, hint)}


def _last_user_hint(session_id: str) -> str:
    """抽最近一条用户消息中的实际文字（去 metadata）作为可读 hint"""
    f = SESSIONS_DIR / f"{session_id}.jsonl"
    if not f.exists():
        return ""
    try:
        mt = f.stat().st_mtime
    except Exception:
        return ""
    cached = _HINT_CACHE.get(session_id)
    if cached and cached[0] == mt:
        return cached[1]
    last_user = ""
    try:
        with f.open() as fp:
            for line in fp:
                if '"role":"user"' not in line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                m = e.get("message", {})
                for c in m.get("content", []):
                    if not isinstance(c, dict):
                        continue
                    t = c.get("text", "")
                    if not t:
                        continue
                    cleaned = re.sub(r'```json.*?```', '', t, flags=re.DOTALL)
                    cleaned = re.sub(r'Conversation info[^\n]*\n+```json.*?```', '', cleaned, flags=re.DOTALL)
                    cleaned = re.sub(r'Conversation info.*?(?=\n\n|\Z)', '', cleaned, flags=re.DOTALL)
                    cleaned = re.sub(r'Sender.*?(?=\n\n|\Z)', '', cleaned, flags=re.DOTALL)
                    cleaned = re.sub(r'System: \[.*?\] SeaTalk[^:]*:', '', cleaned)
                    cleaned = re.sub(r'<[a-z\-]+>.*?</[a-z\-]+>', '', cleaned, flags=re.DOTALL)
                    cleaned = re.sub(r'\[media[^\]]*\]', '', cleaned)
                    cleaned = re.sub(r'\[Quoted from[^\]]*\]', '', cleaned)
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    if cleaned and len(cleaned) > 2:
                        last_user = cleaned[:50]
    except Exception:
        pass
    _HINT_CACHE[session_id] = (mt, last_user)
    return last_user


def _load_sessions_index() -> list:
    """返回 session 字典列表（合并 key 进去）"""
    if not SESSIONS_INDEX.exists():
        return []
    try:
        d = json.loads(SESSIONS_INDEX.read_text())
    except Exception:
        return []
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict):
                v = dict(v); v.setdefault("key", k)
                out.append(v)
    elif isinstance(d, list):
        out = [s for s in d if isinstance(s, dict)]
    return out


def _short_label(s: dict) -> str:
    key = s.get("key", "")
    if key.endswith(":main"):
        return "主 session"
    parts = key.split(":")
    if ":thread:" in key:
        # 取母 session 类型
        if "group" in parts:
            return "群线程"
        return "DM 线程"
    if "direct" in parts:
        return f"DM · {parts[-1][:8]}"
    if "group" in parts:
        return f"群 · {parts[-1][:10]}"
    if ":subagent:" in key:
        return f"子代理 · {parts[-1][:8]}"
    if ":cron:" in key:
        return f"定时 · {parts[-1][:8]}"
    if "dreaming" in key:
        return f"梦境 · {parts[-1][-12:]}"
    return key[-30:]


def _category(s: dict) -> str:
    """返回 session 分类"""
    key = s.get("key", "")
    if key.endswith(":main"): return "main"
    if ":thread:" in key: return "thread"
    if ":subagent:" in key: return "subagent"
    if ":cron:" in key: return "cron"
    if "dreaming" in key: return "dreaming"
    parts = key.split(":")
    if "direct" in parts: return "direct"
    if "group" in parts: return "group"
    return "other"


def api_list_sessions():
    out = []
    for s in _load_sessions_index():
        sid = s.get("sessionId")
        out.append({
            "key": s.get("key"),
            "sessionId": sid,
            "label": _short_label(s),
            "hint": _last_user_hint(sid) if sid else "",
            "category": _category(s),
            "kind": s.get("kind"),
            "updatedAt": s.get("updatedAt"),
            "ageMs": s.get("ageMs"),
            "inputTokens": s.get("inputTokens", 0),
            "outputTokens": s.get("outputTokens", 0),
            "totalTokens": s.get("totalTokens", 0),
            "contextTokens": s.get("contextTokens", 0),
            "model": s.get("model"),
            "modelProvider": s.get("modelProvider"),
            "abortedLastRun": s.get("abortedLastRun"),
        })
    out.sort(key=lambda x: x.get("updatedAt") or 0, reverse=True)
    return {"sessions": out}


def api_get_messages(session_id: str, limit: int = 100):
    f = SESSIONS_DIR / f"{session_id}.jsonl"
    if not f.exists():
        return None
    msgs = []
    with f.open() as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") != "message":
                continue
            m = e.get("message", {})
            role = m.get("role")
            content = m.get("content", [])
            text_parts = []
            tool_calls = []
            for c in content:
                if c.get("type") == "text":
                    text_parts.append(c.get("text", ""))
                elif c.get("type") == "toolCall":
                    tool_calls.append({"name": c.get("name"), "args": c.get("arguments")})
                elif c.get("type") == "toolResult":
                    tool_calls.append({"name": "result", "args": {"content": str(c.get("content", ""))[:200]}})
            msgs.append({
                "id": e.get("id"),
                "role": role,
                "text": "\n".join(text_parts),
                "toolCalls": tool_calls,
                "timestamp": e.get("timestamp"),
                "usage": m.get("usage") if role == "assistant" else None,
            })
    return {"messages": msgs[-limit:], "total": len(msgs)}


def api_usage_today():
    today_sgt = datetime.now(SGT).date()
    total_in = total_out = total_tok = 0
    per_session = []
    for s in _load_sessions_index():
        sid = s.get("sessionId")
        f = SESSIONS_DIR / f"{sid}.jsonl"
        if not f.exists():
            continue
        s_in = s_out = s_tok = 0
        try:
            with f.open() as fp:
                for line in fp:
                    if '"role":"assistant"' not in line:
                        continue
                    try:
                        e = json.loads(line)
                    except:
                        continue
                    ts = e.get("timestamp")
                    if not ts:
                        continue
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(SGT)
                    except:
                        continue
                    if dt.date() != today_sgt:
                        continue
                    u = (e.get("message") or {}).get("usage") or {}
                    s_in += u.get("input", 0)
                    s_out += u.get("output", 0)
                    s_tok += u.get("totalTokens", 0)
        except Exception:
            continue
        if s_tok > 0:
            per_session.append({"key": s.get("key"), "label": _short_label(s), "tokens": s_tok, "input": s_in, "output": s_out})
            total_in += s_in
            total_out += s_out
            total_tok += s_tok
    cost_in_usd = total_in * 15 / 1_000_000 * 0.282
    cost_out_usd = total_out * 75 / 1_000_000 * 0.282
    per_session.sort(key=lambda x: x["tokens"], reverse=True)
    return {
        "date": str(today_sgt),
        "totalInput": total_in,
        "totalOutput": total_out,
        "totalTokens": total_tok,
        "estimatedCostUSD": round(cost_in_usd + cost_out_usd, 4),
        "perSession": per_session[:20],
    }


def api_send(session_id: str, message: str):
    cmd = ["openclaw", "agent", "--session-id", session_id, "--message", message, "--json", "--timeout", "300"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=320)
        out = r.stdout
        err = r.stderr
        try:
            result = json.loads(out)
        except:
            result = {"raw": out[-4000:]}
        return {"ok": r.returncode == 0, "result": result, "stderr": err[-2000:] if err else ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".ico": "image/x-icon",
}


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        pass

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str):
        if path == "/" or path == "":
            path = "/index.html"
        # 防穿越
        safe = path.lstrip("/").replace("..", "")
        f = FRONTEND / safe
        if not f.exists() or not f.is_file():
            # SPA fallback
            f = FRONTEND / "index.html"
        ext = f.suffix.lower()
        ct = CONTENT_TYPES.get(ext, "application/octet-stream")
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("content-type", ct)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        qs = parse_qs(u.query or "")
        # 兼容 /console/ 前缀
        for prefix in ("/console", "/openclaw-console"):
            if p.startswith(prefix):
                p = p[len(prefix):] or "/"
                break
        if p == "/api/sessions":
            return self._json(200, api_list_sessions())
        if p == "/api/usage/today":
            return self._json(200, api_usage_today())
        if p == "/api/messages":
            sid = (qs.get("sessionId") or [""])[0]
            limit = int((qs.get("limit") or ["100"])[0])
            r = api_get_messages(sid, limit)
            if r is None:
                return self._json(404, {"error": "not found"})
            return self._json(200, r)
        if p == "/api/health":
            return self._json(200, {"ok": True, "ts": int(time.time())})
        return self._serve_static(p)

    def do_POST(self):
        u = urlparse(self.path)
        p = u.path
        for prefix in ("/console", "/openclaw-console"):
            if p.startswith(prefix):
                p = p[len(prefix):] or "/"
                break
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n).decode("utf-8") if n else "{}"
        try:
            data = json.loads(body)
        except:
            data = {}
        if p == "/api/send":
            sid = data.get("sessionId", "")
            msg = (data.get("message") or "").strip()
            if not sid or not msg:
                return self._json(400, {"error": "sessionId and message required"})
            return self._json(200, api_send(sid, msg))
        return self._json(404, {"error": "not found"})


class ThreadingServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    print(f"console: http://127.0.0.1:{PORT} (frontend={FRONTEND}, agent={AGENT_DIR})")
    ThreadingServer(("127.0.0.1", PORT), H).serve_forever()
