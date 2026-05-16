"""vlog backend v0.4 — cinematic captions, 9:16, beat-synced, AI-picked, dedup, quota."""
import os, uuid, json, subprocess, random, time, base64, shutil, math, re
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles, asyncio
import urllib.request

GATEWAY_URL = os.environ.get("VLOG_GATEWAY_URL", "https://new-api.openclaw.ingarena.net")
GATEWAY_KEY = os.environ.get("VLOG_GATEWAY_KEY", "")
MODEL_VISION = "claude-sonnet-4-6"  # gateway only exposes 4-6 for sonnet vision
FONT_PATH = "/usr/share/fonts/truetype/anton/Anton-Regular.ttf"

# ---- Quota ----
QUOTA_BYTES = 15 * 1024 * 1024 * 1024  # 15 GB
WARN_PCT, REJECT_PCT = 0.80, 0.95

ROOT = Path("/var/vlog-data")
UPLOADS = ROOT / "uploads"
REFS = ROOT / "refs"
OUTPUTS = ROOT / "outputs"
BGM = ROOT / "bgm"
JOBS = ROOT / "jobs"
for p in (UPLOADS, REFS, OUTPUTS, BGM, JOBS):
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="vlog-mvp")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
USER_ID = "you"


def user_dir(base: Path) -> Path:
    p = base / USER_ID
    p.mkdir(parents=True, exist_ok=True)
    return p


def dir_size(path: Path) -> int:
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            try: total += f.stat().st_size
            except: pass
    return total


def total_used() -> int:
    return sum(dir_size(p) for p in (UPLOADS, REFS, OUTPUTS, JOBS))


def auto_cleanup_old():
    """#4 outputs >30d delete; #5 uploads >7d after job done, delete assets keep output."""
    now = time.time()
    cutoff_out = now - 30 * 86400
    cutoff_assets = now - 7 * 86400
    for f in OUTPUTS.glob("*.mp4"):
        try:
            if f.stat().st_mtime < cutoff_out: f.unlink()
        except: pass
    # Walk jobs: if done >7d, remove their upload assets (keep output)
    for jf in JOBS.glob("*.json"):
        try:
            j = json.loads(jf.read_text())
            if j.get("status") == "done" and j.get("created_at", now) < cutoff_assets:
                for aid in j.get("asset_ids", []):
                    for f in user_dir(UPLOADS).glob(f"{aid}*"):
                        try: f.unlink()
                        except: pass
        except: pass


@app.get("/api/health")
async def health(): return {"ok": True, "ts": int(time.time())}


@app.get("/api/quota")
async def quota():
    used = total_used()
    return {"used": used, "limit": QUOTA_BYTES,
            "pct": round(used / QUOTA_BYTES * 100, 1),
            "warn": used / QUOTA_BYTES > WARN_PCT,
            "reject": used / QUOTA_BYTES > REJECT_PCT}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    used = total_used()
    if used / QUOTA_BYTES > REJECT_PCT:
        raise HTTPException(507, f"vlog 配额已满 ({used/QUOTA_BYTES*100:.0f}%)，先去历史清理")
    aid = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix.lower() or ".bin"
    dest = user_dir(UPLOADS) / f"{aid}{ext}"
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            await f.write(chunk)
    kind = "video" if ext in (".mp4", ".mov", ".m4v", ".webm") else "image"
    thumb = user_dir(UPLOADS) / f"{aid}_thumb.jpg"
    try:
        if kind == "video":
            subprocess.run(["ffmpeg", "-y", "-ss", "0.5", "-i", str(dest), "-vframes", "1",
                "-vf", "scale=240:-1", str(thumb)], check=True, capture_output=True, timeout=30)
        else:
            subprocess.run(["ffmpeg", "-y", "-i", str(dest), "-vf", "scale=240:-1",
                str(thumb)], check=True, capture_output=True, timeout=30)
    except: pass
    return {"id": aid, "kind": kind, "size": dest.stat().st_size, "filename": file.filename,
            "thumb_url": f"/api/asset/{aid}/thumb" if thumb.exists() else None}


@app.get("/api/asset/{aid}/thumb")
async def asset_thumb(aid: str):
    f = user_dir(UPLOADS) / f"{aid}_thumb.jpg"
    if not f.exists(): raise HTTPException(404)
    return FileResponse(f, media_type="image/jpeg")


@app.post("/api/refs/upload")
async def upload_ref(file: UploadFile = File(...), name: Optional[str] = Form(None)):
    rid = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix.lower() or ".mp4"
    dest = user_dir(REFS) / f"{rid}{ext}"
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            await f.write(chunk)
    meta = {"id": rid, "name": name or file.filename, "path": str(dest),
            "uploaded_at": int(time.time())}
    (user_dir(REFS) / f"{rid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    try:
        bgm_out = BGM / f"ref-{rid}.mp3"
        subprocess.run(["ffmpeg", "-y", "-i", str(dest), "-vn", "-acodec", "libmp3lame",
                       "-b:a", "192k", str(bgm_out)], check=True, capture_output=True, timeout=60)
    except: pass
    return meta


@app.get("/api/refs")
async def list_refs():
    out = []
    for jf in sorted(user_dir(REFS).glob("*.json")):
        try: out.append(json.loads(jf.read_text()))
        except: pass
    return out


# ---- Jobs management ----
@app.get("/api/jobs")
async def list_jobs():
    out = []
    for jf in sorted(JOBS.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            j = json.loads(jf.read_text())
            # Compute total size for this job (assets + output)
            out_size = 0
            if j.get("output") and Path(j["output"]).exists():
                out_size += Path(j["output"]).stat().st_size
            asset_size = 0
            for aid in j.get("asset_ids", []):
                for f in user_dir(UPLOADS).glob(f"{aid}*"):
                    asset_size += f.stat().st_size
            j["output_size"] = out_size
            j["asset_size"] = asset_size
            j["has_output"] = bool(j.get("output") and Path(j.get("output","")).exists())
            out.append({k: j[k] for k in ("id","status","prompt","progress","created_at",
                "output_size","asset_size","has_output","duration") if k in j})
        except: pass
    return out


@app.delete("/api/jobs/{jid}")
async def delete_job(jid: str, keep_assets: bool = False):
    jf = JOBS / f"{jid}.json"
    if not jf.exists(): raise HTTPException(404)
    job = json.loads(jf.read_text())
    # Delete output
    if job.get("output"):
        p = Path(job["output"])
        if p.exists(): p.unlink()
    # Delete assets
    if not keep_assets:
        for aid in job.get("asset_ids", []):
            for f in user_dir(UPLOADS).glob(f"{aid}*"):
                try: f.unlink()
                except: pass
    jf.unlink()
    return {"ok": True}


@app.post("/api/jobs/batch_delete")
async def batch_delete(payload: dict):
    ids = payload.get("ids", [])
    keep_assets = payload.get("keep_assets", False)
    n = 0
    for jid in ids:
        try:
            await delete_job(jid, keep_assets)
            n += 1
        except: pass
    return {"deleted": n}


@app.post("/api/jobs")
async def create_job(prompt: str = Form(""), asset_ids: str = Form(""),
                     ref_id: Optional[str] = Form(None),
                     title: Optional[str] = Form(None)):
    used = total_used()
    if used / QUOTA_BYTES > REJECT_PCT:
        raise HTTPException(507, "配额已满")
    jid = uuid.uuid4().hex[:12]
    aids = [a.strip() for a in asset_ids.split(",") if a.strip()]
    job = {"id": jid, "status": "queued", "prompt": prompt, "asset_ids": aids,
           "ref_id": ref_id, "title": title or "",
           "created_at": int(time.time()), "progress": 0, "logs": []}
    (JOBS / f"{jid}.json").write_text(json.dumps(job, ensure_ascii=False, indent=2))
    asyncio.create_task(run_job(jid))
    return job


def probe_dur(path: Path) -> float:
    try:
        return float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(path)], text=True).strip())
    except: return 0.0


def extract_thumb(video: Path, t: float, out: Path) -> bool:
    try:
        subprocess.run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(video),
            "-vframes", "1", "-vf", "scale=480:-1", str(out)],
            check=True, capture_output=True, timeout=30)
        return True
    except: return False


def call_claude_vision(prompt: str, image_paths: List[Path], max_tokens: int = 2000) -> str:
    if not GATEWAY_KEY: return ""
    content = [{"type": "text", "text": prompt}]
    for p in image_paths:
        try:
            b64 = base64.b64encode(p.read_bytes()).decode()
            content.append({"type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        except: continue
    body = json.dumps({"model": MODEL_VISION,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens, "temperature": 0.3}).encode()
    req = urllib.request.Request(f"{GATEWAY_URL}/v1/chat/completions",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {GATEWAY_KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"vision err: {e}")
        return ""


def detect_beats(bgm_path: Path):
    """Returns (tempo_float, beat_times_list, total_duration)."""
    try:
        import librosa
        import numpy as np
        y, sr = librosa.load(str(bgm_path), sr=22050, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        # tempo may be ndarray of shape (1,) — coerce to float
        if hasattr(tempo, "item"): t = float(tempo.item() if tempo.ndim == 0 else tempo[0])
        elif hasattr(tempo, "__iter__"): t = float(list(tempo)[0])
        else: t = float(tempo)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        beat_times = beat_times.tolist() if hasattr(beat_times, "tolist") else list(beat_times)
        dur = float(librosa.get_duration(y=y, sr=sr))
        return t, beat_times, dur
    except Exception as e:
        print(f"beat err: {e}")
        return 120.0, [], 60.0


def build_beat_schedule(beat_times, total_dur):
    """intro 2-beat × 2, main 1-beat, chorus 0.5-beat, outro 2-beat."""
    if len(beat_times) < 8:
        n = max(8, int(total_dur / 1.2))
        return [(i * 1.2, 1.2) for i in range(n) if (i+1)*1.2 < total_dur]
    schedule = []
    bt = beat_times
    n_beats = len(bt)
    intro_end = int(n_beats * 0.15)
    main_end = int(n_beats * 0.50)
    chorus_end = int(n_beats * 0.85)
    i = 0
    while i < intro_end - 1:
        start = bt[i]; nxt = bt[min(i+2, n_beats-1)]
        schedule.append((start, nxt - start)); i += 2
    while i < main_end - 1:
        start = bt[i]; nxt = bt[min(i+1, n_beats-1)]
        schedule.append((start, nxt - start)); i += 1
    while i < chorus_end - 1:
        a = bt[i]; b = bt[min(i+1, n_beats-1)]
        mid = (a + b) / 2
        schedule.append((a, mid - a))
        schedule.append((mid, b - mid)); i += 1
    while i < n_beats - 1:
        start = bt[i]; nxt = bt[min(i+2, n_beats-1)]
        schedule.append((start, nxt - start)); i += 2
    schedule = [(t, d) for (t, d) in schedule if 0.25 <= d <= 4.0 and t < total_dur]
    return schedule[:80]


def phash_dedup(samples, threshold=4):
    """Remove visually similar frames using imagehash."""
    try:
        import imagehash
        from PIL import Image
        kept = []
        for s in samples:
            try:
                h = imagehash.phash(Image.open(s["thumb"]))
                dup = False
                for k in kept:
                    if h - k["hash"] < threshold:
                        dup = True; break
                if not dup:
                    s["hash"] = h
                    kept.append(s)
            except:
                kept.append(s)
        return kept
    except Exception as e:
        print(f"dedup err: {e}")
        return samples


def build_contact_sheet(video: Path, out: Path, n_frames: int = 8, tile: str = "4x2") -> bool:
    """Generate a contact sheet showing N frames in a grid - so AI sees motion progression."""
    dur = probe_dur(video)
    if dur < 0.5:
        return False
    try:
        # Sample every dur/n_frames seconds, scale to 240x426 each, tile into grid
        fps = n_frames / dur
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video),
            "-vf", f"fps={fps:.4f},scale=240:-1,tile={tile}",
            "-frames:v", "1", "-qscale:v", "3", str(out)
        ], check=True, capture_output=True, timeout=60)
        return out.exists()
    except Exception:
        return False


def detect_motion_peaks(video: Path, dur: float) -> list:
    """Return timestamps of scene/motion changes via ffmpeg scene detection."""
    if dur < 1.5:
        return []
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", str(video), "-vf",
             "select='gt(scene,0.15)',showinfo", "-f", "null", "-"],
            capture_output=True, timeout=60, text=True
        )
        peaks = []
        for line in result.stderr.split("\n"):
            m = re.search(r'pts_time:([0-9.]+)', line)
            if m:
                t = float(m.group(1))
                if 0.3 < t < dur - 0.3:
                    peaks.append(t)
        peaks.sort()
        merged = []
        for p in peaks:
            if not merged or p - merged[-1] > 0.8:
                merged.append(p)
        return merged[:8]
    except Exception:
        return []


def ai_pick_clips(videos, images, prompt, n_target, log_fn):
    samples = []
    thumb_dir = OUTPUTS / "_thumbs"
    thumb_dir.mkdir(exist_ok=True)
    motion_by_video = {}
    sheet_paths = []  # contact sheet per video (for AI motion context)
    sheet_meta = []   # parallel list: (video_index, video_path, dur)
    for vi, v in enumerate(videos):
        dur = probe_dur(v)
        n_samples = min(10, max(3, int(dur / 1.2)))
        for k in range(n_samples):
            ts = dur * (k + 0.5) / n_samples
            tp = thumb_dir / f"{uuid.uuid4().hex[:8]}.jpg"
            if extract_thumb(v, ts, tp):
                samples.append({"src": v, "type": "video", "ts": ts, "thumb": tp, "dur": dur,
                                "video_idx": vi})
        motion_by_video[str(v)] = detect_motion_peaks(v, dur)
        # Build contact sheet so AI can see motion across the whole clip
        sheet = thumb_dir / f"sheet_{vi}_{uuid.uuid4().hex[:6]}.jpg"
        if build_contact_sheet(v, sheet, n_frames=8, tile="4x2"):
            sheet_paths.append(sheet)
            sheet_meta.append((vi, v, dur))
    for img in images:
        tp = thumb_dir / f"{uuid.uuid4().hex[:8]}.jpg"
        try:
            subprocess.run(["ffmpeg", "-y", "-i", str(img), "-vf", "scale=480:-1", str(tp)],
                check=True, capture_output=True, timeout=30)
            samples.append({"src": img, "type": "image", "ts": 0, "thumb": tp, "dur": 0})
        except: pass

    if not samples:
        return []
    log_fn(f"抽取 {len(samples)} 帧候选", 25)

    # Perceptual dedup
    before = len(samples)
    samples = phash_dedup(samples)
    log_fn(f"去重后 {len(samples)} 帧 (-{before - len(samples)} 重复)", 28)
    samples = samples[:30]

    # ===== STAGE 1: Highlight detection per video via contact sheets =====
    # Each contact sheet shows 8 frames of a video in 4x2 grid (left-to-right, top-to-bottom)
    # AI identifies WHICH cell range is the highlight (zoom, action, gesture, etc.)
    highlights = {}  # video_idx -> {start_t, end_t, score, desc}
    if sheet_paths:
        sheet_list_str = "\n".join(
            f"贴图 #{si}: 视频 {Path(v).stem[:8]}, 总时长 {dur:.1f}s, 8 帧从左上到右下在 0%/12.5%/25%/37.5%/50%/62.5%/75%/87.5% 时间点抽取"
            for si, (vi, v, dur) in enumerate(sheet_meta)
        )
        stage1_prompt = f"""你是 vlog 剪辑师。我给你 {len(sheet_paths)} 张贴图，每张是一个视频的 8 帧抽取拼接（4x2 网格）。

{sheet_list_str}

任务：看每张贴图的动作进展（从左到右、从上到下），找出每个视频的【精髓时间段】——
- zoom、镜头推进/拉远、人物动作、主体出现、表情变化、全景揭示都是精髓
- 静止/重复/模糊/平平无奇的不算

返回 JSON，为每张贴图给出起止时间和评分：
{{"highlights":[{{"sheet":0,"start_t":1.5,"end_t":4.5,"score":3,"desc":"人拿票后 zoom 到雕刻"}}, ...]}}

score: 3=绝佳精髓, 2=不错, 1=一般, 0=无亮点
start_t/end_t 是该视频中的秒数，范围 0 ~ 总时长。间隔 1-4 秒。
只返 JSON，无任何额外字符。"""
        try:
            resp1 = call_claude_vision(stage1_prompt, sheet_paths, max_tokens=1500)
            log_fn(f"Stage1 raw: {resp1[:120]}", 30)
            m = re.search(r'\{.*"highlights".*\}', resp1, re.DOTALL)
            j1 = json.loads(m.group(0) if m else resp1.strip().lstrip('```json').rstrip('```'))
            for h in j1.get("highlights", []):
                si = int(h["sheet"])
                if 0 <= si < len(sheet_meta):
                    vi, vpath, vdur = sheet_meta[si]
                    highlights[vi] = {
                        "start_t": max(0, float(h.get("start_t", 0))),
                        "end_t": min(vdur, float(h.get("end_t", vdur))),
                        "score": int(h.get("score", 1)),
                        "desc": str(h.get("desc", ""))[:60],
                    }
            log_fn(f"Stage1 识别精髓: {len(highlights)} 个视频", 32)
        except Exception as e:
            log_fn(f"Stage1 解析失败 (采用 motion peak fallback): {e}", 32)

    # ===== STAGE 2: Order picks across videos with weights =====
    # Build sample list emphasizing highlight frames
    motion_hints = []
    for vi, v in enumerate(videos):
        peaks = motion_by_video.get(str(v), [])
        h = highlights.get(vi)
        bits = []
        if h:
            bits.append(f"精髓 {h['start_t']:.1f}-{h['end_t']:.1f}s (score={h['score']}, {h['desc']})")
        if peaks:
            bits.append(f"动作峰值 {', '.join(f'{p:.1f}s' for p in peaks[:4])}")
        if bits:
            motion_hints.append(f"视频 {Path(v).stem[:6]}: " + "; ".join(bits))
    motion_text = "\n".join(motion_hints) if motion_hints else "(无)"

    frame_info = []
    for i, s in enumerate(samples):
        src_short = Path(s["src"]).stem[:6]
        if s["type"] == "image":
            frame_info.append(f"#{i}: 图片 ({src_short})")
        else:
            # Mark frames inside highlight window
            vi = s.get("video_idx", -1)
            h = highlights.get(vi)
            tag = ""
            if h and h["start_t"] <= s["ts"] <= h["end_t"]:
                tag = f" [精髓 score={h['score']}]"
            frame_info.append(f"#{i}: 视频 {src_short} @ {s['ts']:.1f}s{tag}")
    frame_index_str = "\n".join(frame_info)

    user_prompt = f"""你是电影感旅行 vlog 剪辑师。我有 {len(samples)} 个候选帧。

风格: 9:16 竖屏短片，电影感，有叙事节奏的卡点剪辑。
用户描述: {prompt or "(无)"}

帧列表（带源视频、时间戳、精髓标记）:
{frame_index_str}

每个源视频的精髓范围（AI 看贴图后识别出的）:
{motion_text}

挑 {n_target} 个最值得用的，按叙事节奏排:
1. 开头 1-2 个: 地标/全景/天空
2. 中段大量混切: 人物/街景/特写/动作
3. 结尾 1-2 个: 标志性建筑/静帧

⚠️ 重点要求：
- 带【精髓 score=3 或 2】标记的帧必须优先选（这是原素材亮点）
- 给这些精髓帧 weight=2.0，让它们多放几秒舌头戏足
- 空镜/过渡 weight=0.5，一闪而过
- 严禁重复/近似镜头
- 拒绝模糊/黑屏

weights:
- 2.0 = 精髓亮点（score=2/3 的帧）
- 1.0 = 普通镜头
- 0.5 = 空镜/过渡

⚠️ 严格按此 JSON 返回，无额外字符:
{{"picks":[0,5,2,8],"weights":[2.0,1.0,0.5,2.0],"reason":"中文一句话"}}"""

    images_for_api = [s["thumb"] for s in samples]
    resp = call_claude_vision(user_prompt, images_for_api, max_tokens=1500)
    log_fn(f"AI raw: {resp[:120]}", 35)

    def parse_resp(text):
        s = text.strip()
        # try to find JSON object
        m = re.search(r'\{[^{}]*"picks"[^{}]*\}', s, re.DOTALL)
        if m: s = m.group(0)
        if s.startswith("```"):
            s = re.sub(r'^```(?:json)?\s*', '', s)
            s = re.sub(r'\s*```$', '', s)
        return json.loads(s)

    picks_data = None  # list of (idx, weight)
    try:
        j = parse_resp(resp)
        ps = [int(x) for x in j.get("picks", []) if 0 <= int(x) < len(samples)]
        ws = j.get("weights", [1.0]*len(ps))
        ws = [float(w) for w in ws[:len(ps)]] + [1.0]*max(0,len(ps)-len(ws))
        picks_data = list(zip(ps, ws))
        log_fn(f"AI: {j.get('reason','')[:60]}", 40)
    except Exception as e:
        log_fn(f"AI 解析失败,重试: {e}", 38)
        retry_prompt = user_prompt + "\n\n上次你没返回有效 JSON。这次只输出 JSON 一行,无其他字符。必须包含 picks 和 weights 两个数组。"
        resp2 = call_claude_vision(retry_prompt, images_for_api, max_tokens=800)
        log_fn(f"AI retry: {resp2[:120]}", 40)
        try:
            j = parse_resp(resp2)
            ps = [int(x) for x in j.get("picks", []) if 0 <= int(x) < len(samples)]
            ws = j.get("weights", [1.0]*len(ps))
            ws = [float(w) for w in ws[:len(ps)]] + [1.0]*max(0,len(ps)-len(ws))
            picks_data = list(zip(ps, ws))
            log_fn(f"AI(重试): {j.get('reason','')[:60]}", 42)
        except: pass

    if not picks_data:
        # Fallback: alternate from different sources
        by_src = {}
        for i, s in enumerate(samples):
            by_src.setdefault(str(s["src"]), []).append(i)
        ps = []
        srcs = list(by_src.values())
        idx = 0
        while len(ps) < min(n_target, len(samples)):
            for s in srcs:
                if idx < len(s): ps.append(s[idx])
                if len(ps) >= n_target: break
            idx += 1
            if idx > 20: break
        picks_data = [(p, 1.0) for p in ps]
        log_fn(f"用兜底分散选片: {len(picks_data)} 个", 44)

    # Dedup: same source within ±2s window only keeps first; same source max 2 picks total
    seen = []
    src_count = {}
    deduped = []
    for p, w in picks_data:
        s = samples[p]
        src_key = str(s["src"])
        ts = s["ts"]
        # skip if same src and within 2.5s of any kept pick
        skip = False
        for ks, kts in seen:
            if ks == src_key and abs(kts - ts) < 2.5:
                skip = True; break
        if skip: continue
        if src_count.get(src_key, 0) >= 2: continue
        deduped.append((p, w))
        seen.append((src_key, ts))
        src_count[src_key] = src_count.get(src_key, 0) + 1
    log_fn(f"去重后 {len(deduped)} 段 (删 {len(picks_data)-len(deduped)} 个重复)", 46)
    picks_data = deduped

    # Pad to n_target with cycling weights
    while len(picks_data) < n_target:
        picks_data.append(picks_data[len(picks_data) % max(1, len(picks_data))])
    picks_data = picks_data[:n_target]

    # Snap pick timestamps to nearest highlight center or motion peak.
    # If the frame is in a highlight window, snap to highlight midpoint (the action).
    # Else snap to nearest motion peak.
    snapped_count = 0
    result = []
    for (p, w) in picks_data:
        s = samples[p]
        ts = s["ts"]
        if s["type"] == "video":
            vi = s.get("video_idx", -1)
            h = highlights.get(vi)
            new_ts = None
            if h and h["score"] >= 2:
                # snap to highlight center for high-score highlights
                hl_mid = (h["start_t"] + h["end_t"]) / 2
                if h["start_t"] <= ts <= h["end_t"] or abs(hl_mid - ts) < 3.0:
                    new_ts = hl_mid
            if new_ts is None:
                # fall back to motion peak
                peaks = motion_by_video.get(str(s["src"]), [])
                best = None
                best_d = 1.5
                for pk in peaks:
                    d = abs(pk - ts)
                    if d < best_d:
                        best_d = d
                        best = pk
                if best is not None and best_d > 0.1:
                    new_ts = best
            if new_ts is not None and abs(new_ts - ts) > 0.1:
                ts = new_ts
                snapped_count += 1
        result.append((s["src"], s["type"], ts, s["dur"], w))
    if snapped_count:
        log_fn(f"对齐精髓/动作峰值: {snapped_count}/{len(picks_data)} 个 clip", 48)
    return result


def ffmpeg_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_title_ass(out_path, title, subtitle, deco, date_str, td=2.5, w=720, h=1280):
    """Build .ass file with 3D-perspective animated title (Y-axis rotation tilt)."""
    def ts(sec):
        ms = int(sec * 100) % 100
        s = int(sec) % 60
        m = int(sec / 60) % 60
        return f"0:{m:02d}:{s:02d}.{ms:02d}"
    end_t = td
    pop_in_end = 0.45
    hold_end = td - 0.55
    fade_out_dur = int(0.55 * 1000)
    # ASS template - use Anton font, white/orange, big sizes
    # \frx=tilt around X (top-back), \fry=tilt around Y (left-back), \frz=roll
    # We animate: start huge + tilted -> settle to perspective rest
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Anton,160,&H004DB8FF,&H000000FF,&H001A1A1A,&H00000000,0,0,0,0,100,100,0,0,1,5,0,5,0,0,0,1
Style: Sub,Anton,52,&H00FFFFFF,&H000000FF,&H001A1A1A,&H00000000,0,0,0,0,100,100,2,0,1,3,0,5,0,0,0,1
Style: Deco,Anton,36,&H004DB8FF,&H000000FF,&H001A1A1A,&H00000000,0,0,0,0,100,100,4,0,1,2,0,5,0,0,0,1
Style: Date,Anton,42,&H004DB8FF,&H000000FF,&H001A1A1A,&H00000000,0,0,0,0,100,100,2,0,1,2,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Decorative top: fades in early, fades out at end
    ass += (
        f"Dialogue: 0,{ts(0.15)},{ts(end_t)},Deco,,0,0,0,,"
        f"{{\\an5\\pos({w//2},{h//2-180})\\fad(250,500)}}{deco}\n"
    )
    # Main title - 3D perspective: tilt around Y (\fry) and slight X (\frx)
    # Animation: \t() interpolates over duration
    # Pop-in: scale 60->100, fry -25->-8 (settles into perspective)
    pop_ms = int(pop_in_end * 1000)
    out_ms = int((end_t - hold_end) * 1000)
    ass += (
        f"Dialogue: 1,{ts(0)},{ts(end_t)},Title,,0,0,0,,"
        f"{{\\an5\\pos({w//2},{h//2-30})\\fscx60\\fscy60\\fry-30\\frx10\\alpha&HFF&"
        f"\\t(0,{pop_ms},\\fscx115\\fscy115\\fry-8\\frx5\\alpha&H00&)"
        f"\\t({pop_ms},{pop_ms+200},\\fscx100\\fscy100)"
        f"\\t({int(hold_end*1000)},{int(end_t*1000)},\\fscx95\\fscy95\\fry-15\\frx10\\alpha&HFF&)}}"
        f"{title}\n"
    )
    # Subtitle
    ass += (
        f"Dialogue: 1,{ts(pop_in_end+0.1)},{ts(end_t)},Sub,,0,0,0,,"
        f"{{\\an5\\pos({w//2},{h//2+90})\\fad(300,500)\\fry-8\\frx5}}{subtitle}\n"
    )
    # Date
    ass += (
        f"Dialogue: 1,{ts(pop_in_end+0.3)},{ts(end_t)},Date,,0,0,0,,"
        f"{{\\an5\\pos({w//2},{h//2+155})\\fad(300,500)\\fry-8\\frx5}}{date_str}\n"
    )
    out_path.write_text(ass, encoding="utf-8")
    return out_path


def build_fin_ass(out_path, fin_text, start_t, end_t, w=720, h=1280):
    def ts(sec):
        ms = int(sec * 100) % 100
        s = int(sec) % 60
        m = int(sec / 60) % 60
        return f"0:{m:02d}:{s:02d}.{ms:02d}"
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Fin,Anton,180,&H004DB8FF,&H000000FF,&H001A1A1A,&H00000000,0,0,0,0,100,100,0,0,1,6,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # FIN: slide in from right + 3D tilt
    slide_ms = 500
    in_start_ms = int(start_t * 1000)
    in_end_ms = in_start_ms + slide_ms
    ass += (
        f"Dialogue: 1,{ts(start_t)},{ts(end_t)},Fin,,0,0,0,,"
        f"{{\\an5\\pos({w+200},{h//2})\\fscx80\\fscy80\\fry30\\frx-10\\alpha&HFF&"
        f"\\t(0,{slide_ms},\\pos({w//2},{h//2})\\fscx100\\fscy100\\fry-10\\frx5\\alpha&H00&)}}"
        f"{fin_text}\n"
    )
    out_path.write_text(ass, encoding="utf-8")
    return out_path


async def run_job(jid: str):
    jf = JOBS / f"{jid}.json"
    job = json.loads(jf.read_text())

    def log(msg, progress):
        job["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        job["progress"] = progress
        jf.write_text(json.dumps(job, ensure_ascii=False, indent=2))

    try:
        job["status"] = "running"
        log("开始任务", 5)

        # 1. BGM pick
        ref_bgm = None
        if job.get("ref_id"):
            cand = BGM / f"ref-{job['ref_id']}.mp3"
            if cand.exists(): ref_bgm = cand
        if not ref_bgm:
            # Prefer my_jealousy if available
            mj = BGM / "my_jealousy.mp3"
            if mj.exists():
                ref_bgm = mj
            else:
                bgm_pool = list(BGM.glob("*.mp3"))
                bgm_pool = [b for b in bgm_pool if probe_dur(b) > 10 and not b.name.startswith("ref-")]
                if not bgm_pool: raise RuntimeError("No BGM")
                ref_bgm = random.choice(bgm_pool)
        log(f"BGM: {ref_bgm.name}", 10)

        # 2. Beats
        loop = asyncio.get_event_loop()
        tempo, beats, bgm_dur = await loop.run_in_executor(None, detect_beats, ref_bgm)
        log(f"节拍: BPM={tempo:.1f}, {len(beats)} beats, {bgm_dur:.1f}s", 15)

        target_dur = min(bgm_dur, 28.0)
        beat_schedule = build_beat_schedule(beats, target_dur)
        # Sum total beat durations
        total_beat = sum(d for _,d in beat_schedule)
        log(f"节拍点 {len(beat_schedule)} 个,总长 {total_beat:.1f}s", 18)

        # 3. Assets
        assets_dir = user_dir(UPLOADS)
        candidates = []
        for aid in job["asset_ids"]:
            for f in assets_dir.glob(f"{aid}.*"):
                if "_thumb" not in f.name: candidates.append(f)
        videos = [c for c in candidates if c.suffix.lower() in (".mp4",".mov",".m4v",".webm")]
        images = [c for c in candidates if c not in videos]
        if not candidates: raise RuntimeError("No assets")

        # 4. AI picks WITH weights
        # Fewer, longer clips so重头戏 can really breathe (1-2s each)
        n_target = max(7, min(10, int(total_beat / 1.2)))
        picks = await loop.run_in_executor(None, ai_pick_clips,
                                           videos, images, job["prompt"], n_target, log)
        if not picks: raise RuntimeError("AI 未挑出片段")

        # 5. Allocate beat durations to picks BY WEIGHT
        # total beat duration to distribute over picks
        weights = [p[4] for p in picks]
        w_sum = sum(weights) or len(picks)
        # Each clip gets duration proportional to its weight (with min/max bounds)
        clip_durs = []
        for w in weights:
            d = (w / w_sum) * total_beat
            d = max(0.7, min(3.5, d))  # bounds - allow highlights up to 3.5s
            clip_durs.append(d)
        # Renormalize to fit target
        cur_sum = sum(clip_durs)
        scale = total_beat / cur_sum if cur_sum > 0 else 1
        clip_durs = [d * scale for d in clip_durs]
        log(f"AI 权重分配: {len(picks)} 段,时长 [{min(clip_durs):.2f}, {max(clip_durs):.2f}]s", 50)
        # Snap each to nearest beat boundary for cut feel
        snapped = []
        cum = 0
        beat_pts = [0] + [sum(d for _,d in beat_schedule[:i+1]) for i in range(len(beat_schedule))]
        for d in clip_durs:
            target = cum + d
            # find nearest beat boundary
            best = min(beat_pts, key=lambda b: abs(b - target))
            seg = best - cum
            if seg < 0.3: seg = 0.4  # min
            snapped.append(seg)
            cum += seg
        clip_durs = snapped

        # AI weights drive duration. Highlight clips (w=2.0) get up to 3.5s.
        # But force first/last clips to be long enough for title/FIN overlays.
        MIN_FIRST = 2.8
        MIN_LAST = 2.3
        if clip_durs and clip_durs[0] < MIN_FIRST:
            need = MIN_FIRST - clip_durs[0]
            clip_durs[0] = MIN_FIRST
            mids = list(range(1, len(clip_durs)-1)) if len(clip_durs) > 2 else []
            if mids:
                per = need / len(mids)
                for j in mids: clip_durs[j] = max(0.6, clip_durs[j] - per)
        if len(clip_durs) > 1 and clip_durs[-1] < MIN_LAST:
            need = MIN_LAST - clip_durs[-1]
            clip_durs[-1] = MIN_LAST
            mids = list(range(1, len(clip_durs)-1))
            if mids:
                per = need / len(mids)
                for j in mids: clip_durs[j] = max(0.6, clip_durs[j] - per)
        weights_log = [f'{w:.1f}->{d:.1f}s' for w, d in zip(weights, clip_durs)]
        log(f"权重驱动时长: {weights_log}", 52)

        # P0: Bright clean look (was too dark/heavy)
        cine_vf = (
            "scale=720:1280:force_original_aspect_ratio=increase,"
            "crop=720:1280,setsar=1,"
            "eq=brightness=0.04:contrast=1.08:saturation=1.18,"
            "curves=r='0/0.04 0.5/0.55 1/1':b='0/0 0.5/0.48 1/0.97'"
        )

        # Title overlay vars
        title = job.get("title") or (job.get("prompt", "").strip().split()[:1] or ["VLOG"])[0]
        if re.search(r'[\u4e00-\u9fff]', title): display_title = title[:8]
        else: display_title = title.upper()[:12]
        date_str = time.strftime("%Y.%m")
        title_esc = ffmpeg_escape(display_title)
        date_esc = ffmpeg_escape(date_str)

        TITLE_DUR = 2.5  # how long title overlay lasts
        FIN_DUR = 2.0

        clip_dir = OUTPUTS / jid
        clip_dir.mkdir(parents=True, exist_ok=True)
        clips = []
        last_idx = len(picks) - 1
        # Pre-generate ASS files for title (clip 0) and FIN (last clip)
        title_ass = clip_dir / "title.ass"
        fin_ass = clip_dir / "fin.ass"
        for i, ((src, typ, ts, src_dur, _w), dur_beat) in enumerate(zip(picks, clip_durs)):
            out = clip_dir / f"c{i:03d}.mp4"
            extra_sub = None  # path to ass file to overlay
            if i == 0:
                td = min(TITLE_DUR, dur_beat)
                build_title_ass(title_ass, display_title, "TRAVEL DIARY",
                                "— EXPLORING —", date_str, td=td)
                extra_sub = title_ass
            if i == last_idx:
                fd = min(FIN_DUR, dur_beat)
                t0 = max(0, dur_beat - fd)
                build_fin_ass(fin_ass, "FIN", t0, dur_beat)
                extra_sub = fin_ass  # overrides title if both same clip

            # Build base vf with subtle Ken Burns + color
            # Key: scale up by 1.1x with aspect-preserving scale, then ANIMATED crop
            # for slow pan/zoom effect WITHOUT stretching. zoompan's interpolation
            # can introduce aliasing; this approach is cleaner.
            color_chain = (
                "eq=brightness=0.04:contrast=1.08:saturation=1.18,"
                "curves=r='0/0.04 0.5/0.55 1/1':b='0/0 0.5/0.48 1/0.97'"
            )
            if typ == "video":
                # Cover-fit to 9:16 then static (motion comes from source itself + slight zoom)
                # Scale up 8% then animate crop x slightly for parallax feel
                vf_base = (
                    f"scale=778:1382:force_original_aspect_ratio=increase,"
                    f"crop=720:1280:'(in_w-720)/2+sin(t*0.5)*15':'(in_h-1280)/2',"
                    f"setsar=1,"
                    + color_chain
                )
            else:
                # Image: stronger Ken Burns since image is static
                frames = max(2, int(dur_beat * 30))
                vf_base = (
                    "scale=864:1536:force_original_aspect_ratio=increase,"
                    f"zoompan=z='min(1.0+0.0015*on,1.15)':d={frames}:s=720x1280:fps=30,"
                    "setsar=1,"
                    + color_chain
                )

            # If first clip: add darken overlay during title hold
            if i == 0:
                vf_base += f",drawbox=x=0:y=0:w=iw:h=ih:color=black@0.25:t=fill:enable='lt(t\\,{td-0.3:.2f})'"
            if i == last_idx:
                fd = min(FIN_DUR, dur_beat)
                t0 = max(0, dur_beat - fd)
                vf_base += f",drawbox=x=0:y=0:w=iw:h=ih:color=black@0.30:t=fill:enable='gte(t\\,{t0+0.2:.2f})'"

            # Append subtitle filter if ASS file applies
            if extra_sub is not None:
                # subtitles filter needs the path with : escaped
                ass_path = str(extra_sub).replace(':', '\\:').replace("'", "\\'")
                vf_base += f",subtitles='{ass_path}':fontsdir='/usr/share/fonts/truetype/anton'"

            if typ == "video":
                start_t = max(0, min(max(0, src_dur - dur_beat - 0.05), ts - dur_beat/2))
                cmd = ["ffmpeg", "-y", "-ss", f"{start_t:.3f}", "-i", str(src),
                    "-t", f"{dur_beat:.3f}",
                    "-vf", vf_base,
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-an", str(out)]
            else:
                cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(src), "-t", f"{dur_beat:.3f}",
                    "-vf", vf_base,
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-an", "-pix_fmt", "yuv420p", str(out)]
            subprocess.run(cmd, check=True, capture_output=True)
            clips.append(out)
        log(f"渲染 {len(clips)} 段(ASS 3D 透视字幕)", 80)

        # 6. Concat (no separate intro/outro)
        concat_list = clip_dir / "concat.txt"
        concat_list.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
        merged = clip_dir / "merged.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(merged)], check=True, capture_output=True)
        log("拼接完成", 88)

        # 7. BGM mix
        final = OUTPUTS / f"{jid}.mp4"
        video_len = probe_dur(merged)
        subprocess.run(["ffmpeg", "-y", "-i", str(merged), "-i", str(ref_bgm),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-map", "0:v", "-map", "1:a", "-t", f"{video_len:.2f}",
            "-af", f"afade=t=in:st=0:d=0.5,afade=t=out:st={max(0, video_len-1.5):.2f}:d=1.5,volume=0.8",
            str(final)], check=True, capture_output=True)
        log("加 BGM", 96)

        # Cleanup
        for f in clip_dir.glob("*"):
            try: f.unlink()
            except: pass
        try: clip_dir.rmdir()
        except: pass

        # Auto cleanup old
        auto_cleanup_old()

        job["status"] = "done"; job["output"] = str(final); job["duration"] = probe_dur(final)
        log("完成 ✨", 100)
    except subprocess.CalledProcessError as e:
        job["status"] = "error"
        err = e.stderr.decode()[-600:] if e.stderr else str(e)
        job["error"] = f"ffmpeg: {err}"
        log(f"❌ {err[:250]}", job["progress"])
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"❌ {e}", job["progress"])
    finally:
        jf.write_text(json.dumps(job, ensure_ascii=False, indent=2))


@app.get("/api/jobs/{jid}")
async def get_job(jid: str):
    jf = JOBS / f"{jid}.json"
    if not jf.exists(): raise HTTPException(404)
    return json.loads(jf.read_text())


@app.get("/api/jobs/{jid}/result")
async def job_result(jid: str):
    f = OUTPUTS / f"{jid}.mp4"
    if not f.exists(): raise HTTPException(404)
    return FileResponse(f, media_type="video/mp4", filename=f"vlog_{jid}.mp4")


@app.get("/api/jobs/{jid}/thumb")
async def job_thumb(jid: str):
    """Output thumbnail."""
    out = OUTPUTS / f"{jid}.mp4"
    thumb = OUTPUTS / f"{jid}_thumb.jpg"
    if not thumb.exists() and out.exists():
        try:
            subprocess.run(["ffmpeg", "-y", "-ss", "2", "-i", str(out), "-vframes", "1",
                "-vf", "scale=240:-1", str(thumb)], check=True, capture_output=True, timeout=15)
        except: pass
    if not thumb.exists(): raise HTTPException(404)
    return FileResponse(thumb, media_type="image/jpeg")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
