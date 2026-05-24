# Whysper Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/),
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.6.28] - 2026-05-24
### Added
- 账本去重：同 merchant + 同 amount + 24h 内 → 后一条标记 duplicate_of，不创建新 ledger_entry
- 「历」候选区前端去重：同 title 前 8 字 + 同日同小时 → 只显 1 条
- 历史清理：去除已有重复账目和重复事件

## [0.6.27] - 2026-05-24
### Changed
- 风景/无信息截图：AI 识别完全无内容时直接删除 entry + 删图，不再产生「（空条目）」垃圾
- 历史清理：删除所有 final_text/title/summary/events/ledger 全空的 entry

## [0.6.26] - 2026-05-24
### Changed
- AI prompt 加入模糊时间推断规则（今天/明天/后天/本周X/下周X/这周末），不再因为"模糊"丢弃事件
- 历史回扫：空条目（final_text/title 都空）kind 强制改回「其它」，修复 7 条种草误标

## [0.6.24] - 2026-05-24
### Added
- 「理」每条加来源 badge：录音 / 截图
- inline 删除确认：点 × 变「删除?」红字 2.2s 倒计时，再点执行（替换浏览器 confirm）
- 「立刻整理今天」按钮 busy/done/fail 状态 + 动态 ...
- 「历」未来事件 >12 条折叠，「另 N 件 ∨」按钮展开/收起
- chip 按下 translateY(1px) 微反馈
### Fixed
- iOS input 焦点缩放（全局 font-size:16px）
- 账页 hero 数字小屏溢出（<360px 改 34px）

## [0.6.23] - 2026-05-24
### Changed
- 账页筛选改 3 个 dropdown（时间/类别/排序），点开浮层选择
- 切 tab 自动 reset 账页筛选状态
- 「理」kind chip 点击切换无需 refetch，~200ms 延迟消除（loadList 加内存缓存 __listCache）

## [0.6.17] - 2026-05-24
### Changed
- 账本页彻底单色（方案 A）：删除 12 个 category 的紫橙蓝粉绿色条
- row 左侧色条全隐藏，类别只靠文字 + 点阵 icon 区分
- 全站只保留 1 个 accent：Nothing Red (var(--red))

## [0.6.15] - 2026-05-23
### Changed
- 全站按钮 token 化：`.btn-del`（删除/忽略） + `.btn-cal`（加日历，含 compact/block 变体）
- 删除 5 个 legacy class，HTML 引用全部迁移到新 class
- 「账单」删除已有二次确认，与「理」对齐
- .tag-more 改成 dashed 描边 chip，与 .tag 对齐

## [0.6.13] - 2026-05-23
### Added
- 统一交互：「理」row 右上角 × 删除按钮（与「账」一致）
- 「历」未来事件 candidate 加「忽略」× 按钮
- 点击「加」或「忽略」后调用 dismiss API，候选区不再重复出现
- backend: POST /api/entries/{id}/events/{idx}/dismiss
### Fixed
- 加日历后候选区仍显示同条事件的 bug

## [0.6.12] - 2026-05-23
### Changed
- 「理」tag cloud 改成固定 8 类（工具/种草/灵感/文章/教程/想法/待办/其它），AI 不再自由发挥
- entries.meta 加 kind 字段，AI prompt 强制从 8 个枚举里选 1 个
- events 严管：一句聊天最多 1 个 event，禁止派生「提前确认」类提醒；模糊时间用 09:00 兜底不编造
- 历史回扫：账单类 entry 清掉 route knowledge；按 final_text/tags 推断 kind

## [0.6.11] - 2026-05-23
### Changed
- 「理」主页卡片不再展示截图（加载失败的图标也不出），所有图统一进详情页才看
- 「理」过滤收紧：只要有 ledger_candidate 就强制跳过（不再尊重旧 route knowledge）
- tag cloud 高频 (≥2) 默认显示，低频折叠 +N 展开

## [0.6.10] - 2026-05-23
### Changed
- paid_at 兜底：AI 抽不到消费时间时，回退用截图 entry 的 created_at (UTC+8 ISO)

## [0.6.9] - 2026-05-23
### Changed
- 账单列表不再显示截图缩略图，icon 位回到点阵 SVG；点击行进 entry 详情看原图

## [0.6.8] - 2026-05-23
### Changed
- 账单时间严格用消费时间（paid_at），AI 找不到就留空，不再回退到截图时间
- 前端账单 row 显示完整 YYYY-MM-DD HH:MM；找不到显示「时间未知」

## [0.6.7] - 2026-05-23
### Changed
- 账单不再需要手动确认：AI 抽出的账单数据**直接进 ledger_entries**，candidate 表只保留作历史/反悔通道
- 同一 source_entry 多次更新同一条 entry（不重复创建）

## [0.6.6] - 2026-05-23
### Changed
- AI prompt 严格区分日历事件 vs 信息提醒：发货/物流/优惠券/退货/退款/抢购等不再进 events
- 账本去掉「导出 / 刷新」按钮，干净
- 账本 candidate 卡片顶部显示原始截图，点击放大
- 账本已入账 row 用截图缩略替代点阵 icon，整行可点开看原 entry

## [0.6.5] - 2026-05-23
### Changed
- 后端 VISION_PROMPT 升级：明确 route 多值（bill/calendar/knowledge），混合截图双落地
- 后端 organize prompt 升级：综合 entries + 当日账单 + 未来事件，生成 100-150 字叙述话
- 「历」tab 顶部新增「未来事件」候选区，所有未来 events 集中展示 + 加日历按钮


## [0.6.4] - 2026-05-23
### Changed
- 「理」tab 路由过滤：
  - 录音和无图文本 → 「理」
  - 纯账单截图（只 ledger 无 knowledge）→ 跳过（走「账」）
  - 纯日历截图（只 events 无 knowledge）→ 跳过（走「历」）
  - 混合类型（带 knowledge 或同时有多 route）→ 仍在「理」
- 单卡片 tag 最多 3 个，余数 +N 显示


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
