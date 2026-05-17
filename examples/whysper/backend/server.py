"""Whysper backend - voice notes PWA.
Endpoints:
  POST /api/entries          - upload entry (multipart: audio, image?, draft_text?, lat?, lng?)
  GET  /api/entries          - list entries (query: date=YYYY-MM-DD, tag, q, limit, offset)
  GET  /api/entries/{id}     - single entry
  DELETE /api/entries/{id}   - delete
  PATCH /api/entries/{id}    - edit text/tags
  POST /api/organize         - trigger AI organize for today (or date param)
  GET  /api/calendar         - calendar density {YYYY-MM-DD: count}
  GET  /api/stats            - streak + total
  GET  /api/tags             - all tags with counts
  POST /api/ask              - AI Q&A across entries (body: question)
  GET  /media/audio/{name}
  GET  /media/images/{name}
"""
from __future__ import annotations
import os, sqlite3, uuid, json, re, time, asyncio, datetime as dt
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

DATA_ROOT = Path(os.environ.get("WHYSPER_DATA", "/var/whysper-data"))
DATA_ROOT.mkdir(parents=True, exist_ok=True)
(DATA_ROOT / "audio").mkdir(exist_ok=True)
(DATA_ROOT / "images").mkdir(exist_ok=True)
DB_PATH = DATA_ROOT / "db.sqlite"

AI_BASE = os.environ.get("WHYSPER_AI_BASE", "https://new-api.openclaw.ingarena.net")
AI_KEY = os.environ.get("WHYSPER_AI_KEY", "")
AI_MODEL = os.environ.get("WHYSPER_AI_MODEL", "claude-sonnet-4-6")
WHISPER_MODEL = os.environ.get("WHYSPER_WHISPER_MODEL", "gpt-4o-transcribe")

app = FastAPI(title="Whysper")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- DB ----------
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS entries(
          id TEXT PRIMARY KEY,
          created_at INTEGER NOT NULL,
          local_date TEXT NOT NULL,
          audio_file TEXT,
          image_file TEXT,
          draft_text TEXT,
          final_text TEXT,
          title TEXT,
          tags TEXT,
          summary TEXT,
          organized INTEGER DEFAULT 0,
          lat REAL,
          lng REAL
        );
        CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(local_date);
        CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);
        CREATE TABLE IF NOT EXISTS organize_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ran_at INTEGER NOT NULL,
          date TEXT NOT NULL,
          entry_count INTEGER,
          ok INTEGER,
          note TEXT
        );
        """)
init_db()

# ---------- helpers ----------
def now_ts():
    return int(time.time())

def today_local():
    # Asia/Singapore = UTC+8
    return (dt.datetime.utcnow() + dt.timedelta(hours=8)).strftime("%Y-%m-%d")

def ts_to_local_date(ts: int) -> str:
    return (dt.datetime.utcfromtimestamp(ts) + dt.timedelta(hours=8)).strftime("%Y-%m-%d")

def row_to_dict(r):
    d = dict(r)
    if d.get("tags"):
        try: d["tags"] = json.loads(d["tags"])
        except Exception: d["tags"] = []
    else:
        d["tags"] = []
    return d

# ---------- AI ----------
async def ai_chat(messages, max_tokens=900, temperature=0.4) -> str:
    if not AI_KEY:
        return ""
    url = AI_BASE.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {AI_KEY}", "Content-Type": "application/json"}
    payload = {"model": AI_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    async with httpx.AsyncClient(timeout=90) as cli:
        r = await cli.post(url, headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"]

async def transcribe(audio_path: Path) -> str:
    """Use gateway-compatible whisper endpoint if available. Retry on 5xx."""
    if not AI_KEY:
        return ""
    url = AI_BASE.rstrip("/") + "/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {AI_KEY}"}
    last_err = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=180) as cli:
                with open(audio_path, "rb") as f:
                    files = {"file": (audio_path.name, f, "audio/webm")}
                    data = {
                        "model": WHISPER_MODEL,
                        "language": "zh",
                        "prompt": "中文语音笔记，可能包含人名、品牌名、代码片段、中英文混合。",
                        "temperature": "0",
                    }
                    r = await cli.post(url, headers=headers, files=files, data=data)
                    if r.status_code >= 500:
                        last_err = f"{r.status_code} {r.text[:120]}"
                        await asyncio.sleep(1.5 * (attempt+1))
                        continue
                    r.raise_for_status()
                    j = r.json()
                    return j.get("text", "") or ""
        except Exception as e:
            last_err = str(e)
            await asyncio.sleep(1.5 * (attempt+1))
    print(f"[transcribe] failed after retry: {last_err}")
    return ""

def _extract_json(text: str):
    if not text: return None
    m = re.search(r'\{[\s\S]*\}', text)
    if not m: return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

# ---------- endpoints ----------
@app.post("/api/entries")
async def create_entry(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    draft_text: str = Form(""),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
):
    eid = uuid.uuid4().hex[:12]
    audio_name = None
    image_name = None
    final_text = draft_text or ""

    if audio is not None:
        ext = ".webm"
        if audio.filename and "." in audio.filename:
            ext = "." + audio.filename.rsplit(".", 1)[-1].lower()
            if ext not in (".webm", ".mp4", ".m4a", ".mp3", ".ogg", ".wav"): ext = ".webm"
        audio_name = f"{eid}{ext}"
        ap = DATA_ROOT / "audio" / audio_name
        ap.write_bytes(await audio.read())
        # server-side transcribe (preferred over browser draft)
        tx = await transcribe(ap)
        if tx and tx.strip():
            final_text = tx.strip()

    if image is not None:
        ext = ".jpg"
        if image.filename and "." in image.filename:
            ext = "." + image.filename.rsplit(".", 1)[-1].lower()
            if ext not in (".jpg",".jpeg",".png",".webp",".heic"): ext = ".jpg"
        image_name = f"{eid}{ext}"
        (DATA_ROOT / "images" / image_name).write_bytes(await image.read())

    ts = now_ts()
    with db() as c:
        c.execute("""INSERT INTO entries(id,created_at,local_date,audio_file,image_file,draft_text,final_text,lat,lng)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (eid, ts, ts_to_local_date(ts), audio_name, image_name, draft_text, final_text, lat, lng))
    return {"id": eid, "final_text": final_text, "audio_file": audio_name, "image_file": image_name, "created_at": ts}

@app.get("/api/entries")
def list_entries(date: Optional[str] = None, tag: Optional[str] = None, q: Optional[str] = None,
                 limit: int = 100, offset: int = 0):
    sql = "SELECT * FROM entries WHERE 1=1"
    args = []
    if date:
        sql += " AND local_date=?"
        args.append(date)
    if q:
        sql += " AND (final_text LIKE ? OR title LIKE ? OR tags LIKE ?)"
        like = f"%{q}%"; args += [like, like, like]
    if tag:
        sql += " AND tags LIKE ?"
        args.append(f"%\"{tag}\"%")
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    args += [limit, offset]
    with db() as c:
        rows = [row_to_dict(r) for r in c.execute(sql, args)]
    return {"entries": rows, "total": len(rows)}

@app.get("/api/entries/{eid}")
def get_entry(eid: str):
    with db() as c:
        r = c.execute("SELECT * FROM entries WHERE id=?", (eid,)).fetchone()
        if not r: raise HTTPException(404)
        return row_to_dict(r)

@app.patch("/api/entries/{eid}")
async def patch_entry(eid: str, body: dict):
    fields = {}
    for k in ("final_text","title","summary"):
        if k in body: fields[k] = body[k]
    if "tags" in body:
        fields["tags"] = json.dumps(body["tags"], ensure_ascii=False)
    if not fields: return {"ok": True}
    sets = ",".join(f"{k}=?" for k in fields)
    with db() as c:
        c.execute(f"UPDATE entries SET {sets} WHERE id=?", (*fields.values(), eid))
    return {"ok": True}

@app.delete("/api/entries/{eid}")
def delete_entry(eid: str):
    with db() as c:
        r = c.execute("SELECT audio_file,image_file FROM entries WHERE id=?", (eid,)).fetchone()
        if not r: raise HTTPException(404)
        for sub, name in (("audio", r["audio_file"]), ("images", r["image_file"])):
            if name:
                try: (DATA_ROOT/sub/name).unlink(missing_ok=True)
                except Exception: pass
        c.execute("DELETE FROM entries WHERE id=?", (eid,))
    return {"ok": True}

@app.get("/api/calendar")
def calendar(year: Optional[int] = None, month: Optional[int] = None):
    with db() as c:
        rows = c.execute("SELECT local_date, COUNT(*) AS n FROM entries GROUP BY local_date").fetchall()
    out = {r["local_date"]: r["n"] for r in rows}
    if year and month:
        prefix = f"{year:04d}-{month:02d}-"
        out = {k:v for k,v in out.items() if k.startswith(prefix)}
    return out

@app.get("/api/stats")
def stats():
    with db() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM entries").fetchone()["n"]
        dates = [r["local_date"] for r in c.execute("SELECT DISTINCT local_date FROM entries ORDER BY local_date DESC")]
    # streak
    streak = 0
    today = today_local()
    cur = dt.date.fromisoformat(today)
    s = set(dates)
    while cur.isoformat() in s:
        streak += 1
        cur -= dt.timedelta(days=1)
    return {"total": total, "streak": streak, "today": today, "today_count": sum(1 for d in dates if d == today)}

@app.get("/api/tags")
def list_tags():
    with db() as c:
        rows = c.execute("SELECT tags FROM entries WHERE tags IS NOT NULL").fetchall()
    counter = {}
    for r in rows:
        try:
            for t in json.loads(r["tags"] or "[]"):
                counter[t] = counter.get(t, 0) + 1
        except Exception: pass
    return sorted([{"tag": k, "count": v} for k,v in counter.items()], key=lambda x: -x["count"])

@app.post("/api/organize")
async def organize(body: dict = None):
    body = body or {}
    date = body.get("date") or today_local()
    with db() as c:
        rows = [row_to_dict(r) for r in c.execute("SELECT * FROM entries WHERE local_date=? ORDER BY created_at ASC", (date,))]
    if not rows:
        return {"ok": False, "reason": "no entries", "date": date}
    payload_items = [{"id": r["id"], "text": (r.get("final_text") or r.get("draft_text") or "").strip()} for r in rows]
    prompt = (
        "你是一个个人笔记整理助手。下面是用户今天用语音随手记的想法碎片（已转写为文字，可能有错别字）。\n"
        "请你做三件事，对每一条单独输出：\n"
        "1) 修正明显错别字，但保留原意和口语感（不要改写润色）。\n"
        "2) 提取一句不超过 18 字的标题。\n"
        "3) 给 1-3 个自由标签（中文短词，比如 vlog、想法、待办、感悟、阅读、人际、健康）。\n"
        "严格输出 JSON：{\"items\":[{\"id\":\"...\",\"title\":\"...\",\"final_text\":\"...\",\"tags\":[\"...\"]}, ...]}\n"
        "另外加一个 \"summary\" 字段，用一段不超过 80 字的中文总结今天的核心主题。\n"
        "不要任何解释，只输出 JSON。\n\n"
        f"输入条目：\n{json.dumps(payload_items, ensure_ascii=False, indent=2)}"
    )
    try:
        raw = await ai_chat([{"role":"user","content":prompt}], max_tokens=2000, temperature=0.3)
    except Exception as e:
        with db() as c:
            c.execute("INSERT INTO organize_runs(ran_at,date,entry_count,ok,note) VALUES(?,?,?,?,?)",
                      (now_ts(), date, len(rows), 0, f"ai_err: {e}"))
        return {"ok": False, "reason": f"ai_err: {e}"}
    data = _extract_json(raw)
    if not data or "items" not in data:
        with db() as c:
            c.execute("INSERT INTO organize_runs(ran_at,date,entry_count,ok,note) VALUES(?,?,?,?,?)",
                      (now_ts(), date, len(rows), 0, "parse_fail"))
        return {"ok": False, "reason": "parse_fail", "raw": raw[:500]}
    summary = data.get("summary", "")
    items = data.get("items", [])
    updated = 0
    with db() as c:
        for it in items:
            eid = it.get("id")
            if not eid: continue
            c.execute("UPDATE entries SET title=?, final_text=?, tags=?, summary=?, organized=1 WHERE id=?",
                      (it.get("title",""), it.get("final_text",""), json.dumps(it.get("tags",[]), ensure_ascii=False),
                       summary, eid))
            updated += 1
        c.execute("INSERT INTO organize_runs(ran_at,date,entry_count,ok,note) VALUES(?,?,?,?,?)",
                  (now_ts(), date, len(rows), 1, f"updated={updated}"))
    return {"ok": True, "date": date, "updated": updated, "summary": summary}

@app.post("/api/ask")
async def ask(body: dict):
    q = (body.get("question") or "").strip()
    if not q: raise HTTPException(400, "empty question")
    with db() as c:
        rows = [row_to_dict(r) for r in c.execute("SELECT id,local_date,title,final_text,tags FROM entries ORDER BY created_at DESC LIMIT 500")]
    corpus = [f"[{r['local_date']}] {r.get('title') or ''} | {r.get('final_text') or ''} | 标签:{','.join(r.get('tags',[]))}" for r in rows]
    prompt = (
        "下面是用户的语音笔记历史。请根据用户的问题，从中找出相关条目并用中文简洁回答。\n"
        "回答风格：直接、不啰嗦。如果找到相关条目，引用日期和原文片段。如果没有相关内容，明说没找到。\n\n"
        f"用户问题：{q}\n\n"
        "笔记历史：\n" + "\n".join(corpus[:300])
    )
    try:
        ans = await ai_chat([{"role":"user","content":prompt}], max_tokens=700, temperature=0.5)
    except Exception as e:
        return {"answer": f"[AI 调用失败] {e}"}
    return {"answer": ans}

# ---------- media ----------
@app.get("/media/audio/{name}")
def get_audio(name: str):
    p = DATA_ROOT / "audio" / name
    if not p.exists(): raise HTTPException(404)
    return FileResponse(str(p))

@app.get("/media/images/{name}")
def get_image(name: str):
    p = DATA_ROOT / "images" / name
    if not p.exists(): raise HTTPException(404)
    return FileResponse(str(p))

@app.get("/api/health")
def health():
    return {"ok": True, "ts": now_ts(), "data": str(DATA_ROOT)}
