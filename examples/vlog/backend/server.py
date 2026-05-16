"""vlog backend MVP — FastAPI
功能:
- POST /api/upload       上传单个素材文件
- POST /api/refs/upload  上传参考 vlog 视频 (学习风格)
- POST /api/jobs         提交剪辑任务 {style, prompt, asset_ids[]}
- GET  /api/jobs/{id}    查询任务状态
- GET  /api/jobs/{id}/result  下载成片
"""
import os, uuid, json, subprocess, random, time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import aiofiles
import asyncio

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


async def run_job(jid: str):
    """MVP: 找到所有上传的视频 -> 按 6s/片段抽样 -> 拼接 -> 加 BGM"""
    jf = JOBS / f"{jid}.json"
    job = json.loads(jf.read_text())

    def log(msg: str, progress: int):
        job["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        job["progress"] = progress
        jf.write_text(json.dumps(job, ensure_ascii=False, indent=2))

    try:
        job["status"] = "running"
        log("Job started", 5)

        # 找素材
        assets_dir = user_dir(UPLOADS)
        candidates = []
        for aid in job["asset_ids"]:
            for f in assets_dir.glob(f"{aid}.*"):
                candidates.append(f)
        if not candidates:
            raise RuntimeError("No assets found")
        videos = [c for c in candidates if c.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm")]
        images = [c for c in candidates if c not in videos]
        log(f"Found {len(videos)} videos, {len(images)} images", 15)

        # 每个视频随机抽 1 段 4 秒;每张图 stills 2 秒
        clip_dir = OUTPUTS / jid
        clip_dir.mkdir(parents=True, exist_ok=True)
        clips = []
        for i, v in enumerate(videos):
            dur = probe_dur(v)
            start = random.uniform(0, max(0.1, dur - 4))
            out = clip_dir / f"v{i:03d}.mp4"
            cmd = [
                "ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", str(v), "-t", "4",
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
                "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-an", str(out),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            clips.append(out)
        log(f"Extracted {len(clips)} video clips", 50)

        for i, img in enumerate(images):
            out = clip_dir / f"i{i:03d}.mp4"
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", str(img), "-t", "2",
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1,zoompan=z='min(zoom+0.001,1.1)':d=60:s=1280x720",
                "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-an", "-pix_fmt", "yuv420p", str(out),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            clips.append(out)
        log(f"Total {len(clips)} clips ready", 70)

        # 拼接
        random.shuffle(clips)
        concat_list = clip_dir / "concat.txt"
        concat_list.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
        merged = clip_dir / "merged.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(merged),
        ], check=True, capture_output=True)
        log("Concat done", 85)

        # BGM (随便挑一首)
        bgm_files = list(BGM.glob("*.mp3")) + list(BGM.glob("*.wav"))
        final = OUTPUTS / f"{jid}.mp4"
        if bgm_files:
            bgm_file = random.choice(bgm_files)
            subprocess.run([
                "ffmpeg", "-y", "-i", str(merged), "-i", str(bgm_file),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-map", "0:v", "-map", "1:a", "-shortest",
                "-af", "volume=0.6",
                str(final),
            ], check=True, capture_output=True)
            log(f"BGM applied: {bgm_file.name}", 95)
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", str(merged), "-c", "copy", str(final),
            ], check=True, capture_output=True)
            log("No BGM available, silent output", 95)

        # 清理中间产物
        for f in clip_dir.glob("*.mp4"):
            f.unlink()
        concat_list.unlink(missing_ok=True)
        clip_dir.rmdir()

        job["status"] = "done"
        job["output"] = str(final)
        job["duration"] = probe_dur(final)
        log("Job done", 100)
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
