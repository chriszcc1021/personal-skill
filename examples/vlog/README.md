# vlog — AI 旅行 Vlog 自动剪辑

iPhone 桌面 PWA：丢素材 → AI 自动剪 → 9:16 卡点旅行 vlog 出片。

## 现况（v1.7.2 · 2026-05-16）

- ✅ 多视频/图片上传，并发 + 进度条 + 失败重试
- ✅ Gemini 2.5 Flash 原生看视频（找精髓窗口、识别地点、识别主体坐标）
  - 串行 + 6s 间隔 + 15/35/60s 重试（应对免费档 RPM 限流）
- ✅ Claude（gateway claude-sonnet-4-6）做导演选片 + 时长权重
- ✅ librosa 探测 BGM 副歌起点（≥30s 且 intro ≥12s 且在前 1/3 才跳）
- ✅ 卡点：beat snap → MIN_FIRST/LAST 调整 → 再 snap
- ✅ AI 输出三层验证：Gemini 越界 clamp · dedup max 1/src + 4s 窗口 · 渲染预检计划表
- ✅ 9:16 主体感知裁切：Gemini bbox → OpenCV Haar 人脸/显著性 → 默认 0.5/0.4 偏上构图
- ✅ ASS 字幕：Anton + mustard yellow + 柔和阴影（去掉硬黑边/3D 透视）
- ✅ 生成总结卡片 + 详细日志（视频下方展开）
- ✅ ETA 提示（toast + 进度条下持续显示剩余分钟）
- ✅ iOS 存相册引导（点存到相册 → 全屏播放 → 右下分享 → 存储视频）

## 技术栈

- 前端：原生 HTML + PWA（manifest.json + sw.js + apple-touch-icon）
- 后端：FastAPI + uvicorn（单 worker，asyncio）
- AI：
  - Gemini 2.5 Flash：原生视频输入（Files API resumable upload + generateContent）
  - Claude sonnet-4-6（gateway 中转）：导演级 picks + weights
- 媒体：ffmpeg（crop / zoompan / drawbox / ASS subtitles）+ librosa（beats / RMS chorus）
- 主体检测：opencv-python-headless（Haar 人脸 + spectral saliency）
- 部署：systemd + nginx 反代 + cloudflare tunnel

## 目录

```
backend/
  server.py            # FastAPI app（所有业务逻辑）
  disk_monitor.py      # 每天 10:00 SGT 配额监控
  requirements.txt
frontend/
  index.html           # 单文件 SPA
  manifest.json sw.js icon-*.png
deploy/
  vlog-api.service     # systemd unit 模板
  nginx.conf           # nginx 反代片段
```

## 部署速记

```bash
sudo mkdir -p /var/www/vlog /var/vlog-data/{uploads/you,outputs,bgm,refs,jobs}
sudo chown -R ubuntu:ubuntu /var/www/vlog /var/vlog-data
cd /var/www/vlog
python3 -m venv venv
./venv/bin/pip install -r backend/requirements.txt
cp backend/server.py /var/www/vlog/server.py
cp -r frontend/ /var/www/vlog/frontend/
sudo cp deploy/vlog-api.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now vlog-api
# 把 deploy/nginx.conf 内容贴进现有 server block，reload nginx
```

环境变量（写进 service 文件）：
- `VLOG_GATEWAY_URL` / `VLOG_GATEWAY_KEY` — Claude 网关
- `GEMINI_API_KEY` — Google AI Studio

## 已知边界

- Gemini 免费档 RPM 很低，多视频偶发全 429（已用 6s 间隔 + 重试缓解，未根治）
- 主体跟踪：只在 clip 中点抽 1 帧定位 crop，主体在画面里跑动**不会跟**
- 卡点节奏目前均匀切，BGM 强/弱段不分（v1.6b 计划做能量曲线分段）
- 文件入口仅本机，没有用户系统 / 鉴权

## 版本足迹

- v0.4：字幕叠在素材上、AI 权重
- v0.5：Anton + ASS + 9:16 裁切
- v1.0–v1.1：cinematic color + beat snap
- v1.2：Gemini 2.5 Flash 原生视频
- v1.3：librosa 探测副歌
- v1.4：AI 输出三层验证（clamp + dedup + preflight）
- v1.5：UI 重做 + auto skip_intro
- v1.6a：Gemini 串行+重试、title 从地点取、去硬黑边、生成总结
- v1.7：主体感知裁切（Gemini bbox + OpenCV 兜底）
- v1.7.1：ETA + Gemini 间隔放宽
- v1.7.2：CV 默认坐标 0.5/0.4
