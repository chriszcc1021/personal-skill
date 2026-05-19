#!/usr/bin/env python3
"""OpenClaw Console - 纯 stdlib HTTP 服务器"""
import os, json, subprocess, time, re, uuid, base64
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
MEDIA_DIR = Path(os.environ.get("OPENCLAW_MEDIA_DIR", "/home/openclaw/.openclaw/media/inbound"))
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
META_DIR = Path(__file__).resolve().parent / "meta"
META_DIR.mkdir(parents=True, exist_ok=True)
SESSION_META_FILE = META_DIR / "session-meta.json"  # {sessionId: {pinned, archived, alias}}
PROJECTS_FILE = META_DIR / "projects.json"  # {projectId: {name, sessionIds: []}}
_PROJ_LOCK = threading.Lock()


def _load_projects() -> dict:
    if not PROJECTS_FILE.exists():
        return {}
    try:
        return json.loads(PROJECTS_FILE.read_text("utf-8") or "{}")
    except Exception:
        return {}


def _save_projects(d: dict):
    PROJECTS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), "utf-8")
_META_LOCK = threading.Lock()


def _load_meta() -> dict:
    if not SESSION_META_FILE.exists():
        return {}
    try:
        return json.loads(SESSION_META_FILE.read_text("utf-8") or "{}")
    except Exception:
        return {}


def _save_meta(d: dict):
    SESSION_META_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), "utf-8")

_HINT_CACHE: dict = {}  # {sessionId: (mtime, {hint, lastSender, recentSenders})}


def _extract_session_info(session_id: str) -> dict:
    """从 jsonl 抽取：hint、最近发言者、最近 3 个发言者。"""
    f = SESSIONS_DIR / f"{session_id}.jsonl"
    if not f.exists():
        return {"hint": "", "lastSender": "", "recentSenders": []}
    try:
        mt = f.stat().st_mtime
    except Exception:
        return {"hint": "", "lastSender": "", "recentSenders": []}
    cached = _HINT_CACHE.get(session_id)
    if cached and cached[0] == mt:
        return cached[1]
    last_hint = ""
    senders_recent = []
    channel_seen = ""
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
                    # 抽 channel源【System: [time] SeaTalk[default] DM from ...】
                    if not channel_seen:
                        cmt = re.search(r'System:\s*\[[^\]]+\]\s*([A-Za-z][A-Za-z0-9 _-]+?)(?:\[[^\]]*\])?\s+(?:DM|Group)\b', t)
                        if cmt:
                            ch = cmt.group(1).strip().lower()
                            if ch in ('seatalk','telegram','whatsapp','signal','discord','slack','imessage','feishu','messenger','line','wechat','matrix','irc','msteams','mattermost'):
                                channel_seen = ch
                        if not channel_seen:
                            # 退一步：看 JSON 里的 channel字段
                            cmt2 = re.search(r'"channel"\s*:\s*"([^"]+)"', t)
                            if cmt2: channel_seen = cmt2.group(1)
                    # 抽 sender
                    smt = re.search(r'Sender[^\n]*\n+```json\s*({.*?})\s*```', t, re.S)
                    if not smt:
                        smt = re.search(r'```json\s*({"label":[^`]*"name":\s*"[^"]+"[^`]*})\s*```', t, re.S)
                    if smt:
                        try:
                            jd = json.loads(smt.group(1))
                            nm = jd.get("name") or jd.get("label")
                            if nm:
                                # 化简：删除 (xxx@xxx)、(82124) 之类
                                nm = re.sub(r'\s*\([^)]*\)\s*$', '', nm).strip()
                                nm = re.sub(r'\s*\([^)]*\)\s*', ' ', nm).strip()
                                if nm:
                                    senders_recent.append(nm)
                        except Exception:
                            pass
                    # 抽 cleaned hint
                    cleaned = t
                    cleaned = re.sub(r'```json[\s\S]*?```', '', cleaned)
                    cleaned = re.sub(r'Conversation info[^\n]*', '', cleaned)
                    cleaned = re.sub(r'Sender[^\n]*', '', cleaned)
                    cleaned = re.sub(r'System: \[[^\]]+\] [A-Za-z]+(?:\[[^\]]+\])?(?: Group\([^)]*\))? from [^:]+:\s*', '', cleaned)
                    cleaned = re.sub(r'<[a-z\-]+>[\s\S]*?</[a-z\-]+>', '', cleaned)
                    cleaned = re.sub(r'\[media[^\]]*\]', '', cleaned)
                    cleaned = re.sub(r'\[Quoted from[^\]]*\]', '', cleaned)
                    cleaned = re.sub(r'^\s*\[[A-Z][a-z]+\s+\d{4}-\d{2}-\d{2}[^\]]*\]\s*', '', cleaned)
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    if cleaned and len(cleaned) > 2:
                        last_hint = cleaned[:60]
    except Exception:
        pass
    # dedupe recent senders, 保最后 3 个不同
    seen = set()
    uniq_back = []
    for nm in reversed(senders_recent):
        if nm in seen:
            continue
        seen.add(nm)
        uniq_back.append(nm)
        if len(uniq_back) >= 3:
            break
    last_sender = uniq_back[0] if uniq_back else ""
    info = {"hint": last_hint, "lastSender": last_sender, "recentSenders": uniq_back, "channel": channel_seen}
    _HINT_CACHE[session_id] = (mt, info)
    return info


def _last_user_hint(session_id: str) -> str:
    return _extract_session_info(session_id).get("hint", "")


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
    meta = _load_meta()
    out = []
    for s in _load_sessions_index():
        sid = s.get("sessionId")
        m = meta.get(sid, {}) if sid else {}
        info = _extract_session_info(sid) if sid else {"hint":"","lastSender":"","recentSenders":[],"channel":""}
        # 从 sessionKey 第 3 段抽 channel（优先于 jsonl 抽取）
        key_parts = (s.get("key") or "").split(":")
        key_chan = key_parts[2] if len(key_parts) >= 3 else ""
        # 带外部渠道名才当作 channel；cron / main / subagent / dreaming 不算外部渠道
        external = {"seatalk","telegram","whatsapp","signal","discord","slack","imessage","feishu","messenger","line","wechat","matrix","irc","msteams","mattermost","qqbot","twitch","nostr"}
        if key_chan in external:
            chan = key_chan
        else:
            chan = info.get("channel", "") or key_chan
        out.append({
            "key": s.get("key"),
            "sessionId": sid,
            "label": m.get("alias") or _short_label(s),
            "alias": m.get("alias"),
            "pinned": bool(m.get("pinned")),
            "archived": bool(m.get("archived")),
            "hint": info.get("hint", ""),
            "lastSender": info.get("lastSender", ""),
            "recentSenders": info.get("recentSenders", []),
            "channel": chan,
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
    # pinned 优先，然后 updatedAt desc；archived 除非调用时要
    out.sort(key=lambda x: (0 if x["pinned"] else 1, -(x.get("updatedAt") or 0)))
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


def _entry_to_sse(e: dict):
    """将 jsonl entry 压缩为 SSE 轻量 payload。返回 None 表示跳过。"""
    m = e.get("message", {}) or {}
    role = m.get("role")
    ts = e.get("timestamp") or m.get("timestamp") or ""
    if role == "assistant":
        parts = []
        for c in m.get("content", []) or []:
            if not isinstance(c, dict):
                continue
            t = c.get("type")
            if t == "text":
                parts.append({"type": "text", "text": c.get("text", "")})
            elif t == "thinking":
                parts.append({"type": "thinking", "text": c.get("text", "") or c.get("thinking", "")})
            elif t == "toolCall":
                args = c.get("arguments", {}) or {}
                parts.append({
                    "type": "toolCall",
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "arguments": args,
                })
        usage = m.get("usage", {}) or {}
        return {"role": "assistant", "ts": ts, "parts": parts, "usage": {"input": usage.get("input", 0), "output": usage.get("output", 0), "total": usage.get("totalTokens", 0)}}
    if role == "user":
        c = m.get("content", "")
        if isinstance(c, list):
            txt = ""
            for x in c:
                if isinstance(x, dict) and x.get("type") == "text":
                    txt += x.get("text", "")
            c = txt
        return {"role": "user", "ts": ts, "text": str(c)[:4000]}
    if role == "toolResult":
        details = m.get("details", {}) or {}
        agg = details.get("aggregated", "") or ""
        content_txt = ""
        for x in m.get("content", []) or []:
            if isinstance(x, dict) and x.get("type") == "text":
                content_txt += x.get("text", "")
        return {
            "role": "toolResult",
            "ts": ts,
            "toolCallId": m.get("toolCallId"),
            "toolName": m.get("toolName"),
            "status": details.get("status"),
            "exitCode": details.get("exitCode"),
            "durationMs": details.get("durationMs"),
            "isError": m.get("isError", False),
            "text": (agg or content_txt)[:4000],
        }
    return None


_SEND_LOCK = threading.Lock()
_RUNNING: dict = {}  # sessionId -> {pid, started}


def api_send(session_id: str, message: str, media_paths: list = None):
    """同步跳进后台，立即返回；agent 走 jsonl 追加 → SSE 推。"""
    full_msg = message
    if media_paths:
        prefix = "[media attached: " + " | ".join(media_paths) + "]\n"
        full_msg = prefix + full_msg
    # 项目上下文注入（对齐 Codex）：
    # - 首次 send：注入 prompt + cwd 说明作为 system-like 上下文
    # - 后续 send：只带一行轻量 cwd 提醒，避免占 token
    proj = _project_for_session(session_id)
    work_cwd = None
    if proj:
        if proj.get("cwd"):
            cw = Path(proj["cwd"]).expanduser()
            if cw.exists() and cw.is_dir():
                work_cwd = str(cw)
        if not _session_has_history(session_id):
            pieces = [f"[项目上下文 · {proj.get('name','')}]"]
            if proj.get("prompt"):
                pieces.append(proj['prompt'].strip())
            if work_cwd:
                pieces.append(
                    f"[项目工作目录] {work_cwd}\n"
                    "后续所有 exec/read/write/edit 默认在此目录下。"
                    "openclaw 运行 cwd 是 workspace，你需要在 exec 里显式 cd 或使用绝对路径。"
                )
            full_msg = "\n\n".join(pieces) + "\n\n---\n\n" + full_msg
        elif work_cwd:
            full_msg = f"[cwd: {work_cwd}]\n" + full_msg
    with _SEND_LOCK:
        existing = _RUNNING.get(session_id)
        if existing:
            return {"ok": False, "error": "already running", "runningSince": existing["started"]}
        cmd = ["openclaw", "agent", "--session-id", session_id, "--message", full_msg, "--json", "--timeout", "300"]
        log_path = Path("/tmp") / f"console-send-{session_id[:8]}.log"
        logf = log_path.open("ab")
        try:
            proc = subprocess.Popen(
                cmd, stdout=logf, stderr=logf, stdin=subprocess.DEVNULL,
                start_new_session=True, cwd=work_cwd,
            )
        except FileNotFoundError as e:
            logf.close()
            return {"ok": False, "error": f"openclaw CLI not found in PATH: {e}"}
        _RUNNING[session_id] = {"pid": proc.pid, "started": int(time.time()), "cwd": work_cwd}

        def _wait():
            try:
                proc.wait(timeout=360)
            except Exception:
                proc.kill()
            finally:
                logf.close()
                with _SEND_LOCK:
                    _RUNNING.pop(session_id, None)

        threading.Thread(target=_wait, daemon=True).start()
        return {"ok": True, "pid": proc.pid, "started": _RUNNING[session_id]["started"]}


def api_running(session_id: str):
    with _SEND_LOCK:
        info = _RUNNING.get(session_id)
    return {"running": bool(info), "info": info}


def api_running_all():
    with _SEND_LOCK:
        out = {sid: {"pid": info["pid"], "started": info["started"]} for sid, info in _RUNNING.items()}
    return {"running": out}


# ============= Projects =============

def api_projects():
    projs = _load_projects()
    meta = _load_meta()
    idx_sessions = {s.get("sessionId"): s for s in _load_sessions_index()}
    out = []
    for pid, p in projs.items():
        threads = []
        for sid in p.get("sessionIds", []):
            s = idx_sessions.get(sid) or {}
            m = meta.get(sid, {})
            threads.append({
                "sessionId": sid,
                "alias": m.get("alias"),
                "updatedAt": s.get("updatedAt"),
                "totalTokens": s.get("totalTokens", 0),
                "hint": _extract_session_info(sid).get("hint", "") if sid else "",
            })
        threads.sort(key=lambda t: -(t.get("updatedAt") or 0))
        out.append({
            "projectId": pid,
            "name": p.get("name") or pid,
            "prompt": p.get("prompt", ""),
            "cwd": p.get("cwd", ""),
            "threads": threads,
        })
    out.sort(key=lambda x: x["name"])
    return {"projects": out}


def api_project_upsert(project_id: str, name: str, prompt: str = None, cwd: str = None):
    with _PROJ_LOCK:
        projs = _load_projects()
        if project_id not in projs:
            projs[project_id] = {"name": name or project_id, "sessionIds": [], "prompt": prompt or "", "cwd": cwd or ""}
        else:
            projs[project_id]["name"] = name or projs[project_id].get("name", project_id)
            if prompt is not None: projs[project_id]["prompt"] = prompt
            if cwd is not None: projs[project_id]["cwd"] = cwd
        _save_projects(projs)
        return {"ok": True, "project": projs[project_id]}


def _project_for_session(session_id: str) -> dict:
    """返回 session 所在的 project dict（含 prompt / cwd），没有 返 None。"""
    projs = _load_projects()
    for pid, p in projs.items():
        if session_id in p.get("sessionIds", []):
            return {**p, "projectId": pid}
    return None


def _session_has_history(session_id: str) -> bool:
    f = SESSIONS_DIR / f"{session_id}.jsonl"
    return f.exists() and f.stat().st_size > 50


def api_project_delete(project_id: str):
    with _PROJ_LOCK:
        projs = _load_projects()
        existed = project_id in projs
        projs.pop(project_id, None)
        _save_projects(projs)
        return {"ok": True, "existed": existed}


def api_thread_assign(project_id: str, session_id: str):
    """将 sessionId 划入 project（先从其它 project 移除）。project_id=None/'' 表示从所有 project 移除。"""
    with _PROJ_LOCK:
        projs = _load_projects()
        for pid, p in projs.items():
            if session_id in p.get("sessionIds", []):
                p["sessionIds"] = [s for s in p["sessionIds"] if s != session_id]
        if project_id and project_id in projs:
            if session_id not in projs[project_id]["sessionIds"]:
                projs[project_id]["sessionIds"].append(session_id)
        _save_projects(projs)
        return {"ok": True}


def api_thread_new(project_id: str, alias: str = ""):
    """创建一个新 thread（sessionId），可选挂到 project，可选 alias。返回 sessionId。"""
    new_sid = str(uuid.uuid4())
    # 写 alias到 meta
    if alias:
        with _META_LOCK:
            meta = _load_meta()
            meta[new_sid] = {"alias": alias[:80]}
            _save_meta(meta)
    if project_id:
        api_thread_assign(project_id, new_sid)
    return {"ok": True, "sessionId": new_sid}


def api_stop(session_id: str):
    """发 SIGTERM 给 openclaw agent 进程。"""
    import signal
    with _SEND_LOCK:
        info = _RUNNING.get(session_id)
    if not info:
        return {"ok": False, "error": "not running"}
    pid = info.get("pid")
    try:
        # 杀整个进程组（openclaw agent fork 了子进程）
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"ok": True, "pid": pid}


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
        if p == "/api/stream":
            sid = (qs.get("sessionId") or [""])[0]
            return self._sse_stream(sid)
        if p == "/api/running":
            sid = (qs.get("sessionId") or [""])[0]
            return self._json(200, api_running(sid))
        if p == "/api/projects":
            return self._json(200, api_projects())
        if p == "/api/running-all":
            return self._json(200, api_running_all())
        return self._serve_static(p)

    def _sse_stream(self, session_id: str):
        f = SESSIONS_DIR / f"{session_id}.jsonl"
        if not f.exists():
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("content-type", "text/event-stream; charset=utf-8")
        self.send_header("cache-control", "no-cache")
        self.send_header("x-accel-buffering", "no")  # nginx不缓冲
        self.send_header("connection", "keep-alive")
        self.end_headers()
        try:
            # 从末尾开始 tail，不重发历史
            pos = f.stat().st_size
            last_ping = time.time()
            try:
                self.wfile.write(b"event: hello\ndata: {\"ok\":true}\n\n")
                self.wfile.flush()
            except Exception:
                return
            while True:
                time.sleep(0.4)
                try:
                    size = f.stat().st_size
                except FileNotFoundError:
                    break
                if size < pos:
                    pos = 0  # 文件被重写
                if size > pos:
                    with f.open("rb") as fp:
                        fp.seek(pos)
                        chunk = fp.read(size - pos).decode("utf-8", errors="replace")
                        pos = size
                    for line in chunk.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            e = json.loads(line)
                        except Exception:
                            continue
                        payload = _entry_to_sse(e)
                        if payload is None:
                            continue
                        data = json.dumps(payload, ensure_ascii=False)
                        try:
                            self.wfile.write(f"event: entry\ndata: {data}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            return
                # keepalive ping 每 20s
                now = time.time()
                if now - last_ping > 20:
                    try:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    except Exception:
                        return
                    last_ping = now
        except Exception as ex:
            try:
                self.wfile.write(f"event: error\ndata: {json.dumps({'error': str(ex)})}\n\n".encode("utf-8"))
            except Exception:
                pass

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
            media = data.get("mediaPaths") or []
            if not sid or (not msg and not media):
                return self._json(400, {"error": "sessionId and message/media required"})
            return self._json(200, api_send(sid, msg or "(图片)", media))
        if p == "/api/stop":
            sid = data.get("sessionId", "")
            if not sid:
                return self._json(400, {"error": "sessionId required"})
            return self._json(200, api_stop(sid))
        if p == "/api/upload":
            return self._handle_upload(body)
        if p == "/api/session-meta":
            sid = data.get("sessionId")
            if not sid:
                return self._json(400, {"error": "sessionId required"})
            with _META_LOCK:
                meta = _load_meta()
                cur = meta.get(sid, {})
                for k in ("pinned", "archived", "alias"):
                    if k in data:
                        v = data[k]
                        if k == "alias":
                            cur[k] = str(v)[:80] if v else None
                        else:
                            cur[k] = bool(v)
                # 清理空
                cur = {k: v for k, v in cur.items() if v}
                if cur:
                    meta[sid] = cur
                else:
                    meta.pop(sid, None)
                _save_meta(meta)
            return self._json(200, {"ok": True, "meta": cur})
        if p == "/api/project-upsert":
            pid = (data.get("projectId") or "").strip() or str(uuid.uuid4())
            name = (data.get("name") or "").strip()
            prompt_v = data.get("prompt")
            cwd_v = data.get("cwd")
            return self._json(200, api_project_upsert(pid, name, prompt_v, cwd_v))
        if p == "/api/project-delete":
            pid = (data.get("projectId") or "").strip()
            if not pid:
                return self._json(400, {"error": "projectId required"})
            return self._json(200, api_project_delete(pid))
        if p == "/api/thread-assign":
            sid = (data.get("sessionId") or "").strip()
            pid = (data.get("projectId") or "").strip()
            if not sid:
                return self._json(400, {"error": "sessionId required"})
            return self._json(200, api_thread_assign(pid, sid))
        if p == "/api/thread-new":
            pid = (data.get("projectId") or "").strip()
            alias = (data.get("alias") or "").strip()
            return self._json(200, api_thread_new(pid, alias))
        if p == "/api/thread-assign-batch":
            pid = (data.get("projectId") or "").strip()
            sids = data.get("sessionIds") or []
            if not isinstance(sids, list):
                return self._json(400, {"error": "sessionIds list required"})
            n = 0
            for sid in sids:
                if isinstance(sid, str) and sid.strip():
                    api_thread_assign(pid, sid.strip()); n += 1
            return self._json(200, {"ok": True, "count": n})
        return self._json(404, {"error": "not found"})

    def _handle_upload(self, body: str):
        ctype = self.headers.get("content-type", "")
        if not body:
            return self._json(400, {"error": "empty"})
        if ctype.startswith("application/json"):
            try:
                d = json.loads(body)
            except Exception:
                return self._json(400, {"error": "bad json"})
            durl = d.get("dataUrl", "")
            m = re.match(r"^data:([\w./+-]+);base64,(.+)$", durl, re.S)
            if not m:
                return self._json(400, {"error": "bad dataUrl"})
            mime = m.group(1)
            try:
                raw = base64.b64decode(m.group(2))
            except Exception:
                return self._json(400, {"error": "bad base64"})
            ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}.get(mime, ".bin")
            fname = f"console-{uuid.uuid4()}{ext}"
            fp = MEDIA_DIR / fname
            fp.write_bytes(raw)
            return self._json(200, {"ok": True, "path": str(fp), "mime": mime, "size": len(raw)})
        return self._json(400, {"error": "unsupported content-type, send application/json with dataUrl"})


class ThreadingServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    print(f"console: http://127.0.0.1:{PORT} (frontend={FRONTEND}, agent={AGENT_DIR})")
    ThreadingServer(("127.0.0.1", PORT), H).serve_forever()
