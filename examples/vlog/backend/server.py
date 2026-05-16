"""vlog backend MVP — FastAPI
功能:
- POST /api/upload       上传单个素材文件
- POST /api/refs/upload  上传参考 vlog 视频 (学习风格)
- POST /api/jobs         提交剪辑任务 {style, prompt, asset_ids[]}
- GET  /api/jobs/{id}    查询任务状态
- GET  /api/jobs/{id}/result  下载成片
"""
import os, uuid, json, subprocess, random, time, base64, shutil
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import aiofiles
import asyncio
import urllib.request, urllib.error

GATEWAY_URL = os.environ.get("VLOG_GATEWAY_URL", "https://new-api.openclaw.ingarena.net")
GATEWAY_KEY = os.environ.get("VLOG_GATEWAY_KEY", "")
MODEL_VISION = "claude-sonnet-4-5-20250929"  # vision-capable, cheap

ROOT = Path("/var/vlog-data")
UPLOADS = ROOT / "uploads"   # 用户素材
REFS = ROOT / "refs"          # 参考 vlog
OUTPUTS = ROOT / "outputs"    # 成片
BGM = ROOT / "bgm"            # BGM 库
JOBS = ROOT / "jobs"          # 任务状态
for p in (UPLOADS, REFS, OUTPUTS, BGM, JOBS):
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="vlog-mvp")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

USER_ID = "you"  # 单用户预埋,后续按 token 替换


def user_dir(base: Path) -> Path:
    p = base / USER_ID
    p.mkdir(parents=True, exist_ok=True)
    return p


@app.get("/api/health")
async def health():
    return {"ok": True, "ts": int(time.time())}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """上传单个素材 (照片 / 视频)"""
    aid = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix.lower() or ".bin"
    dest = user_dir(UPLOADS) / f"{aid}{ext}"
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            await f.write(chunk)
    size = dest.stat().st_size
    kind = "video" if ext in (".mp4", ".mov", ".m4v", ".webm") else "image"
    return {"id": aid, "kind": kind, "size": size, "filename": file.filename}


@app.post("/api/refs/upload")
async def upload_ref(file: UploadFile = File(...), name: Optional[str] = Form(None)):
    """上传参考 vlog,稍后会被分析提取 style profile"""
    rid = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix.lower() or ".mp4"
    dest = user_dir(REFS) / f"{rid}{ext}"
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            await f.write(chunk)
    meta = {
        "id": rid,
        "name": name or file.filename,
        "path": str(dest),
        "uploaded_at": int(time.time()),
        "analyzed": False,
    }
    (user_dir(REFS) / f"{rid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return meta


@app.get("/api/refs")
async def list_refs():
    out = []
    for jf in sorted(user_dir(REFS).glob("*.json")):
        try:
            out.append(json.loads(jf.read_text()))
        except Exception:
            pass
    return out


@app.post("/api/jobs")
async def create_job(
    style: str = Form(...),  # daily / travel
    prompt: str = Form(""),
    asset_ids: str = Form(""),  # 逗号分隔
    ref_id: Optional[str] = Form(None),
):
    if style not in ("daily", "travel"):
        raise HTTPException(400, "style must be daily or travel")
    jid = uuid.uuid4().hex[:12]
    aids = [a.strip() for a in asset_ids.split(",") if a.strip()]
    job = {
        "id": jid,
        "status": "queued",
        "style": style,
        "prompt": prompt,
        "asset_ids": aids,
        "ref_id": ref_id,
        "created_at": int(time.time()),
        "progress": 0,
        "logs": [],
    }
    (JOBS / f"{jid}.json").write_text(json.dumps(job, ensure_ascii=False, indent=2))
    # fire background task
    asyncio.create_task(run_job(jid))
    return job


def extract_thumb(video: Path, t: float, out: Path) -> bool:
    try:
        subprocess.run([
            "ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-vframes", "1",
            "-vf", "scale=480:-1", str(out),
        ], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def call_claude_vision(prompt: str, image_paths: List[Path], max_tokens: int = 1200) -> str:
    """Send images + prompt to Claude via Garena gateway (OpenAI-compatible /v1/chat/completions)."""
    if not GATEWAY_KEY:
        return ""
    content = [{"type": "text", "text": prompt}]
    for p in image_paths:
        try:
            b64 = base64.b64encode(p.read_bytes()).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        except Exception:
            continue
    body = json.dumps({
        "model": MODEL_VISION,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{GATEWAY_URL}/v1/chat/completions",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {GATEWAY_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read())
            return j["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Claude vision error: {e}")
        return ""


STYLE_CONFIG = {
    "daily": {"clip_dur": 3.5, "img_dur": 1.8, "hint": "温和日常节奏,镜头切换轻快,挑能体现生活感的瞬间"},
    "travel": {"clip_dur": 5.5, "img_dur": 2.5, "hint": "电影感慢节奏,挑大景/移动镜头/标志性建筑,优先广角"},
}


def ai_pick_and_arrange(videos, images, style, prompt, log_fn):
    """对每个视频均匀抽 3 帧 + 每张图 1 帧 -> 喂 Claude -> 返回排好序的 plan:
    [{"src": path, "type": "video", "start": 0.0, "dur": 4.0}, ...]
    """
    cfg = STYLE_CONFIG[style]
    samples = []  # list of (src_path, type, ts_in_src, thumb_path)
    thumb_dir = OUTPUTS / "_thumbs"
    thumb_dir.mkdir(exist_ok=True)

    for v in videos:
        dur = probe_dur(v)
        for k, frac in enumerate([0.2, 0.5, 0.8]):
            ts = dur * frac
            tp = thumb_dir / f"{uuid.uuid4().hex[:8]}.jpg"
            if extract_thumb(v, ts, tp):
                samples.append({"src": v, "type": "video", "ts": ts, "thumb": tp, "src_dur": dur})
    for img in images:
        # use the image itself as thumb (after rescale)
        tp = thumb_dir / f"{uuid.uuid4().hex[:8]}.jpg"
        try:
            subprocess.run(["ffmpeg", "-y", "-i", str(img), "-vf", "scale=480:-1", str(tp)],
                          check=True, capture_output=True)
            samples.append({"src": img, "type": "image", "ts": 0, "thumb": tp, "src_dur": 0})
        except Exception:
            pass

    if not samples:
        return []
    log_fn(f"抽取 {len(samples)} 个候选帧,送 AI 挑选", 30)

    # 限制到最多 20 张避免 token 爆炸
    samples = samples[:20]
    numbered = [(i, s) for i, s in enumerate(samples)]
    user_prompt = f"""你是 AI vlog 剪辑师。我有 {len(samples)} 个候选帧,按顺序编号 0-{len(samples)-1}。

风格: {style} ({cfg['hint']})
用户描述: {prompt or '(无)'}

任务: 挑 6-12 个最值得用的帧,按叙事顺序排列。优先考虑:
1. 画面有内容(不模糊、不黑屏、不重复)
2. 镜头有差异(远景+特写+人物穿插)
3. 符合 {style} 风格

只返回 JSON,不要任何其他文字。格式:
{{"picks": [0, 5, 2, 8, ...], "reason": "一句中文解释为什么这么排"}}"""

    images_for_api = [s["thumb"] for s in samples]
    resp = call_claude_vision(user_prompt, images_for_api)
    log_fn(f"AI 回复: {resp[:80]}", 40)

    # parse
    picks = list(range(min(8, len(samples))))  # fallback
    try:
        s = resp.strip()
        if s.startswith("```"):
            s = s.split("```")[1]
            if s.startswith("json"): s = s[4:]
        j = json.loads(s)
        if "picks" in j and isinstance(j["picks"], list):
            picks = [int(x) for x in j["picks"] if 0 <= int(x) < len(samples)]
            log_fn(f"AI 选: {j.get('reason', '')[:60]}", 45)
    except Exception as e:
        log_fn(f"AI 解析失败,用兜底: {e}", 45)

    plan = []
    for idx in picks:
        s = samples[idx]
        if s["type"] == "video":
            start = max(0, s["ts"] - cfg["clip_dur"] / 2)
            plan.append({"src": s["src"], "type": "video",
                        "start": start, "dur": cfg["clip_dur"]})
        else:
            plan.append({"src": s["src"], "type": "image",
                        "start": 0, "dur": cfg["img_dur"]})
    return plan


async def run_job(jid: str):
    """AI 驱动: 抽帧 -> Claude 挑/排 -> ffmpeg 拼接."""
    jf = JOBS / f"{jid}.json"
    job = json.loads(jf.read_text())

    def log(msg: str, progress: int):
        job["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        job["progress"] = progress
        jf.write_text(json.dumps(job, ensure_ascii=False, indent=2))

    try:
        job["status"] = "running"
        log("开始任务", 5)

        assets_dir = user_dir(UPLOADS)
        candidates = []
        for aid in job["asset_ids"]:
            for f in assets_dir.glob(f"{aid}.*"):
                candidates.append(f)
        if not candidates:
            raise RuntimeError("No assets found")
        videos = [c for c in candidates if c.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm")]
        images = [c for c in candidates if c not in videos]
        log(f"找到 {len(videos)} 视频 {len(images)} 图", 15)

        # AI 挑片段 + 排序
        loop = asyncio.get_event_loop()
        plan = await loop.run_in_executor(None, ai_pick_and_arrange,
                                          videos, images, job["style"], job["prompt"], log)
        if not plan:
            raise RuntimeError("AI 没挑出可用片段")
        log(f"AI 排好 {len(plan)} 段", 60)

        clip_dir = OUTPUTS / jid
        clip_dir.mkdir(parents=True, exist_ok=True)
        clips = []
        for i, p in enumerate(plan):
            out = clip_dir / f"c{i:03d}.mp4"
            if p["type"] == "video":
                cmd = [
                    "ffmpeg", "-y", "-ss", f"{p['start']:.2f}", "-i", str(p["src"]), "-t", f"{p['dur']:.2f}",
                    "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-an", str(out),
                ]
            else:
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(p["src"]), "-t", f"{p['dur']:.2f}",
                    "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1,zoompan=z='min(zoom+0.001,1.1)':d=60:s=1280x720",
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-an", "-pix_fmt", "yuv420p", str(out),
                ]
            subprocess.run(cmd, check=True, capture_output=True)
            clips.append(out)
        log(f"切完 {len(clips)} 段", 80)

        concat_list = clip_dir / "concat.txt"
        concat_list.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
        merged = clip_dir / "merged.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(merged),
        ], check=True, capture_output=True)
        log("拼接完成", 90)

        bgm_files = list(BGM.glob("*.mp3")) + list(BGM.glob("*.wav"))
        final = OUTPUTS / f"{jid}.mp4"
        if bgm_files:
            bgm_file = random.choice(bgm_files)
            subprocess.run([
                "ffmpeg", "-y", "-i", str(merged), "-i", str(bgm_file),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-map", "0:v", "-map", "1:a", "-shortest", "-af", "volume=0.6",
                str(final),
            ], check=True, capture_output=True)
            log(f"加 BGM: {bgm_file.name}", 98)
        else:
            shutil.move(str(merged), str(final))
            log("无 BGM,纯画面", 98)

        # 清理
        for f in clip_dir.glob("*.mp4"):
            f.unlink()
        for f in clip_dir.glob("*.txt"):
            f.unlink()
        try: clip_dir.rmdir()
        except: pass

        job["status"] = "done"
        job["output"] = str(final)
        job["duration"] = probe_dur(final)
        log("完成", 100)
    except subprocess.CalledProcessError as e:
        job["status"] = "error"
        job["error"] = f"ffmpeg failed: {e.stderr.decode()[-500:]}"
        log(f"ERROR: {job['error']}", job["progress"])
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"ERROR: {e}", job["progress"])
    finally:
        jf.write_text(json.dumps(job, ensure_ascii=False, indent=2))


def probe_dur(path: Path) -> float:
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(path),
        ], text=True).strip()
        return float(out)
    except Exception:
        return 0.0


@app.get("/api/jobs/{jid}")
async def get_job(jid: str):
    jf = JOBS / f"{jid}.json"
    if not jf.exists():
        raise HTTPException(404, "job not found")
    return json.loads(jf.read_text())


@app.get("/api/jobs/{jid}/result")
async def job_result(jid: str):
    f = OUTPUTS / f"{jid}.mp4"
    if not f.exists():
        raise HTTPException(404, "result not ready")
    return FileResponse(f, media_type="video/mp4", filename=f"vlog_{jid}.mp4")


@app.get("/api/bgm")
async def list_bgm():
    out = []
    for f in sorted(BGM.glob("*.*")):
        if f.suffix.lower() in (".mp3", ".wav", ".m4a"):
            out.append({"name": f.name, "size": f.stat().st_size})
    return out


# 静态前端
FRONTEND = Path(__file__).parent.parent / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
