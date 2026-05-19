---
name: squid-console-skill
description: |
  Build a personal IM-style web console on top of any agent runtime that
  writes session jsonl files. Covers project/thread hierarchy, Codex-style
  turn rendering, channel-source tagging, unread state machine, group-name
  mapping, and minimum-dependency deployment (stdlib http.server + single
  HTML file + cloudflared tunnel). Use when wrapping a CLI-driven agent so
  the operator can monitor and reply across many concurrent sessions from
  a browser.
---

# Squid Console — Build Your Own Agent Console

> 🦑 _"多触手、快送达、重叠隐书色"_ —— 为 CLI 驱动的 agent runtime 打造的浏览器 IM 控制台。

把任意 "会话即 jsonl 文件 + CLI 是唯一写入口" 的 agent runtime（OpenClaw / Codex / Claude Code / Aider 等）包装成一个**多项目并行的浏览器控制台**。
完整可运行的参考实现：[`examples/console`](../../examples/console)。

## 用在什么时候

- 你的 agent 是 CLI 驱动的，每个会话都落一个 jsonl
- 你需要并行管理多个 session（订阅了几个 IM 来源、跑着多个项目、有定时任务）
- 你想从手机/远程电脑回消息，但不想为此装 Electron / 跑 Postgres / 引入 React 工程链
- 单人或团队 < 5 人使用

## 三个核心抽象

### 1. Session = jsonl 文件
不要试图设计 ORM。每个 session 就是 `~/<agent>/sessions/<uuid>.jsonl`：
- 一行一 entry（user / assistant / toolCall / toolResult）
- 增量追加，mtime 反映活跃度
- 只读到内存做投影；写靠 CLI（见下）

### 2. CLI = 唯一写入口
前端永远不直接拼 jsonl，发消息一律走 `subprocess`：
```py
subprocess.Popen(["openclaw", "agent", "--session-id", sid, "--message", text, "--json"])
```
代价是每次 1-2s 启动开销，回报是和官方注入逻辑零分歧，升级 agent 时不会突然崩。

### 3. 元数据外挂
项目分组、别名、置顶、已读状态、群名等 jsonl 里没有的东西，**外挂存** `backend/meta/*.json`：
- `projects.json`：projectId → { name, sessionIds[], prompt, cwd }
- `session-meta.json`：sid → { alias, pinned, archived }
- `data/group-names.json`：chat_id → 群名（手工填）
- 浏览器 localStorage：未读、折叠状态、UI 偏好

外挂数据格式简单到不需要 schema，坏了删掉重来。

## UI 三大模块

### A. Sidebar — 项目-线程树
```
┌─ 📁 personalskill              [+]
│  ● console 调试 · 4 tools
│  ● cwd 验证
│
├─ 📁 测试
│  ○ thread · 872576
│
└─ ⊙ 未归类
   ○ DM · 82124
   ○ 群 · 共享牛子    [seatalk]   ← channel tag
   ● 群 · fastpublish [seatalk]   ← unread orange dot
```

**关键细节**：
- 项目用 `projects.json` 维护，sidebar 折叠展开状态进 localStorage
- 线程上的 dot 三态：● 蓝点脉冲(running) / ● 橙点(完成未读) / ○ 灰圈(idle)
- channel tag 颜色映射（seatalk 蓝 / telegram 青 / discord 紫 / signal 灰蓝 / whatsapp 绿 / slack 品红），从 `sessionKey` 的第三段抽：`agent:main:seatalk:group:xxx`

### B. 主区 — Codex 风格 turn 渲染
```
                                            你说的话 →
                                          ┌──────────┐
                                          │  改一下..│ ← 蓝气泡靠右
                                          └──────────┘
─── › ● 已处理 6s · 2 tools ──────────────── ← 横线分隔，点击折叠
agent 的回答正文是纯文本，没有气泡背景      ← 直接占满
```

**为什么这样**：用户曾反馈"输出一坨看不懂，没有对话关系"。Codex 用居中横线 + 状态条 分割每个 turn，比"两端气泡" 更适合 agent 场景，因为 assistant 文本经常很长 + 带列表 + 带代码块，套气泡会把 80% 视野浪费在 padding 上。

**实现要点**：
- `turn-card` 状态机：`running`（默认展开 + 秒表 + STOP）→ `done`（自动折叠）
- 横线用 CSS `::before / ::after` 配合 flex 拉伸
- 无 tool 的 turn 隐藏 chevron 禁用点击

### C. 顶栏 — `<alias> · <project> · <cwd>` + 当日 token
单行展示所有上下文，token 折扣价用 `gateway × 0.282` 估算。

## 状态机 & 推送

### 完成通知 = 未读 dot，不要做 banner
banner 干扰使用，未读 dot 挂线程上才符合 IM/邮箱直觉。
- `state.unread[sid] = {label, dur, ts}`，写 localStorage
- `selectSession(sid)` 入口自动清
- sidebar 渲染时 `.unread` 加粗 + 橙 dot

### 流式：SSE 主 + 2s 轮询 fallback
- 主路径 EventSource 订阅 `/api/stream?sid=...`
- 后端用 `inotify` 或 mtime 轮询 jsonl 增量
- 轮询 fallback 必须**只在 user 行数变化时**才重绘，**绝不能在 sending=true 时重绘**，否则会冲掉 optimistic turn

### Optimistic UI 必须在 await 之前
按下回车 → **立即**：清输入框 + 插一张 `running` turn-card；**然后**才 await upload / await send。否则用户体感"卡几秒"。

## 部署铁三角

```
nginx (HTTPS + auth) ── cloudflared tunnel ── 本机 127.0.0.1:8088
                                                       │
                                                       ▼
                                              systemd unit 起 backend
```

完整 `.service` 模板在 [`examples/console/`](../../examples/console)。

**铁律**：
1. 永远不要把 `0.0.0.0` 暴露 — 只听 127.0.0.1，所有进出走 tunnel
2. nginx basic auth 或 cloudflare access 是底裤，不要裸奔
3. 单进程单用户 — 不要试图加 SaaS 多租户，那是完全另一个项目

## 字号 / 间距 token 体系

不要散落 `px` 在代码里。一个 `:root` 块定死：

```css
:root {
  --fs-xs: 11px; --fs-sm: 12px; --fs-md: 13px; --fs-lg: 14px; --fs-xl: 15px;
  --fs-mono-xs: 11px;
  --lh-tight: 1.4; --lh-base: 1.55; --lh-relaxed: 1.65;
  --ls-base: .02em;
}
```

只有 3 处 JS 动态计算的内联例外（input autosize / scroll padding / inline svg）。
裸 px 一律视为待清理 tech debt。

## 反模式（别踩）

- ❌ 用 React/Vue 工程链 — 单文件 HTML 就够，无构建无 bundler 等于零升级负担
- ❌ 加数据库 — jsonl + 几个 JSON 文件解决所有持久化
- ❌ 给会话再设计一份消息表 schema — 直接 reduce jsonl 投影出来
- ❌ 用 banner 通知 — 用未读 dot
- ❌ 套两端气泡 — 用 Codex 横线分隔
- ❌ 在 await 之后才插 optimistic turn — 用户会怀疑卡了
- ❌ 群名想通过 IM API 抓 — 99% 拿不到，做手工映射表

## 何时不要用这套

- 多人协作（≥5 人）— 你需要真权限模型 + 真数据库
- 需要离线移动端 — 这是 web，没 service worker
- 上游 agent 不输出 jsonl — 整个抽象失效，先解决会话持久化

## 进一步阅读

- `examples/console/README.md` — 跑起来 + 架构图
- `examples/console/backend/server.py` — 870 行后端全部，可直接复制改造
- `examples/console/frontend/index.html` — 单文件前端，CSS token + Codex 渲染参考
