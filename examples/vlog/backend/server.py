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


def ai_pick_clips(videos, images, prompt, n_target, log_fn):
    samples = []
    thumb_dir = OUTPUTS / "_thumbs"
    thumb_dir.mkdir(exist_ok=True)
    for v in videos:
        dur = probe_dur(v)
        n_samples = min(8, max(2, int(dur / 2)))
        for k in range(n_samples):
            ts = dur * (k + 0.5) / n_samples
            tp = thumb_dir / f"{uuid.uuid4().hex[:8]}.jpg"
            if extract_thumb(v, ts, tp):
                samples.append({"src": v, "type": "video", "ts": ts, "thumb": tp, "dur": dur})
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
    samples = samples[:25]

    user_prompt = f"""你是电影感旅行 vlog 剪辑师。我有 {len(samples)} 个候选帧,编号 0-{len(samples)-1}。

风格: 9:16 竖屏短片,电影感,有叙事节奏的卡点剪辑。
用户描述: {prompt or "(无)"}

挑 {n_target} 个最值得用的,按"叙事节奏"排:
1. 开头 2-3 个: 地标/全景/天空(建立场景)
2. 中段大量混切: 人物/街景/招牌/特写/细节(远近交错)
3. 结尾 2-3 个: 标志性建筑/夕阳/静帧

要求:
- 镜头多样性: 远景/特写/动态/静态混合
- 严禁重复或近似镜头
- 优先有内容的(人物/招牌/动作)
- 拒绝模糊/黑屏

⚠️ 同时给出 weights 数组(与 picks 等长),代表每个镜头的叙事权重:
- 2.0 = 重头戏(地标/人物特写/精彩动作),给长时长
- 1.0 = 普通镜头
- 0.5 = 空镜/过渡/转场,一闪而过

⚠️ 严格按此 JSON 格式返回,不要任何其他字符或 markdown 包裹:
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

    # Pad to n_target with cycling weights
    while len(picks_data) < n_target:
        picks_data.append(picks_data[len(picks_data) % max(1, len(picks_data))])
    picks_data = picks_data[:n_target]

    return [(samples[p]["src"], samples[p]["type"], samples[p]["ts"],
             samples[p]["dur"], w) for (p, w) in picks_data]


def ffmpeg_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


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
            bgm_pool = list(BGM.glob("*.mp3"))
            bgm_pool = [b for b in bgm_pool if probe_dur(b) > 10]
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
            d = max(0.7, min(2.8, d))  # bounds
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

        # 5. Render — 9:16 with overlaid title on first clip, FIN on last clip
        cine_vf = (
            "scale=720:1280:force_original_aspect_ratio=increase,"
            "crop=720:1280,setsar=1,"
            "eq=contrast=1.10:saturation=1.30:gamma=0.95,"
            "curves=r='0/0 0.5/0.55 1/1':b='0/0 0.5/0.45 1/0.95'"
        )

        # Title overlay vars
        title = job.get("title") or (job.get("prompt", "").strip().split()[:1] or ["VLOG"])[0]
        if re.search(r'[\u4e00-\u9fff]', title): display_title = title[:8]
        else: display_title = title.upper()[:12]
        date_str = time.strftime("%Y.%m")
        title_esc = ffmpeg_escape(display_title)
        date_esc = ffmpeg_escape(date_str)

        TITLE_DUR = 1.8  # how long title overlay lasts
        FIN_DUR = 1.2

        clip_dir = OUTPUTS / jid
        clip_dir.mkdir(parents=True, exist_ok=True)
        clips = []
        last_idx = len(picks) - 1
        for i, ((src, typ, ts, src_dur, _w), dur_beat) in enumerate(zip(picks, clip_durs)):
            out = clip_dir / f"c{i:03d}.mp4"
            vf = cine_vf
            # First clip: overlay BUDAPEST title (fade out)
            if i == 0:
                td = min(TITLE_DUR, dur_beat)
                # Use enable for time-gated darken; text alpha controls fade
                vf += (
                    f",drawbox=x=0:y=0:w=iw:h=ih:color=black@0.55:t=fill:enable='lt(t\\,{td-0.3:.2f})',"
                    f"drawtext=fontfile='{FONT_PATH}':text='{title_esc}':"
                    f"fontcolor=#ffb84d:fontsize=120:"
                    f"x=(w-text_w)/2:y=(h-text_h)/2-40:"
                    f"borderw=4:bordercolor=#1a1a1a:"
                    f"alpha='if(lt(t\\,0.3)\\,t/0.3\\,if(lt(t\\,{td-0.4:.2f})\\,1\\,if(lt(t\\,{td:.2f})\\,1-(t-{td-0.4:.2f})/0.4\\,0)))',"
                    f"drawtext=fontfile='{FONT_PATH}':text='{date_esc}':"
                    f"fontcolor=white:fontsize=40:"
                    f"x=(w-text_w)/2:y=(h-text_h)/2+80:"
                    f"alpha='if(lt(t\\,0.5)\\,0\\,if(lt(t\\,{td-0.4:.2f})\\,1\\,if(lt(t\\,{td:.2f})\\,1-(t-{td-0.4:.2f})/0.4\\,0)))'"
                )
            # Last clip: overlay FIN (fade in towards end)
            if i == last_idx:
                fd = min(FIN_DUR, dur_beat)
                t0 = max(0, dur_beat - fd)
                fin_esc = ffmpeg_escape("FIN")
                vf += (
                    f",drawbox=x=0:y=0:w=iw:h=ih:color=black@0.45:t=fill:enable='gte(t\\,{t0+0.3:.2f})',"
                    f"drawtext=fontfile='{FONT_PATH}':text='{fin_esc}':"
                    f"fontcolor=#ffb84d:fontsize=140:"
                    f"x=(w-text_w)/2:y=(h-text_h)/2:"
                    f"borderw=4:bordercolor=#1a1a1a:"
                    f"alpha='if(lt(t\\,{t0+0.2:.2f})\\,0\\,min(1\\,(t-{t0+0.2:.2f})/0.3))'"
                )
            if typ == "video":
                start_t = max(0, min(max(0, src_dur - dur_beat - 0.05), ts - dur_beat/2))
                cmd = ["ffmpeg", "-y", "-ss", f"{start_t:.3f}", "-i", str(src),
                    "-t", f"{dur_beat:.3f}",
                    "-vf", vf,
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-an", str(out)]
            else:
                frames = max(2, int(dur_beat * 30))
                vf_img = vf + f",zoompan=z='min(zoom+0.0015,1.18)':d={frames}:s=720x1280"
                # zoompan must be before draws -> rebuild order
                cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(src), "-t", f"{dur_beat:.3f}",
                    "-vf", vf,  # zoompan on image without overlay separately
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-an", "-pix_fmt", "yuv420p", str(out)]
            subprocess.run(cmd, check=True, capture_output=True)
            clips.append(out)
        log(f"渲染 {len(clips)} 段(片头/片尾叠在素材上)", 80)

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
