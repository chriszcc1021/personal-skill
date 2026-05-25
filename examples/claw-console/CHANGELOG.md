# Squid Console Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/),
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.2] - 2026-05-19
### Added
- Sidebar 标题改成「张鱼哥你好」，通知前缀 `Squid · ...`
- `/api/usage/today` 加入 cacheRead / cacheWrite 计算（Opus 4 价 in $15 / out $75 / cacheRead $1.5 / cacheWrite $18.75，折扣 0.282）

## [0.3.1] - 2026-05-18
### Added
- 未读 dot 替代完成 banner：`state.unread[sid]` + localStorage 持久化
- SeaTalk 群名手工映射 (`data/group-names.json`)
- channel tag 上色（seatalk 蓝 #4a9eff 等）
- Codex 风格 turn 渲染（用户右蓝气泡 → `› ● 已处理 Xs · N tools` 折叠头 → assistant 纯文本）

### Fixed
- `prettyLabel` 不再覆盖 server label
- Optimistic UI 卡顿：清输入框 + 插 turn 移到 await 前；polling 加 `state.sending` 守卫

## [0.3.0] - 2026-05-17
### Added
- Squid Console 品牌定型，runtime 名（OpenClaw / Codex / Claude Code）作示例保留
- 部署到 systemd `squid-console.service` + cloudflared tunnel + nginx basic auth

## [0.1.0] - 2026-05-15
### Added
- 多 AI session 集中 PWA console
- 后端聚合 OpenClaw 多 session 状态
