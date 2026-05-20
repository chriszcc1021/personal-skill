# Whysper Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/),
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.2] - 2026-05-20
### Fixed
- iOS 点「加日历」按钮跳空白页：.ics 响应改 `Content-Disposition: inline`，让 iOS Safari 触发原生「添加到日历」预览
- whysper-api 之前跑在手动 nohup 老进程没加载 systemd env，导致 AI key 为空、视觉抽取永远静默失败 → 切回 systemd 启动

### Added
- `GET /api/entries/{id}/event` 端点：返回扁平事件结构 `{has_event, title, start_iso, end_iso, location, notes}`，给 iOS 快捷指令判断该截图是否触发日历弹窗
- 前端列表卡片自动挂红色「📅 加日历」按钮（仅当 entry 有 `events.start_iso` 时显示）
- 新 entry 抽出 events 时，列表底部自动弹 sheet 提示加日历，可跳过
- Service Worker bump 到 v3，激活时清旧 cache

## [0.4.1] - 2026-05-19
### Added
- iOS 快捷指令 7 步流程：Action Button 长按 → 截屏 → POST 上传 → AI 视觉抽取 → 自动加日历

## [0.4.0] - 2026-05-18
### Added
- 图片视觉抽取：上传截图后 AI 抽出 title / summary / events / tasks / codes / key_points
- `/api/organize` 端点：日常 batch organize
- ICS 导出：`/api/entries/{id}/ics`

## [0.3.0] - 2026-05-17
### Added
- 整体重构：FastAPI + sqlite + PWA + Whisper STT + Claude 整理
- 部署 ubuntu@43.134.32.223 systemd `whysper-api`，数据 `/var/whysper-data/`
- 访问 https://broadway-aim-discuss-occasions.trycloudflare.com/whysper/

## [0.1.0] - 2026-05-16
### Added
- 启用版本管理（VERSION + CHANGELOG）
- 初始 voice notes 原型
