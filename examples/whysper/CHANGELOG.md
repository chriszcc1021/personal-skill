# Whysper Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/),
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.1] - 2026-05-21
### Added
- 单次上传总量限制 100MB，避免公开入口被超大文件拖垮。
- 顶栏增加轻量 Action Button 配置图标，点击后显示快捷指令配置说明。

### Changed
- `?tab=ledger` 等 URL 参数会自动切换到底部对应页面。
- iOS 快捷指令说明改为上传后最多轮询 3 次日历时间项，减少 AI 异步处理导致漏加日历。
- Service Worker 升级缓存版本，确保线上前端更新后优先加载新版页面。

## [0.5.0] - 2026-05-21
### Added
- 单一截图入口自动分流：账单进入待确认账本，时间事项进入日历/Todo 提醒，普通截图进入知识整理。
- 账本数据表与 API：待确认账单、确认入账、已入账列表、月度汇总、CSV 导出。
- 前端新增「账」页，支持查看待确认账单、修改识别结果、确认入账、删除误识别。

### Changed
- iOS 快捷指令说明改为一个 Action Button 截图入口，`capture_mode=auto` 由 AI 自动判断去向。
- 截图视觉 prompt 增加消费账单识别字段，同时保留日历/Todo/知识整理字段。

## [0.4.3] - 2026-05-21
### Added
- `calendar_items` 统一时间项：截图里的日程、待办截止时间、码过期时间都能导出到 ICS。
- `GET /api/entries/{id}/calendar-items`，给 iOS 快捷指令轮询分析结果并自动添加日历。
- 条目处理状态字段：`processing_stage` / `processing_status` / `processing_error`。

### Changed
- 「理」页列表卡片显示截图分析中、语音转写中、分析失败、检测到时间项等明确状态。
- 自动加日历弹窗从只识别 events 改为识别全部 calendar items。
- 快捷指令文档补充上传后轮询并添加日程的流程。

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
