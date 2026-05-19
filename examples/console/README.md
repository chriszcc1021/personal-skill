# Squid Console

> 🦑 多项目多线程并行的浏览器 AI Agent 控制台 — 多触手、快进、不袭击其它 session。
> 5 分钟在自己机器跑起来，远程通过 cloudflared 隧道访问。

![Codex-style turn rendering](docs/screenshot.png)

## 它能做什么

- **多项目 × 多线程并行管理**：把若干 session 归到一个项目（带 system prompt + cwd 默认值），左侧像 IDE 文件树一样切换
- **Codex 风格对话渲染**：用户消息右侧蓝气泡 → `● 已处理 Xs · N tools ›` 折叠分隔条 → assistant 纯文本
- **多 channel 来源标识**：seatalk / telegram / discord / signal / whatsapp / slack 上不同颜色 tag，一眼看出某条消息从哪来
- **运行状态 + 完成通知**：sidebar 实时 ● 蓝点脉冲（running）/ ● 橙点（完成未读）/ ○ 灰圈（idle），完成时浏览器系统通知 + 880Hz 短提示音
- **token + 估算花费**：当日总 token，按 Garena gateway 0.282 折扣换算 USD
- **黏在哪里就发到哪里**：底部输入框直接调 `openclaw agent --session-id <sid>`，发往同一个 session 上下文
- **发图友好（PC + 移动端）**：输入框左侧 `+` 调原生 file picker（移动端给「相册/拍照/文件」三选一），PC 仍可 Cmd/Ctrl+V 直接粘贴截图
- **消息可排队 + 一键 STOP**：agent 跑着也能继续发，自动入队按序执行；STOP 按钮挪到输入框旁，运行时才显形，停的只是当前 turn 不清队列；右下角 `+N queued` 一键清空

## 架构

```
浏览器 ──HTTPS──> nginx ──/console/──> cloudflared tunnel ──> 本机 127.0.0.1:8088
                                                                  │
                                                                  ▼
                                                          backend/server.py
                                                          (stdlib http.server)
                                                                  │
                                                          ┌──────┴──────┐
                                                          ▼             ▼
                                       读 ~/.openclaw/agents/main/   subprocess
                                       sessions/*.jsonl              openclaw agent
                                       (sessions.json + 增量行)       (--session-id)
```

- **前端**：单文件 `frontend/index.html`，vanilla JS + 极简 CSS token 体系，无构建链
- **后端**：纯 stdlib，无依赖，端口 8088
- **存储**：会话靠 jsonl（OpenClaw 原生格式），项目/别名/已读 元数据写在 `backend/meta/`
- **流式**：SSE → 轮询 fallback，2s 轮询不会冲掉 optimistic turn

## 关键设计决策

1. **不接 OpenClaw gateway WS API** — 直接读 jsonl 比 RPC 简单，唯一代价是 token 余额查不到
2. **subprocess 调 CLI 发消息** — 每次 1-2s 启动开销，但保证和官方一致的注入逻辑
3. **项目级 prompt + cwd 用 prompt 注入** — agent 物理 cwd 不能改，所以首次完整注入 prompt+cwd 提示，后续仅 `[cwd: xxx]` 轻量提醒
4. **群名靠手工映射表** — IM 平台扩展拿不到群标题，`data/group-names.json` 让用户手动补一行就好
5. **未读 dot 替代右上角 banner** — 完成通知挂在线程上更符合 IM/邮箱直觉，localStorage 跨刷新持久
6. **字号阶梯严格 token 化** — `--fs-xs/sm/md/lg/xl = 11/12/13/14/15`，禁止裸 px（JS 模板内联例外）

## 快速跑起来

### 前置
- Linux + Python 3.10+
- 装好 `openclaw` CLI，确保 `~/.openclaw/agents/main/sessions/sessions.json` 存在
- （可选）cloudflared，做外网访问

### 本地

```bash
cd backend
python3 server.py
# 浏览器开 http://127.0.0.1:8088/console/
```

### systemd + cloudflared

```bash
# 1. 装 service（按需改用户/路径）
cp squid-console.service.example /etc/systemd/system/squid-console.service
cp squid-console-tunnel.service.example /etc/systemd/system/squid-console-tunnel.service
systemctl daemon-reload
systemctl enable --now squid-console squid-console-tunnel

# 2. 配 nginx 反代 /console/ → http://127.0.0.1:8088
# 3. cloudflared 给一个 tryclouflare URL 或自定义域
```

## 群名映射

`data/group-names.json` 是 chat_id → 群名的手工映射，因为大部分 IM extension（特别是 SeaTalk）不缓存群标题：

```json
{
  "otmymdm5otmynze3": "共享牛子",
  "ntk2mzi4nd...": "项目讨论群"
}
```

不映射也能用，会显示 `群 · <hash缩写>`。

## 已知限制

- token 余额需要 voyager OAuth，目前只显示本地估算用量
- 无并发用户隔离 — 单人本地用没问题，多人共用同一 backend 会互看 session
- 没有权限模型 — 谁有 URL 谁就能发消息，远程暴露务必加 nginx basic auth 或 cloudflare access

## 目录结构

```
backend/
  server.py              # 主入口，stdlib http.server，~900 lines
  meta/                  # 运行时元数据（gitignore）
    projects.json        # 项目-session 映射 + 项目级 prompt/cwd
    session-meta.json    # session 别名、置顶、归档状态
frontend/
  index.html             # 单文件 UI
data/
  group-names.json       # 群名手工映射
squid-console.service.example
squid-console-tunnel.service.example
```

## 如何复刻

如果你也想给自己的 agent 装个类似的 IM 控制台，本目录就是完整可参考的实现，配合根目录 [`docs/console-skill.md`](../../skills/squid-console-skill/SKILL.md) 看方法论。

核心理念：**会话 = 文件**（jsonl 一行一 entry）+ **CLI = 唯一写入口**，前端只是把这两者编排好。后端 ~900 行，前端 ~1400 行，没有数据库、没有 ORM、没有依赖。
