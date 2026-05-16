"""vlog backend v0.3 — Travel-only, beat-synced, AI scene picking.

Pipeline:
- Pick BGM
- librosa beat detect → beat timestamps
- AI picks N best clips from candidates (sub-scenes via PySceneDetect or time samples)
- Cut clips strictly at beat boundaries: intro 2-beat / verse 1-beat / chorus 0.5-beat
"""
import os, uuid, json, subprocess, random, time, base64, shutil, math
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import aiofiles, asyncio
import urllib.request

GATEWAY_URL = os.environ.get("VLOG_GATEWAY_URL", "https://new-api.openclaw.ingarena.net")
GATEWAY_KEY = os.environ.get("VLOG_GATEWAY_KEY", "")
MODEL_VISION = "claude-sonnet-4-5-20250929"

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


@app.get("/api/health")
async def health(): return {"ok": True, "ts": int(time.time())}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    aid = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix.lower() or ".bin"
    dest = user_dir(UPLOADS) / f"{aid}{ext}"
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            await f.write(chunk)
    kind = "video" if ext in (".mp4", ".mov", ".m4v", ".webm") else "image"
    # Generate thumbnail for preview
    thumb = user_dir(UPLOADS) / f"{aid}_thumb.jpg"
    try:
        if kind == "video":
            subprocess.run(["ffmpeg", "-y", "-ss", "0.5", "-i", str(dest), "-vframes", "1",
                "-vf", "scale=240:-1", str(thumb)], check=True, capture_output=True, timeout=30)
        else:
            subprocess.run(["ffmpeg", "-y", "-i", str(dest), "-vf", "scale=240:-1",
                str(thumb)], check=True, capture_output=True, timeout=30)
    except Exception:
        pass
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
    # Auto-extract its BGM as a candidate
    try:
        bgm_out = BGM / f"ref-{rid}.mp3"
        subprocess.run(["ffmpeg", "-y", "-i", str(dest), "-vn", "-acodec", "libmp3lame",
                       "-b:a", "192k", str(bgm_out)], check=True, capture_output=True, timeout=60)
    except Exception:
        pass
    return meta


@app.get("/api/refs")
async def list_refs():
    out = []
    for jf in sorted(user_dir(REFS).glob("*.json")):
        try: out.append(json.loads(jf.read_text()))
        except: pass
    return out


@app.post("/api/jobs")
async def create_job(prompt: str = Form(""), asset_ids: str = Form(""),
                     ref_id: Optional[str] = Form(None)):
    jid = uuid.uuid4().hex[:12]
    aids = [a.strip() for a in asset_ids.split(",") if a.strip()]
    job = {"id": jid, "status": "queued", "prompt": prompt, "asset_ids": aids,
           "ref_id": ref_id, "created_at": int(time.time()), "progress": 0, "logs": []}
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


def detect_beats(bgm_path: Path) -> tuple:
    """Returns (tempo, beat_times[], total_duration)"""
    try:
        import librosa
        y, sr = librosa.load(str(bgm_path), sr=22050, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        dur = float(librosa.get_duration(y=y, sr=sr))
        t = float(tempo) if hasattr(tempo, '__float__') else float(tempo[0]) if len(tempo) else 120.0
        return t, beat_times, dur
    except Exception as e:
        print(f"beat err: {e}")
        return 120.0, [], 60.0


def build_beat_schedule(beat_times, total_dur):
    """Build cut schedule: intro slow 2-beat × 2, main 1-beat × N, chorus 0.5-beat × 8, outro 2-beat × 2.
    Returns list of (start_t, dur_seconds)."""
    if len(beat_times) < 8:
        # fallback fixed rhythm
        n = max(8, int(total_dur / 1.2))
        return [(i * 1.2, 1.2) for i in range(n) if (i+1)*1.2 < total_dur]

    schedule = []
    bt = beat_times
    n_beats = len(bt)
    # Section split: intro 0-15%, main 15-50%, chorus 50-85%, outro 85-100%
    intro_end = int(n_beats * 0.15)
    main_end = int(n_beats * 0.50)
    chorus_end = int(n_beats * 0.85)

    i = 0
    # Intro: 2-beat clips
    while i < intro_end - 1:
        start = bt[i]
        nxt = bt[min(i+2, n_beats-1)]
        schedule.append((start, nxt - start))
        i += 2
    # Main: 1-beat clips
    while i < main_end - 1:
        start = bt[i]
        nxt = bt[min(i+1, n_beats-1)]
        schedule.append((start, nxt - start))
        i += 1
    # Chorus: half-beat (every other beat we slice into 2)
    while i < chorus_end - 1:
        a = bt[i]
        b = bt[min(i+1, n_beats-1)]
        mid = (a + b) / 2
        schedule.append((a, mid - a))
        schedule.append((mid, b - mid))
        i += 1
    # Outro: 2-beat
    while i < n_beats - 1:
        start = bt[i]
        nxt = bt[min(i+2, n_beats-1)]
        schedule.append((start, nxt - start))
        i += 2

    # Filter too short / too long
    schedule = [(t, d) for (t, d) in schedule if 0.25 <= d <= 4.0 and t < total_dur]
    return schedule[:80]  # cap


def ai_pick_clips(videos, images, prompt, n_target, log_fn):
    """Sample frames from all videos+images, send to Claude, return ordered list of
    (src_path, type, frame_time) with len >= n_target (oversample)"""
    samples = []  # {src, type, ts, thumb, dur}
    thumb_dir = OUTPUTS / "_thumbs"
    thumb_dir.mkdir(exist_ok=True)
    for v in videos:
        dur = probe_dur(v)
        # Sample more densely (every 2s up to 8 samples per video)
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
    log_fn(f"抽取 {len(samples)} 帧候选,送 AI 排片", 30)

    # Cap to 25 for token budget
    samples = samples[:25]

    user_prompt = f"""你是旅行 vlog 剪辑师。我有 {len(samples)} 个候选帧,编号 0-{len(samples)-1}。

风格: 旅行 vlog,快节奏卡点剪辑(类似抖音/Instagram Reels)。
用户描述: {prompt or "(无)"}

任务: 挑 {n_target} 个最值得用的帧,按"叙事节奏"排列:
1. 开头 2-3 个: 地标/全景/天空(建立场景)
2. 中段大量混切: 人物动作/街景/招牌/特写/细节
3. 结尾 2-3 个: 标志性建筑/夕阳/慢镜头(收尾)

要求:
- 镜头多样性: 远景/特写/动态/静态混合
- 避免重复镜头
- 优先有内容的(人物、招牌、动作)
- 拒绝模糊/黑屏/重复

只返回 JSON,无其他文字:
{{"picks": [0,5,2,8,...], "reason": "一句中文解释"}}

如果可用帧不够 {n_target} 个,picks 可以包含重复编号(后续会从原片不同位置切)。"""

    images_for_api = [s["thumb"] for s in samples]
    resp = call_claude_vision(user_prompt, images_for_api, max_tokens=1500)
    log_fn(f"AI 回复: {resp[:80]}...", 40)

    picks = list(range(min(n_target, len(samples))))
    try:
        s = resp.strip()
        if s.startswith("```"):
            s = s.split("```")[1]
            if s.startswith("json"): s = s[4:]
        j = json.loads(s)
        if isinstance(j.get("picks"), list):
            picks = [int(x) for x in j["picks"] if 0 <= int(x) < len(samples)]
            log_fn(f"AI 排片: {j.get('reason', '')[:60]}", 45)
    except Exception as e:
        log_fn(f"解析失败兜底: {e}", 45)

    # Ensure enough picks
    while len(picks) < n_target:
        picks.append(picks[len(picks) % max(1, len(picks))])
    return [(samples[p]["src"], samples[p]["type"], samples[p]["ts"], samples[p]["dur"])
            for p in picks[:n_target]]


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

        # 1. Pick BGM (prefer ref-extracted, else random)
        ref_bgm = None
        if job.get("ref_id"):
            cand = BGM / f"ref-{job['ref_id']}.mp3"
            if cand.exists(): ref_bgm = cand
        if not ref_bgm:
            bgm_pool = list(BGM.glob("travel-*.mp3")) + list(BGM.glob("*.mp3"))
            bgm_pool = [b for b in bgm_pool if probe_dur(b) > 10]
            if not bgm_pool:
                raise RuntimeError("No BGM available")
            ref_bgm = random.choice(bgm_pool)
        log(f"BGM: {ref_bgm.name}", 10)

        # 2. Beat detection
        loop = asyncio.get_event_loop()
        tempo, beats, bgm_dur = await loop.run_in_executor(None, detect_beats, ref_bgm)
        log(f"节拍: BPM={tempo:.1f}, {len(beats)} beats, {bgm_dur:.1f}s", 15)

        # 3. Schedule (target ~20-30s video)
        target_dur = min(bgm_dur, 30.0)
        schedule = build_beat_schedule(beats, target_dur)
        # Trim schedule so total fits target
        total = 0; trimmed = []
        for st, d in schedule:
            if total + d > target_dur: break
            trimmed.append((st, d)); total += d
        schedule = trimmed
        log(f"节拍卡点 {len(schedule)} 段,总长 {total:.1f}s", 20)

        # 4. Collect assets
        assets_dir = user_dir(UPLOADS)
        candidates = []
        for aid in job["asset_ids"]:
            for f in assets_dir.glob(f"{aid}.*"):
                if "_thumb" not in f.name: candidates.append(f)
        videos = [c for c in candidates if c.suffix.lower() in (".mp4",".mov",".m4v",".webm")]
        images = [c for c in candidates if c not in videos]
        if not candidates:
            raise RuntimeError("No assets")
        log(f"{len(videos)} 视频 {len(images)} 图", 25)

        # 5. AI picks
        n_target = len(schedule)
        picks = await loop.run_in_executor(None, ai_pick_clips,
                                           videos, images, job["prompt"], n_target, log)
        if not picks:
            raise RuntimeError("AI 未挑出片段")

        # 6. Render each clip aligned to beat duration
        clip_dir = OUTPUTS / jid
        clip_dir.mkdir(parents=True, exist_ok=True)
        clips = []
        for i, ((st_beat, dur_beat), (src, typ, ts, src_dur)) in enumerate(zip(schedule, picks)):
            out = clip_dir / f"c{i:03d}.mp4"
            # video output dimensions: 9:16 portrait OR 16:9 landscape -- choose 16:9 (matches HK ref)
            scale_vf = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1"
            if typ == "video":
                start_t = max(0, min(src_dur - dur_beat - 0.05, ts - dur_beat/2))
                start_t = max(0, start_t)
                cmd = ["ffmpeg", "-y", "-ss", f"{start_t:.3f}", "-i", str(src),
                    "-t", f"{dur_beat:.3f}",
                    "-vf", scale_vf + ",eq=saturation=1.15:gamma_r=1.05",  # slight warm/saturated
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-an", str(out)]
            else:
                # Image: Ken Burns zoom over the beat duration
                frames = max(2, int(dur_beat * 30))
                cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(src), "-t", f"{dur_beat:.3f}",
                    "-vf", scale_vf + f",zoompan=z='min(zoom+0.0015,1.15)':d={frames}:s=1280x720,eq=saturation=1.15:gamma_r=1.05",
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-an", "-pix_fmt", "yuv420p", str(out)]
            subprocess.run(cmd, check=True, capture_output=True)
            clips.append(out)
        log(f"渲染 {len(clips)} 段", 80)

        # 7. Concat
        concat_list = clip_dir / "concat.txt"
        concat_list.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
        merged = clip_dir / "merged.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(merged)], check=True, capture_output=True)
        log("拼接完成", 88)

        # 8. Add BGM (trim to video length, fade out)
        final = OUTPUTS / f"{jid}.mp4"
        video_len = probe_dur(merged)
        subprocess.run(["ffmpeg", "-y", "-i", str(merged), "-i", str(ref_bgm),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-map", "0:v", "-map", "1:a", "-t", f"{video_len:.2f}",
            "-af", f"afade=t=out:st={max(0, video_len-1.5):.2f}:d=1.5,volume=0.8",
            str(final)], check=True, capture_output=True)
        log(f"加 BGM ({ref_bgm.name})", 96)

        # Cleanup
        for f in clip_dir.glob("*"): f.unlink()
        try: clip_dir.rmdir()
        except: pass

        job["status"] = "done"; job["output"] = str(final); job["duration"] = probe_dur(final)
        log("完成", 100)
    except subprocess.CalledProcessError as e:
        job["status"] = "error"
        job["error"] = f"ffmpeg: {e.stderr.decode()[-400:]}"
        log(f"❌ {job['error'][:200]}", job["progress"])
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
    if not f.exists(): raise HTTPException(404, "result not ready")
    return FileResponse(f, media_type="video/mp4", filename=f"vlog_{jid}.mp4")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
