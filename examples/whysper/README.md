# Whysper

语音笔记 PWA — Nothing OS 风格。

## 功能
- 按住录音，实时本地 STT 草稿
- 上传音频/图片，服务器 Whisper 转写
- AI 整理（手动 + 每晚 23:00 自动）
- 日历视图 + 标签云 + AI 问答
- 10G 磁盘上限巡检

## 部署
- 后端 FastAPI 端口 8084 (systemd: whysper-api)
- 前端 nginx alias `/whysper/`
- 数据 `/var/whysper-data/{audio,images,db.sqlite}`
- cron: 23:00 SGT 整理 + 0:30 磁盘巡检
