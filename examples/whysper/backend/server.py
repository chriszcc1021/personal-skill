"""Whysper backend - voice notes PWA.
Endpoints:
  POST /api/entries          - upload entry (multipart: audio, image?, draft_text?, lat?, lng?)
  GET  /api/entries          - list entries (query: date=YYYY-MM-DD, tag, q, limit, offset)
  GET  /api/entries/{id}     - single entry
  DELETE /api/entries/{id}   - delete
  PATCH /api/entries/{id}    - edit text/tags
  POST /api/organize         - trigger AI organize for today (or date param)
  GET  /api/entries/{id}/calendar-items - calendar-worthy events/tasks/codes
  GET  /api/ledger/candidates - review-first ledger candidates
  GET  /api/ledger/entries    - confirmed ledger entries
  GET  /api/calendar         - calendar density {YYYY-MM-DD: count}
  GET  /api/stats            - streak + total
  GET  /api/tags             - all tags with counts
  POST /api/ask              - AI Q&A across entries (body: question)
  GET  /media/audio/{name}
  GET  /media/images/{name}
"""
from __future__ import annotations
import os, sqlite3, uuid, json, re, time, asyncio, base64, datetime as dt
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

DATA_ROOT = Path(os.environ.get("WHYSPER_DATA", "/var/whysper-data"))
DATA_ROOT.mkdir(parents=True, exist_ok=True)
(DATA_ROOT / "audio").mkdir(exist_ok=True)
(DATA_ROOT / "images").mkdir(exist_ok=True)
DB_PATH = DATA_ROOT / "db.sqlite"

AI_BASE = os.environ.get("WHYSPER_AI_BASE", "https://new-api.openclaw.ingarena.net")
AI_KEY = os.environ.get("WHYSPER_AI_KEY", "")
AI_MODEL = os.environ.get("WHYSPER_AI_MODEL", "claude-sonnet-4-6")
WHISPER_MODEL = os.environ.get("WHYSPER_WHISPER_MODEL", "gpt-4o-transcribe")
WHISPER_CLI = os.environ.get("WHYSPER_WHISPER_CLI", "/opt/whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL_PATH = os.environ.get("WHYSPER_WHISPER_MODEL_PATH", "/opt/whisper.cpp/models/ggml-medium-q5_0.bin")
WHISPER_THREADS = int(os.environ.get("WHYSPER_WHISPER_THREADS", "4"))
CAPTURE_MODES = {"auto", "note", "ledger"}
MAX_UPLOAD_MB = int(os.environ.get("WHYSPER_MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

app = FastAPI(title="Whysper")

@app.get("/api/version")
def version():
    try:
        v = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
    except Exception: v = ""
    return {
        "version": v,
        "git_sha": os.environ.get("GIT_SHA", ""),
        "deployed_at": os.environ.get("DEPLOYED_AT", ""),
    }
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=512)

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
          transcribing INTEGER DEFAULT 0,
          lat REAL,
          lng REAL
        );
        CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(local_date);
        CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);
        """)
        # add transcribing column if missing (migration)
        cols = [r[1] for r in c.execute("PRAGMA table_info(entries)")]
        if "transcribing" not in cols:
            try: c.execute("ALTER TABLE entries ADD COLUMN transcribing INTEGER DEFAULT 0")
            except Exception: pass
        if "meta" not in cols:
            try: c.execute("ALTER TABLE entries ADD COLUMN meta TEXT")
            except Exception: pass
        if "source" not in cols:
            try: c.execute("ALTER TABLE entries ADD COLUMN source TEXT DEFAULT 'app'")
            except Exception: pass
        if "processing_stage" not in cols:
            try: c.execute("ALTER TABLE entries ADD COLUMN processing_stage TEXT")
            except Exception: pass
        if "processing_status" not in cols:
            try: c.execute("ALTER TABLE entries ADD COLUMN processing_status TEXT")
            except Exception: pass
        if "processing_error" not in cols:
            try: c.execute("ALTER TABLE entries ADD COLUMN processing_error TEXT")
            except Exception: pass
        if "capture_mode" not in cols:
            try: c.execute("ALTER TABLE entries ADD COLUMN capture_mode TEXT DEFAULT 'auto'")
            except Exception: pass
        c.executescript("""
        CREATE TABLE IF NOT EXISTS organize_runs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ran_at INTEGER NOT NULL,
          date TEXT NOT NULL,
          entry_count INTEGER,
          ok INTEGER,
          note TEXT
        );
        CREATE TABLE IF NOT EXISTS ledger_candidates(
          id TEXT PRIMARY KEY,
          source_entry_id TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          status TEXT DEFAULT 'pending',
          merchant TEXT,
          amount REAL,
          currency TEXT DEFAULT 'CNY',
          paid_at TEXT,
          category TEXT,
          payment_method TEXT,
          note TEXT,
          confidence REAL,
          raw_json TEXT,
          tags TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ledger_candidates_status ON ledger_candidates(status);
        CREATE INDEX IF NOT EXISTS idx_ledger_candidates_entry ON ledger_candidates(source_entry_id);
        CREATE TABLE IF NOT EXISTS ledger_entries(
          id TEXT PRIMARY KEY,
          candidate_id TEXT,
          source_entry_id TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          confirmed_at INTEGER NOT NULL,
          merchant TEXT,
          amount REAL,
          currency TEXT,
          paid_at TEXT,
          category TEXT,
          payment_method TEXT,
          note TEXT,
          tags TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ledger_entries_created ON ledger_entries(created_at);
        """)
        for tbl in ("ledger_candidates", "ledger_entries"):
            try: c.execute(f"ALTER TABLE {tbl} ADD COLUMN tags TEXT")
            except Exception: pass
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
    if d.get("meta"):
        try: d["meta"] = json.loads(d["meta"])
        except Exception: d["meta"] = {}
    else:
        d["meta"] = {}
    d["calendar_items"] = calendar_items_from_entry(d)
    if not d.get("processing_status"):
        if d.get("transcribing"):
            d["processing_status"] = "running"
        elif d.get("organized"):
            d["processing_status"] = "done"
        else:
            d["processing_status"] = "idle"
    if not d.get("processing_stage"):
        if d.get("transcribing"):
            d["processing_stage"] = "vision" if d.get("image_file") else "transcribe"
        else:
            d["processing_stage"] = ""
    if not d.get("capture_mode"):
        d["capture_mode"] = "auto"
    return d

def simple_row(r):
    if not r:
        return None
    d = dict(r)
    for k in ("tags",):
        if k in d and d.get(k):
            try: d[k] = json.loads(d[k])
            except Exception: d[k] = []
        elif k in d:
            d[k] = []
    if d.get("raw_json"):
        try: d["raw_json"] = json.loads(d["raw_json"])
        except Exception: pass
    return d

LEDGER_CATEGORIES = {
    "food": "餐饮",
    "transport": "交通",
    "shopping": "购物",
    "entertainment": "娱乐",
    "housing": "居住",
    "health": "医疗",
    "education": "学习",
    "travel": "旅行",
    "business": "工作",
    "subscription": "订阅",
    "transfer": "转账",
    "other": "其他",
}

LEDGER_CATEGORY_ALIASES = {
    "餐饮": "food",
    "吃饭": "food",
    "咖啡": "food",
    "交通": "transport",
    "出行": "transport",
    "打车": "transport",
    "购物": "shopping",
    "娱乐": "entertainment",
    "游戏": "entertainment",
    "电影": "entertainment",
    "居住": "housing",
    "住房": "housing",
    "房租": "housing",
    "医疗": "health",
    "健康": "health",
    "学习": "education",
    "教育": "education",
    "旅行": "travel",
    "旅游": "travel",
    "工作": "business",
    "商务": "business",
    "订阅": "subscription",
    "会员": "subscription",
    "转账": "transfer",
    "其他": "other",
}

def normalize_ledger_category(value) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return "other"
    if raw in LEDGER_CATEGORIES:
        return raw
    return LEDGER_CATEGORY_ALIASES.get(str(value or "").strip(), "other")

async def write_upload_limited(upload: UploadFile, dest: Path, used_bytes: int = 0) -> int:
    total = used_bytes
    written = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, f"upload exceeds {MAX_UPLOAD_MB} MB")
                f.write(chunk)
                written += len(chunk)
    except Exception:
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    return written

def as_float(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None

def _parse_iso(iso: str):
    try:
        if not iso: return None
        d = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
        return d
    except Exception:
        return None

def _iso_plus_minutes(iso: str, minutes: int = 30) -> str:
    d = _parse_iso(iso)
    if not d: return ""
    return (d + dt.timedelta(minutes=minutes)).isoformat()

def calendar_items_from_entry(e: dict) -> list[dict]:
    """Normalize AI events, task due dates, and code expirations into calendar-worthy items."""
    meta = e.get("meta") or {}
    items = []
    for i, ev in enumerate(meta.get("events") or []):
        start = ev.get("start_iso") or ""
        if not start: continue
        items.append({
            "id": f"event-{i}",
            "type": "event",
            "title": ev.get("title") or e.get("title") or "Whysper 事件",
            "start_iso": start,
            "end_iso": ev.get("end_iso") or _iso_plus_minutes(start, 30),
            "location": ev.get("location") or "",
            "notes": ev.get("notes") or e.get("summary") or "",
            "alert_min": ev.get("alert_min") if ev.get("alert_min") is not None else 30,
        })
    for i, task in enumerate(meta.get("tasks") or []):
        due = task.get("due_iso") or ""
        if not due: continue
        title = task.get("text") or e.get("title") or "Whysper 待办"
        items.append({
            "id": f"task-{i}",
            "type": "task",
            "title": title,
            "start_iso": due,
            "end_iso": _iso_plus_minutes(due, 30),
            "location": "",
            "notes": e.get("summary") or e.get("final_text") or "",
            "alert_min": 30,
        })
    for i, code in enumerate(meta.get("codes") or []):
        exp = code.get("expire_iso") or ""
        if not exp: continue
        kind = code.get("kind") or "码"
        value = code.get("value") or ""
        items.append({
            "id": f"code-{i}",
            "type": "code",
            "title": f"{kind}过期提醒",
            "start_iso": exp,
            "end_iso": _iso_plus_minutes(exp, 15),
            "location": "",
            "notes": f"{kind}: {value}" if value else kind,
            "alert_min": 30,
        })
    return items

def ensure_ledger_candidate(source_entry_id: str, seed_text: str = "") -> dict:
    with db() as c:
        existing = c.execute("SELECT * FROM ledger_candidates WHERE source_entry_id=?", (source_entry_id,)).fetchone()
        if existing:
            return simple_row(existing)
        cid = uuid.uuid4().hex[:12]
        c.execute("""INSERT INTO ledger_candidates(id,source_entry_id,created_at,status,currency,note,confidence)
                     VALUES(?,?,?,?,?,?,?)""",
                  (cid, source_entry_id, now_ts(), "pending", "CNY", seed_text or "", 0.0))
        return simple_row(c.execute("SELECT * FROM ledger_candidates WHERE id=?", (cid,)).fetchone())

def update_ledger_candidate_from_ai(source_entry_id: str, data: dict):
    ensure_ledger_candidate(source_entry_id)
    fields = {
        "merchant": (data.get("merchant") or "").strip(),
        "amount": as_float(data.get("amount")),
        "currency": (data.get("currency") or "CNY").strip() or "CNY",
        "paid_at": (data.get("paid_at") or "").strip(),
        "category": normalize_ledger_category(data.get("category")),
        "payment_method": (data.get("payment_method") or "").strip(),
        "note": (data.get("note") or "").strip(),
        "confidence": as_float(data.get("confidence")),
        "raw_json": json.dumps(data, ensure_ascii=False),
    }
    with db() as c:
        sets = ",".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE ledger_candidates SET {sets} WHERE source_entry_id=?", (*fields.values(), source_entry_id))

def maybe_ledger_data(data: dict) -> dict | None:
    ledger = data.get("ledger") or {}
    if not isinstance(ledger, dict):
        return None
    amount = as_float(ledger.get("amount"))
    merchant = (ledger.get("merchant") or "").strip()
    is_expense = ledger.get("is_expense")
    if is_expense is False:
        return None
    if amount is None and not merchant:
        return None
    ledger["amount"] = amount
    ledger["category"] = normalize_ledger_category(ledger.get("category"))
    return ledger

# ---------- AI ----------
async def ai_chat(messages, max_tokens=900, temperature=0.4) -> str:
    if not AI_KEY:
        return ""
    url = AI_BASE.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {AI_KEY}", "Content-Type": "application/json"}
    payload = {"model": AI_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    async with httpx.AsyncClient(timeout=180) as cli:
        r = await cli.post(url, headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"]

async def transcribe(audio_path: Path) -> str:
    """Local whisper.cpp transcription. Returns text or ''."""
    cli = Path(WHISPER_CLI)
    mdl = Path(WHISPER_MODEL_PATH)
    if not cli.exists() or not mdl.exists():
        print(f"[transcribe] whisper-cli or model missing: {cli} / {mdl}")
        return ""
    # convert to 16k mono wav (use a tmp path different from source)
    import tempfile
    wav_fd, wav_str = tempfile.mkstemp(suffix=".wav", prefix="whysper_tx_")
    os.close(wav_fd)
    wav_path = Path(wav_str)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0 or not wav_path.exists():
            print(f"[transcribe] ffmpeg failed")
            return ""
        # whisper-cli with zh
        p = await asyncio.create_subprocess_exec(
            str(cli), "-m", str(mdl), "-l", "zh", "-f", str(wav_path),
            "-np", "-nt", "-t", str(WHISPER_THREADS),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await p.communicate()
        txt = (out or b"").decode("utf-8", errors="ignore").strip()
        return txt
    except Exception as e:
        print(f"[transcribe] error: {e}")
        return ""
    finally:
        try:
            if wav_path.exists(): wav_path.unlink()
        except Exception: pass

def _extract_json(text: str):
    if not text: return None
    m = re.search(r'\{[\s\S]*\}', text)
    if not m: return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

async def _transcribe_and_update(eid: str, audio_path: Path):
    """Background task: run whisper.cpp, update entry on success."""
    try:
        with db() as c:
            c.execute("""UPDATE entries SET transcribing=1, processing_stage='transcribe',
                         processing_status='running', processing_error=NULL WHERE id=?""", (eid,))
        tx = await transcribe(audio_path)
        if tx and tx.strip():
            with db() as c:
                c.execute("""UPDATE entries SET final_text=?, transcribing=0, processing_stage='transcribe',
                             processing_status='done', processing_error=NULL WHERE id=?""", (tx.strip(), eid))
            print(f"[transcribe] {eid} done: {tx[:40]}")
        else:
            with db() as c:
                c.execute("""UPDATE entries SET transcribing=0, processing_stage='transcribe',
                             processing_status='failed', processing_error='empty transcription' WHERE id=?""", (eid,))
            print(f"[transcribe] {eid} empty result")
    except Exception as e:
        with db() as c:
            c.execute("""UPDATE entries SET transcribing=0, processing_stage='transcribe',
                         processing_status='failed', processing_error=? WHERE id=?""", (str(e)[:200], eid))
        print(f"[transcribe] {eid} error: {e}")


VISION_PROMPT = """你是个个人外挂大脑。看这张截图，抽取用户应该记住、提醒、或收藏的结构化信息。
今天是 {today} (Asia/Singapore)。以下是输出格式，严格 JSON，不要任何解释：

{{
  "route": ["knowledge"],
  "summary": "一句话总结这张图是什么 (不超 50 字)",
  "title": "一句话标题 (不超 18 字)",
  "text": "图里的关键文本内容提取 (OCR + 理解后的难表述，完整 250 字以内)",
  "tags": ["..."],
  "ledger": {{"is_expense": false, "merchant": "", "amount": null, "currency": "CNY", "paid_at": "", "category": "food|transport|shopping|entertainment|housing|health|education|travel|business|subscription|transfer|other", "payment_method": "", "note": "", "confidence": 0.0}},
  "events": [{{"title":"...", "start_iso":"2026-05-18T14:00:00+08:00", "end_iso":"2026-05-18T15:00:00+08:00", "location":"...", "notes":"...", "alert_min":30}}],
  "codes": [{{"kind":"取件码/兑换码/取餐号", "value":"1234", "expire_iso":null}}],
  "tasks": [{{"text":"...", "due_iso":null}}],
  "key_points": ["..."]
}}

规则：
- 推断时间时遵照当地 +08:00。“明天”就是 {today}+1。
- 有明确时间 + 事件 才填 events，否则留空数组。
- 机票/火车票 alert_min 设 120，其他默认 30。
- 如果截图是支付、收据、订单、账单、转账或消费记录，ledger.is_expense=true，并尽量提取 merchant/amount/paid_at/category/payment_method；category 必须从枚举里选，娱乐消费用 entertainment；不要编造金额。
- codes 只抽实际可复制使用的短码（取件码、核销码、热锁、取餐号）。
- tasks 限明确“我”需要完成的事项。
- 如果是文章/帖子，重点摆 key_points，不产生 events/codes/ledger。
- 不要手动转义引号，在 JSON 里用双引号即可。
"""

async def _vision_extract_and_update(eid: str, image_path: Path, capture_mode: str = "auto"):
    """Background task: send image to multimodal Claude, store structured meta."""
    if not AI_KEY or not image_path.exists():
        reason = "AI key missing" if not AI_KEY else "image file missing"
        with db() as c:
            c.execute("""UPDATE entries SET transcribing=0, processing_stage='vision',
                         processing_status='failed', processing_error=? WHERE id=?""", (reason, eid))
        return
    try:
        with db() as c:
            c.execute("""UPDATE entries SET transcribing=1, processing_stage='vision',
                         processing_status='running', processing_error=NULL WHERE id=?""", (eid,))
        b64 = base64.b64encode(image_path.read_bytes()).decode()
        ext = image_path.suffix.lstrip('.').lower()
        mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp","heic":"image/heic"}.get(ext, "image/jpeg")
        today = ts_to_local_date(now_ts())
        prompt = VISION_PROMPT.format(today=today)
        msg = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": prompt},
            ],
        }]
        raw = await ai_chat(msg, max_tokens=1800, temperature=0.2)
        data = _extract_json(raw) or {}
        ledger_data = maybe_ledger_data(data)
        if capture_mode == "ledger" and not ledger_data:
            ledger_data = {"is_expense": True, "merchant": "", "amount": None, "currency": "CNY", "category": "other", "note": "AI 未能从截图中稳定提取消费信息", "confidence": 0.0}
        if ledger_data:
            update_ledger_candidate_from_ai(eid, ledger_data)
        text = (data.get("text") or "").strip()
        title = (data.get("title") or "").strip()
        summary = (data.get("summary") or "").strip()
        tags = data.get("tags") or []
        if ledger_data and "ledger" not in tags:
            tags = [*tags, "ledger"]
        meta = {
            "route": data.get("route") or [],
            "ledger_candidate": ledger_data or None,
            "events": data.get("events") or [],
            "codes": data.get("codes") or [],
            "tasks": data.get("tasks") or [],
            "key_points": data.get("key_points") or [],
        }
        with db() as c:
            c.execute("""UPDATE entries SET final_text=?, title=?, summary=?, tags=?, meta=?, transcribing=0,
                         organized=1, processing_stage='vision', processing_status='done', processing_error=NULL WHERE id=?""",
                      (text or summary or "", title, summary, json.dumps(tags, ensure_ascii=False), json.dumps(meta, ensure_ascii=False), eid))
        print(f"[vision] {eid} done: {title}")
    except Exception as e:
        with db() as c:
            c.execute("""UPDATE entries SET transcribing=0, processing_stage='vision',
                         processing_status='failed', processing_error=? WHERE id=?""", (str(e)[:200], eid))
        print(f"[vision] {eid} error: {e}")

# ---------- endpoints ----------
@app.post("/api/entries")
async def create_entry(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    draft_text: str = Form(""),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    source: str = Form("app"),
    capture_mode: str = Form("auto"),
):
    capture_mode = capture_mode if capture_mode in CAPTURE_MODES else "auto"
    eid = uuid.uuid4().hex[:12]
    audio_name = None
    image_name = None
    final_text = draft_text or ""
    total_upload_bytes = 0
    saved_paths: list[Path] = []
    audio_path: Optional[Path] = None

    try:
        if audio is not None:
            ext = ".webm"
            if audio.filename and "." in audio.filename:
                ext = "." + audio.filename.rsplit(".", 1)[-1].lower()
                if ext not in (".webm", ".mp4", ".m4a", ".mp3", ".ogg", ".wav"): ext = ".webm"
            audio_name = f"{eid}{ext}"
            ap = DATA_ROOT / "audio" / audio_name
            total_upload_bytes += await write_upload_limited(audio, ap, total_upload_bytes)
            saved_paths.append(ap)
            audio_path = ap

        if image is not None:
            ext = ".jpg"
            if image.filename and "." in image.filename:
                ext = "." + image.filename.rsplit(".", 1)[-1].lower()
                if ext not in (".jpg",".jpeg",".png",".webp",".heic"): ext = ".jpg"
            image_name = f"{eid}{ext}"
            ip = DATA_ROOT / "images" / image_name
            total_upload_bytes += await write_upload_limited(image, ip, total_upload_bytes)
            saved_paths.append(ip)
    except HTTPException:
        for p in saved_paths:
            try: p.unlink(missing_ok=True)
            except Exception: pass
        raise

    ts = now_ts()
    processing_stage = "vision" if image_name else ("transcribe" if audio_name else "")
    processing_status = "running" if (audio_name or image_name) else "idle"
    transcribing = 1 if (audio_name or image_name) else 0
    with db() as c:
        c.execute("""INSERT INTO entries(id,created_at,local_date,audio_file,image_file,draft_text,final_text,lat,lng,source,
                     transcribing,processing_stage,processing_status,capture_mode)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (eid, ts, ts_to_local_date(ts), audio_name, image_name, draft_text, final_text, lat, lng, source,
                   transcribing, processing_stage, processing_status, capture_mode))
    if audio_path:
        # server-side transcribe (async — return entry with draft immediately, update later)
        asyncio.create_task(_transcribe_and_update(eid, audio_path))
    # if image present, fire vision extraction in background
    if image_name:
        if capture_mode == "ledger":
            ensure_ledger_candidate(eid, draft_text or "")
        asyncio.create_task(_vision_extract_and_update(eid, DATA_ROOT / "images" / image_name, capture_mode))
    return {"id": eid, "final_text": final_text, "audio_file": audio_name, "image_file": image_name,
            "created_at": ts, "transcribing": transcribing, "processing_stage": processing_stage,
            "processing_status": processing_status, "source": source, "capture_mode": capture_mode}

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

@app.get("/api/day-summary")
def day_summary(date: str):
    with db() as c:
        rows = [row_to_dict(r) for r in c.execute(
            "SELECT * FROM entries WHERE local_date=? ORDER BY created_at ASC", (date,))]
    if not rows:
        return {"ok": True, "date": date, "count": 0, "summary": "", "organized": False, "titles": [], "tags": []}
    # any non-empty summary from organized entries
    summary = ""
    for r in rows:
        if r.get("summary"):
            summary = r["summary"]; break
    organized = all(r.get("organized") for r in rows) and bool(summary)
    titles = [r["title"] for r in rows if r.get("title")]
    tag_set = []
    for r in rows:
        try:
            for t in json.loads(r.get("tags") or "[]"):
                if t not in tag_set: tag_set.append(t)
        except Exception: pass
    return {"ok": True, "date": date, "count": len(rows), "summary": summary,
            "organized": organized, "titles": titles, "tags": tag_set}

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

# ---------- ledger ----------
@app.get("/api/ledger/categories")
def list_ledger_categories():
    with db() as c:
        rows = c.execute("SELECT lower(coalesce(category,'other')) AS category, COUNT(*) AS n FROM ledger_entries GROUP BY category").fetchall()
    counts = {}
    for r in rows:
        key = normalize_ledger_category(r["category"])
        counts[key] = counts.get(key, 0) + r["n"]
    return {
        "categories": [
            {"category": key, "label": label, "count": counts.get(key, 0)}
            for key, label in LEDGER_CATEGORIES.items()
        ]
    }

@app.get("/api/ledger/candidates")
def list_ledger_candidates(status: str = "pending", limit: int = 100):
    sql = "SELECT * FROM ledger_candidates"
    args = []
    if status != "all":
        sql += " WHERE status=?"
        args.append(status)
    sql += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    with db() as c:
        rows = [simple_row(r) for r in c.execute(sql, args)]
    return {"candidates": rows, "total": len(rows)}

@app.patch("/api/ledger/candidates/{cid}")
async def patch_ledger_candidate(cid: str, body: dict):
    allowed = {"merchant", "amount", "currency", "paid_at", "category", "payment_method", "note", "confidence", "status", "tags"}
    fields = {k: body[k] for k in allowed if k in body}
    if "amount" in fields:
        fields["amount"] = as_float(fields["amount"])
    if "confidence" in fields:
        fields["confidence"] = as_float(fields["confidence"])
    if "category" in fields:
        fields["category"] = normalize_ledger_category(fields["category"])
    if "tags" in fields:
        v = fields["tags"]
        if isinstance(v, list):
            fields["tags"] = json.dumps([str(t).strip() for t in v if str(t).strip()], ensure_ascii=False)
        elif isinstance(v, str):
            fields["tags"] = json.dumps([x.strip() for x in v.split(",") if x.strip()], ensure_ascii=False)
        elif v is None:
            fields["tags"] = None
    if not fields:
        return {"ok": True}
    sets = ",".join(f"{k}=?" for k in fields)
    with db() as c:
        c.execute(f"UPDATE ledger_candidates SET {sets} WHERE id=?", (*fields.values(), cid))
        row = c.execute("SELECT * FROM ledger_candidates WHERE id=?", (cid,)).fetchone()
        if not row: raise HTTPException(404)
    return {"ok": True, "candidate": simple_row(row)}

@app.post("/api/ledger/candidates/{cid}/confirm")
def confirm_ledger_candidate(cid: str):
    with db() as c:
        r = c.execute("SELECT * FROM ledger_candidates WHERE id=?", (cid,)).fetchone()
        if not r: raise HTTPException(404)
        item = simple_row(r)
        tags_json = json.dumps(item.get("tags") or [], ensure_ascii=False) if isinstance(item.get("tags"), list) else None
        entry_id = uuid.uuid4().hex[:12]
        confirmed_at = now_ts()
        c.execute("""INSERT INTO ledger_entries(id,candidate_id,source_entry_id,created_at,confirmed_at,merchant,amount,currency,paid_at,category,payment_method,note,tags)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (entry_id, cid, item["source_entry_id"], item["created_at"], confirmed_at,
                   item.get("merchant"), item.get("amount"), item.get("currency") or "CNY",
                   item.get("paid_at"), item.get("category"), item.get("payment_method"), item.get("note"), tags_json))
        c.execute("UPDATE ledger_candidates SET status='confirmed' WHERE id=?", (cid,))
        row = c.execute("SELECT * FROM ledger_entries WHERE id=?", (entry_id,)).fetchone()
    return {"ok": True, "entry": simple_row(row)}

def _filter_ledger_entries_sql(category: Optional[str], q: Optional[str], from_date: Optional[str], to_date: Optional[str]):
    sql = "SELECT * FROM ledger_entries WHERE 1=1"
    args = []
    if category:
        sql += " AND lower(coalesce(category,''))=lower(?)"
        args.append(normalize_ledger_category(category))
    if q:
        like = f"%{q.lower()}%"
        sql += " AND (lower(coalesce(merchant,'')) LIKE ? OR lower(coalesce(note,'')) LIKE ? OR lower(coalesce(payment_method,'')) LIKE ?)"
        args += [like, like, like]
    if from_date:
        sql += " AND substr(coalesce(paid_at,''),1,10) >= ?"
        args.append(from_date)
    if to_date:
        sql += " AND substr(coalesce(paid_at,''),1,10) <= ?"
        args.append(to_date)
    return sql, args

@app.get("/api/ledger/entries")
def list_ledger_entries(limit: int = 200,
                        category: Optional[str] = None,
                        q: Optional[str] = None,
                        from_date: Optional[str] = Query(None, alias="from"),
                        to_date: Optional[str] = Query(None, alias="to")):
    sql, args = _filter_ledger_entries_sql(category, q, from_date, to_date)
    sql += " ORDER BY coalesce(paid_at, '') DESC, confirmed_at DESC LIMIT ?"
    args.append(limit)
    with db() as c:
        rows = [simple_row(r) for r in c.execute(sql, args)]
    return {"entries": rows, "total": len(rows)}

@app.delete("/api/ledger/entries/{lid}")
def delete_ledger_entry(lid: str):
    with db() as c:
        row = c.execute("SELECT id FROM ledger_entries WHERE id=?", (lid,)).fetchone()
        if not row: raise HTTPException(404)
        c.execute("DELETE FROM ledger_entries WHERE id=?", (lid,))
    return {"ok": True, "id": lid}

@app.get("/api/ledger/stats")
def ledger_stats(window: str = "month"):
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    today = now.date()
    if window == "today":
        start_date = today
    elif window == "week":
        start_date = today - dt.timedelta(days=today.weekday())
    elif window == "month":
        start_date = today.replace(day=1)
    elif window == "year":
        start_date = today.replace(month=1, day=1)
    else:
        start_date = None
    with db() as c:
        rows = [simple_row(r) for r in c.execute("SELECT * FROM ledger_entries ORDER BY confirmed_at DESC")]
    def entry_date(e):
        s = (e.get("paid_at") or "").strip()
        if s:
            d = _parse_iso(s)
            if d: return d.astimezone(dt.timezone(dt.timedelta(hours=8))).date()
            try: return dt.date.fromisoformat(s[:10])
            except Exception: pass
        return dt.date.fromtimestamp((e.get("created_at") or e.get("confirmed_at") or now_ts()) + 8*3600)
    scoped = []
    for e in rows:
        d = entry_date(e)
        if start_date and d < start_date:
            continue
        amt = float(e.get("amount") or 0)
        if (e.get("category") or "").lower() == "transfer":
            continue
        scoped.append((d, amt, e))
    total = round(sum(x[1] for x in scoped), 2)
    by_cat = {}
    for _, amt, e in scoped:
        cat = (e.get("category") or "other").lower()
        cat = normalize_ledger_category(cat)
        by_cat[cat] = by_cat.get(cat, 0) + amt
    return {
        "window": window,
        "total_count": len(scoped),
        "total_amount": total,
        "avg": round(total / len(scoped), 2) if scoped else 0,
        "by_category": [
            {
                "category": k,
                "label": LEDGER_CATEGORIES.get(k, "其他"),
                "amount": round(v, 2),
                "percent": round((v / total * 100), 1) if total else 0,
            }
            for k, v in sorted(by_cat.items(), key=lambda x: -x[1])
        ],
    }

@app.get("/api/ledger/export.csv")
def export_ledger_csv():
    import csv, io
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf)
    w.writerow(["paid_at", "merchant", "amount", "currency", "category", "payment_method", "tags", "note", "confirmed_at"])
    with db() as c:
        for r in c.execute("SELECT * FROM ledger_entries ORDER BY coalesce(paid_at,'') DESC, confirmed_at DESC"):
            d = simple_row(r) or {}
            tags = d.get("tags") or []
            w.writerow([d.get("paid_at") or "", d.get("merchant") or "", d.get("amount") or "", d.get("currency") or "",
                        d.get("category") or "", d.get("payment_method") or "", ",".join(tags), d.get("note") or "", d.get("confirmed_at") or ""])
    filename = f"whysper-ledger-{dt.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(content=buf.getvalue().encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

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

def _ics_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def _ics_dt(iso: str) -> str:
    """Convert ISO 8601 with offset to ICS UTC stamp YYYYMMDDTHHMMSSZ."""
    try:
        d = dt.datetime.fromisoformat(iso)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
        d = d.astimezone(dt.timezone.utc)
        return d.strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        return ""

@app.get("/api/entries/{eid}/event")
def entry_event(eid: str):
    """返回给快捷指令设计的扁平事件结构。取第一个 calendar item。"""
    with db() as c:
        r = c.execute("SELECT * FROM entries WHERE id=?", (eid,)).fetchone()
    if not r: raise HTTPException(404)
    e = row_to_dict(r)
    items = e.get("calendar_items") or []
    if not items:
        return {"has_event": False, "entry_id": eid, "processing_status": e.get("processing_status", ""), "processing_stage": e.get("processing_stage", "")}
    ev = items[0]
    def _fmt(iso):
        try:
            d = dt.datetime.fromisoformat(iso.replace("Z","+00:00"))
            if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
            d = d.astimezone(dt.timezone(dt.timedelta(hours=8)))
            return d.strftime("%Y-%m-%d %H:%M")
        except Exception: return ""
    return {
        "has_event": True,
        "entry_id": eid,
        "type": ev.get("type") or "event",
        "title": ev.get("title") or e.get("title") or "Whysper 事件",
        "start": _fmt(ev.get("start_iso") or ""),
        "end": _fmt(ev.get("end_iso") or ""),
        "start_iso": ev.get("start_iso") or "",
        "end_iso": ev.get("end_iso") or "",
        "location": ev.get("location") or "",
        "notes": ev.get("notes") or e.get("summary") or "",
        "event_count": len(items),
        "processing_status": e.get("processing_status", ""),
        "processing_stage": e.get("processing_stage", ""),
    }

@app.get("/api/entries/{eid}/calendar-items")
def entry_calendar_items(eid: str):
    with db() as c:
        r = c.execute("SELECT * FROM entries WHERE id=?", (eid,)).fetchone()
    if not r: raise HTTPException(404)
    e = row_to_dict(r)
    return {
        "entry_id": eid,
        "has_items": bool(e.get("calendar_items")),
        "items": e.get("calendar_items") or [],
        "processing_status": e.get("processing_status", ""),
        "processing_stage": e.get("processing_stage", ""),
        "processing_error": e.get("processing_error") or "",
    }

@app.get("/api/entries/{eid}/ics")
def entry_ics(eid: str):
    with db() as c:
        r = c.execute("SELECT * FROM entries WHERE id=?", (eid,)).fetchone()
    if not r: raise HTTPException(404)
    e = row_to_dict(r)
    events = e.get("calendar_items") or []
    if not events: raise HTTPException(404, "no calendar items on this entry")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Whysper//Whysper//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for i, ev in enumerate(events):
        dtstart = _ics_dt(ev.get("start_iso") or "")
        if not dtstart: continue
        dtend = _ics_dt(ev.get("end_iso") or "") or dtstart
        uid = f"{eid}-{i}@whysper"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{_ics_escape(ev.get('title') or e.get('title') or 'Whysper')}",
        ]
        if ev.get("location"):
            lines.append(f"LOCATION:{_ics_escape(ev['location'])}")
        if ev.get("notes"):
            lines.append(f"DESCRIPTION:{_ics_escape(ev['notes'])}")
        alert_min = ev.get("alert_min")
        if alert_min is None: alert_min = 30
        try: alert_min = int(alert_min)
        except Exception: alert_min = 30
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_escape(ev.get('title') or 'Whysper')}",
            f"TRIGGER:-PT{alert_min}M",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines) + "\r\n"
    return Response(content=body, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": f'inline; filename="whysper-{eid}.ics"'})

@app.get("/api/storage")
def storage_info():
    def dir_size_mb(p: Path) -> float:
        if not p.exists(): return 0.0
        total = 0
        for f in p.rglob("*"):
            if f.is_file():
                try: total += f.stat().st_size
                except Exception: pass
        return round(total / (1024*1024), 2)
    audio_mb = dir_size_mb(DATA_ROOT/"audio")
    images_mb = dir_size_mb(DATA_ROOT/"images")
    db_mb = round(DB_PATH.stat().st_size / (1024*1024), 2) if DB_PATH.exists() else 0.0
    total_mb = round(audio_mb + images_mb + db_mb, 2)
    limit_mb = int(os.environ.get("WHYSPER_DISK_LIMIT_MB", "10240"))  # shared with disk-quota cron (10G)
    pct = round(total_mb / limit_mb * 100, 1) if limit_mb else 0
    # rough vlog co-tenant usage (best effort)
    vlog_path = Path("/var/vlog-data")
    vlog_mb = dir_size_mb(vlog_path)
    return {
        "audio_mb": audio_mb, "images_mb": images_mb, "db_mb": db_mb,
        "total_mb": total_mb, "limit_mb": limit_mb, "pct": pct,
        "vlog_mb": vlog_mb,
        "note": "limit shared across whysper+vlog by /usr/local/bin/whysper-disk-quota.sh"
    }

@app.get("/api/health")
def health():
    return {"ok": True, "ts": now_ts(), "data": str(DATA_ROOT)}

@app.get("/api/boot")
def boot(tab: str = "rec", date: Optional[str] = None, year: Optional[int] = None, month: Optional[int] = None):
    """One-shot bootstrap: stats + the current tab's needed data. Saves N RTTs vs separate calls."""
    out = {"stats": stats(), "tags": list_tags(), "shortcut_url": None}
    if tab == "list":
        out["entries"] = list_entries(date=None, tag=None, q=None, limit=200, offset=0)
    elif tab == "cal":
        d = date or today_local()
        try:
            y = int(year) if year else dt.date.fromisoformat(d).year
            m = int(month) if month else dt.date.fromisoformat(d).month
        except Exception:
            y, m = dt.date.fromisoformat(today_local()).year, dt.date.fromisoformat(today_local()).month
        out["calendar"] = calendar(year=y, month=m)
        out["storage"] = storage_info()
        out["day_summary"] = day_summary(d)
    elif tab == "ledger":
        out["ledger_candidates"] = list_ledger_candidates(status="pending", limit=100)
        out["ledger_entries"] = list_ledger_entries(limit=200, category=None, q=None, from_date=None, to_date=None)
        out["ledger_stats"] = ledger_stats(window="month")
    return out
