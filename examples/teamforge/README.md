# TeamForge · 团队管理 RPG 平台

Leader 驾驶舱：角色卡 + 团队战力 + (后续) 项目编排 + 任务派发 + SeaTalk 推送。

## v0.3 (2026-05-16)
- 6 张角色卡 (头像 + 一句话风格 + 12 维技能雷达 + 满载度 + bio + "更多"折叠)
- Apple 设计风格 (浅色 + SF Pro + macOS segmented nav)
- 后端 FastAPI + SQLite 持久化
- CRUD: 新增 / 编辑 / 软删除 (回收站可恢复) / 彻底删除
- 抽屉编辑器: 基础 / 风格 / 满载度 + 12 维技能 (默认折叠) + 头像上传
- 2 次确认删除 + Toast 撤销

## 部署
```
sudo mkdir -p /var/www/teamforge /var/teamforge-data/avatars
cp -r backend frontend /var/www/teamforge/
cp frontend/index.html /var/www/teamforge/
python3 -m venv /var/www/teamforge/venv && /var/www/teamforge/venv/bin/pip install -r backend/requirements.txt
sudo cp deploy/teamforge-api.service /etc/systemd/system/ && sudo systemctl enable --now teamforge-api
# nginx: 把 deploy/nginx.conf 内容贴进现有 server block
```

## TODO
- 项目编排器 (输入目标 → AI 拆任务 + 推荐人选 + 风险/缺口)
- 任务看板 + DDL 提醒
- SeaTalk 推送 (走 fastpublish 通道)
- 拖拽排序 (API 已就绪 /characters/reorder)
- AI 简历自动生卡
