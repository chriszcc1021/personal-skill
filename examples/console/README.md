# OpenClaw Console

简洁多项目并行的 Web UI for OpenClaw — 浏览/发消息/看 token 用量。

## 特性
- 左侧 session 列表（按主要/线程/子代理/定时/全部分类），每个 session 显示最近一条人话作为 hint
- 右侧聊天历史（user/assistant + tool calls）
- 底部输入框，发消息走 `openclaw agent --session-id ...`
- 顶部当日 token + 估算花费（Garena gateway 折扣 0.282 × Anthropic list）
- 暗/亮主题切换（跟系统默认）
- 手机端 sidebar 抽屉

## 架构
- backend：纯 stdlib `http.server`，端口 8088
- frontend：单文件 HTML + vanilla JS，无构建
- 不接 gateway WS API，直接读 `~/.openclaw/agents/main/sessions/*.jsonl`
- 发消息：subprocess 调用 `openclaw agent --session-id <sid> --message <msg> --json`

## 部署
1. backend 跑在 agent 同主机（要访问 sessions 目录 + openclaw CLI）
2. 反向 SSH 隧道 → 外网 nginx 反代到 `/console/`
3. 见 `systemd/openclaw-console.service` 和 `systemd/openclaw-console-tunnel.service`

## 已知
- token 余额需要 voyager OAuth，目前只显示本地估算用量
- 没接 SSE 流式，回复一次性出
- 发送通过 subprocess CLI，每次有 1-2s 启动开销
