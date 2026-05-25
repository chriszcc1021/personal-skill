# claw-console

OpenClaw 本地控制台 — 管理 sessions / projects / usage stats。

## 架构
- `backend/server.py` — Python stdlib HTTPServer，默认 `:8088`
- `frontend/index.html` — vanilla JS PWA

## 启动
```bash
python3 backend/server.py
# 或自定义端口
CONSOLE_PORT=8088 python3 backend/server.py
```

## 数据
- `data/group-names.json` — SeaTalk 群名映射

VERSION: 见 `VERSION` 文件
