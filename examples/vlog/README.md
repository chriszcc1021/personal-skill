# vlog — AI Vlog 自动剪辑工具

## 目标
iPhone 桌面 PWA：丢素材 → 选风格 → AI 自动剪 → 出片下载

## 状态
🚧 规划中（2026-05-16 立项）

## 路线图
- [ ] MVP 范围 + 风格预设确认
- [ ] 前端 PWA 骨架（Next.js + Tailwind）
- [ ] 后端 API（FastAPI + ffmpeg）
- [ ] AI 挑片段（Gemini Vision）
- [ ] BGM + 卡点（librosa）
- [ ] HTTPS 部署 + iOS 安装

## 技术栈
- 前端：Next.js 14 + PWA plugin + Tailwind + shadcn
- 后端：FastAPI + Celery + Redis
- AI：Claude（导演）+ Gemini Vision（看片）+ Whisper（转录）
- 媒体处理：ffmpeg + librosa
- 部署：43.134.32.223 nginx + cloudflare tunnel

详细方案见 main session 讨论记录。
