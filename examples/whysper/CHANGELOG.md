# Whysper Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/),
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.6.3] - 2026-05-23
### Changed
- 合并 personal-skill 远端 5d4d832 typography 改动
- 3d.html 应用 Doto / Space Grotesk / Space Mono / Noto Sans SC 字体栈
- 与 0.6.0-0.6.2 的 ledger 重设计 + 主页字体合并


## [0.6.2] - 2026-05-22
### Changed
- Nothing-inspired 字体栈：
  - Doto = 点阵/品牌味，仅用于 hero 大数字
  - Space Grotesk = 主 UI/display
  - Space Mono = 数字/标签/时间/状态
  - PingFang SC = 中文 fallback（商家名、洞察文、chip 标签），不被点阵化
- chip active 状态改为实心反色更醒目


## [0.6.1] - 2026-05-22
### Changed
- 流水行去掉「支付方式·类别」啰嗦元信息（类别已被左侧色条 + group 头表达）
- 商家字号 14→16，金额 15→18，更清晰
- Hero 下方加回人话洞察「最大支出是 购物，占 99%」


## [0.6.0] - 2026-05-22
### Changed
- 「账」tab Nothing-style 重设计：
  - Hero 数字（本月支出 46px 大字 + 时间段 label + 笔数）
  - 时间窗口 chip（本月 / 上月 / 近30天 / 全部）
  - 类别 Nothing 点阵 SVG icon（12 类，单色 currentColor）
  - 流水卡片改单行 row（3px 类别色条 + icon + 商家 + 时间·支付方式·类别 + 金额 + ×）
  - 按日期 group + 当日小计
  - 去掉重 stats panel / 候选 panel 默认折叠


## [0.5.5] - 2026-05-22
### Added
- 「账」tab 加按时间 / 按金额排序切换（纯前端排序，不打后端）


## [0.5.4] - 2026-05-22
### Changed
- 「账」tab 切换 category chip 不再重新请求后端，纯前端 filter + 重渲（__ledgerData 全量缓存）
- 加 entry 或确认/删除后才主动 loadLedger，浏览即过滤秒切


## [0.5.3] - 2026-05-21
### Added
- `/api/boot?tab=<tab>` 聚合端点：一次请求拿到 stats + tags + 当前 tab 数据（list/cal/ledger）
- 前端启动改成 `bootPrefetch(initialTab)` 一发命中，loadList/loadCal/loadStorage/loadDaySummary/loadLedger/loadTags 都优先吃 cache
- FastAPI 启用 GZip middleware（≥512B 自动压缩），entries 列表 17KB → ~3KB

### Performance
- 首屏请求数：~8 个 → 1 个 boot + 异步刷新
- entries JSON 体积：~80% 压缩
- SW cache bump `whysper-v9-perf`

## [0.5.2] - 2026-05-21
### Fixed
- 「账」tab 一直「加载中」：`esc()` 在 `c.confidence`（number）上炸 `TypeError: replace is not a function`。`esc()` 改成 `String(s||'').replace(...)`，对所有非字符串都安全
- Service Worker bump 到 v8（whysper-v8-ledger-fix），强制重拉 index.html

## [0.5.1] - 2026-05-20
### Added
- 记账 review-first 流程：`/api/ledger/candidates` + `/api/ledger/entries`，前端「账」tab 显示待确认/已入账
- AI 视觉抽取增加 `ledger` 字段（is_expense / merchant / amount / category / paid_at / payment_method）
- DB 新表 `ledger_candidates` + `ledger_entries`
- entries 加 `capture_mode` 字段（auto / note / ledger）

## [0.5.0] - 2026-05-20
### Added
- `/api/entries/{id}/calendar-items` 端点


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
