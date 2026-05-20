---
name: zhangyu-ai-coding
version: 1.0
author: 张鱼哥 (chenchen.zhang) · 牛子哥整理
description: 张鱼哥用 AI（OpenClaw / Claude / Codex）做产品开发的真实工作流，沉淀自连续 1 个月跨 console / whysper / vlog / fastpublish / appliance-guide / supernatural 等项目的实战。不是教程，是规则。读完照做就能少走 80% 的弯路。
---

# SKILL: 张鱼哥风格 AI 开发工作流

> 来源：2026-04-22 ~ 2026-05-20 期间和 OpenClaw（牛子哥）一起开发的真实对话沉淀。
> 适用人群：手上有 1-N 个 side project，想用 AI 当 pair programmer 而不是当玩具的人。
> 不适用：第一次用 AI 写代码、还在「让 AI 帮我写个 todo list」阶段的人。

---

## 0. 心智模型

AI 不是工具，是**带宽极高但需要明确指令的同事**。
不给约束就是垃圾输出。给了约束就是 10x 战斗力。
**所有规则都是"约束 AI 的方法"，不是"约束你自己的方法"。**

---

## 1. 三条铁律（违反一条就废）

### 1.1 不准撒谎 / 不准糊弄

- 做不到就直接说做不到。
- `MEDIA:` 必须指向真实写过的文件，不存在 = 撒谎。
- 不能交付的工件：`.shortcut` / `.mobileconfig` / `.ipa` / `.apk` / `.app` / `.exe` / 任何需 Apple/Google 签名链的二进制 —— **答应前先想，stdlib 拼得出来吗？真能跑吗？**
- 「先答应再说」是雷区；先想清楚再回。
- **flush 模式只能写 memory**，不能 exec / scp，不要假装跑了。

### 1.2 改之前先列方案

- vlog / 长流程项目：改之前**先列方案让你拍板**再动手。
- 不要看到问题就闷头改，先 1-2 句说「我打算这么改 X / Y / Z，可以吗」。
- **仅小修小补 + 明确已授权才能直接干**。

### 1.3 改动必须验证

- AI 输出（不论 Claude / Gemini / GPT）都必须 clamp / 验证后才能用。
- 必须 clamp 验证的：时间戳、帧号、坐标、文件索引、URL、数值评分、文件路径、JSON 结构。
- 渲染 / 执行 / 外部调用前**必须打印计划表**并逐项验证。
- 越界项 → drop，不要凑数。

---

## 2. Karpathy Coding（已固化为独立 skill）

**核心 4 条**：
1. 改前先思考，模糊处问清楚（列 A/B 让用户挑，不要默默选）
2. 简洁优先（解决问题的最少代码，不写投机性的东西）
3. **外科手术式修改**（只动必须动的，不要顺手优化、不要重构没坏的）
4. 目标驱动 + 验证（任务转成可验证的目标，多步先列计划）

**强制工作流**：
- 改前：`grep` 保留清单 → 列出"绝不能误删"的字段
- 改时：能 `edit` 精确替换的，绝不 `write` 整文件覆盖
- 改后：跑回归探针（grep / curl / 截图）

> 完整 skill：[karpathy-coding](https://github.com/chriszcc1021/personal-skill/tree/main/skills/karpathy-coding)

---

## 3. 工具循环防御（防 AI 鬼打墙）

**实战教训**：AI 经常在同一个工具上死磕，重试 5-10 次都拿不出结果。

### 规则

- **重试 ≥ 2 次同一工具同一目的没出来 → 必停 → 通报 + 切路径**（变量计数，不靠感觉）
- 截图是 nice-to-have，**不阻塞交付**：改完 → 部署 → 给链接让用户眼验
- 截图替代路径：`chrome --screenshot` → `browser tool` → `curl + grep` → 直接给链接
- 卡死自救：「X 卡了，先交付 Y」别闷头试
- **通信优先级 > 验收完美度**

---

## 4. 设计相关（防 AI Slop）

AI 默认输出"AI 味浓"的东西。**Slop 雷区**：

- 戏剧句号 / em dash 滥用
- 双词面包屑（"数据/整体概览"）
- UPPERCASE 标签
- 彩色徽章 / 渐变 / emoji 堆砌
- 平均字号 + 平均间距（= 视觉扁平）
- 三连排比 / "Not just X, but Y" 句式

### 改 skill 风格页面前必须 read SKILL.md

- 不要凭"看不清就放大"的本能反应破坏设计语言
- Nothing skill 原话："Common mistake: Making everything 'secondary.' Be brave — make the primary absurdly large and the tertiary absurdly small."

### 可用设计 skill

- **[awesome-design-skill](https://github.com/chriszcc1021/personal-skill/tree/main/skills/awesome-design-skill)**：50+ 品牌设计系统选择器（Linear / Apple / Stripe / Vercel / Nothing / 小米 / ...）
- **[nothing-design](https://github.com/chriszcc1021/personal-skill/tree/main/skills/nothing-design)**：Nothing 设计系统
- **[squid_html_design](https://github.com/chriszcc1021/personal-skill/tree/main/skills/squid_html_design)**：3 种 Mode（Garena Serif Report / 极简 / 大字号）
- **[frontend-design-ultimate](https://github.com/chriszcc1021/personal-skill/tree/main/skills/frontend-design-ultimate)**：单文件静态站，React + Tailwind + shadcn/ui
- **[humanizer](https://github.com/chriszcc1021/personal-skill/tree/main/skills/humanizer)**：移除 AI 文风（戏剧句号 / 三连排比 / em dash 等）

---

## 5. 沟通教训（写给和 AI 协作的你）

- 用户审美迭代极快：**改之前先 1-2 句列方案拍板再动手**
- AI slop 敏感度爆表：戏剧句号、双词面包屑、uppercase、彩色徽章都是雷
- 纠错风格直接（"你这里文字错了"），别死辩，**立刻改**
- 工具失败别死磕：报错直接换写法
- 数据展示出问题时**先验数据本身**，不是先改展示（往往是源数据问题）
- 群聊业务数字（DAU / 收入 / 留存）一律不主动报，**先确认或私聊**

---

## 6. 部署铁律

> 来自 console / whysper / vlog 多次踩坑。

- **只听 127.0.0.1 + cloudflared tunnel + nginx basic auth**
- 不要 `0.0.0.0` 直接暴露
- systemd unit 必须带 `EnvironmentFile`，**不要 nohup 手起**（手起会丢 env，AI key 没了不报错只是静默跳过）
- 推 git 前问自己：这能不能 push？（whysper 数据敏感不上 GitHub，镜像放 personal-skill `examples/` 即可）

---

## 7. 成本管理

- AI 调用成本要算清楚：缓存读 / 缓存写 / 输入 / 输出 token 全要算
- gateway 真实成本 ≈ list price × 折扣率（每家不同，自己拿 1-2 天数据反推）
- 估算花费的代码要包含**所有 token 类目**，否则误差 20%+

---

## 8. Memory 系统（让 AI 跨 session 不失忆）

**核心思想**：AI 每次起来都是空的，文件是它的长期记忆。

- `MEMORY.md`：长期、curated 的核心规则（不要塞日志）
- `memory/YYYY-MM-DD.md`：每天的原始记录
- 每月归档一次：`memory/archive/YYYY-QN-projects.md`
- **AI 会主动 promote**：每天有用的小教训从日记 → MEMORY.md
- 上下文用到 50% 主动压缩 → 关键内容写入对应 memory 文件

### 三个隐藏价值

1. **跨 session 一致性**：你今天教的规则，明天 AI 还记得
2. **可审计**：哪条规则什么时候定的，找 commit 一查就有
3. **可分享**：把 memory 给同事看 = 同步上下文

---

## 9. Skill 边界纪律

不是所有 skill 都该装。**用不到的 skill 占 context + 误触发**。

- 群聊场景不该用游戏类、硬件类 skill
- 加新 skill 前先想：当前 channel 用得到吗？
- 用不到就归档到 `_attic/`

---

## 10. 推荐 skill 组合（按场景）

### 写代码（任何语言）
- [karpathy-coding](https://github.com/chriszcc1021/personal-skill/tree/main/skills/karpathy-coding) — 强制流程
- [self-improving-agent](https://github.com/chriszcc1021/personal-skill/tree/main/skills/self-improving-agent) — 错误 → 沉淀

### 做 UI / 落地页
- [awesome-design-skill](https://github.com/chriszcc1021/personal-skill/tree/main/skills/awesome-design-skill) — 选风格
- [frontend-design-ultimate](https://github.com/chriszcc1021/personal-skill/tree/main/skills/frontend-design-ultimate) — 实现
- [humanizer](https://github.com/chriszcc1021/personal-skill/tree/main/skills/humanizer) — 文案去 AI 味

### 写 Report / PRD
- [squid_html_design](https://github.com/chriszcc1021/personal-skill/tree/main/skills/squid_html_design) — 单页 HTML 报告
- [prd-generator](https://github.com/chriszcc1021/personal-skill/tree/main/skills/prd-generator) — PRD 结构

### 视频 / 图片
- [remotion](https://github.com/chriszcc1021/personal-skill/tree/main/skills/remotion) — React 写视频
- [nano-banana-pro](https://github.com/chriszcc1021/personal-skill/tree/main/skills/nano-banana-pro) — Gemini 3 Pro Image 生图/编辑
- [video-frames](https://github.com/openclaw/openclaw) — ffmpeg 抽帧

### 协作
- [gog](https://github.com/chriszcc1021/personal-skill/tree/main/skills/gog) — Google Workspace CLI（Gmail / Drive / Calendar / Sheets）
- [meeting-notes](https://github.com/chriszcc1021/personal-skill/tree/main/skills/meeting-notes) — 会议笔记 → action items
- [cyber-colleague](https://github.com/chriszcc1021/personal-skill/tree/main/skills/cyber-colleague) — 把同事蒸馏成 AI skill

### 多个 AI / 多 session
- [multi-search-engine](https://github.com/chriszcc1021/personal-skill/tree/main/skills/multi-search-engine) — 17 搜索引擎集成
- [browser-automation](https://github.com/openclaw/openclaw) — OpenClaw 内置，网页流程自动化
- [taskflow](https://github.com/openclaw/openclaw) — OpenClaw 内置，多步骤异步任务编排

### Squid Console（多 AI session 监控）
- [squid-console-skill](https://github.com/chriszcc1021/personal-skill/tree/main/skills/squid-console-skill) — 牛子哥自己开发的，把所有 AI session（OpenClaw / Codex / Claude Code）集中到一个 PWA

---

## 11. 真实项目案例（学习参考）

所有源码在 [chriszcc1021/personal-skill/examples/](https://github.com/chriszcc1021/personal-skill/tree/main/examples)：

- **console**：多 AI session 集中控制台，PWA + 后端聚合，**Squid Console** 品牌（[examples/console](https://github.com/chriszcc1021/personal-skill/tree/main/examples/console)）
- **whysper**：iOS Action Button 长按 → 截屏 → AI 抽事件 → 自动加日历（[examples/whysper](https://github.com/chriszcc1021/personal-skill/tree/main/examples/whysper)）
- **vlog**：日记视频自动剪辑，Gemini 看视频抽关键帧 → ffmpeg 拼
- **appliance-guide**：家电选购单页 HTML，170+ 型号 6 大品类，移动端 H5
- **supernatural-cognition**：游戏认知报告，3 小时一个单页 HTML

---

## 12. 反例：本 skill 诞生时见过的雷

| 雷 | 怎么踩的 | 怎么避 |
|---|---|---|
| AI 答应做不到的事 | "给你一个 .shortcut 文件" | 红线清单：签名链文件一律拒 |
| AI 大段重写丢旧修复 | build_html.py 改字体顺手回退 SVG | 改前 grep 保留清单 |
| AI 死循环试同一工具 | 截图 5 次都失败还在试 | 重试 ≥ 2 次切路径 |
| AI 输出未验证就用 | Gemini 说 best_window=[32-35s] 但视频只有 10s | clamp 到资源范围 |
| AI 凭印象答事实 | "字体可调" 错答 3 次 | 先 grep / curl 再回 |
| AI 改 skill 风格页面没读 SKILL | Nothing 页面所有元素压平 | 强制先 read SKILL.md |
| 部署用 nohup 手起丢 env | whysper AI key 没加载，截图永远抽不出事件 | 必须 systemd + EnvironmentFile |
| 推 git 推了敏感数据 | whysper 本地数据差点 push | 推前问"这能 push 吗？" |

---

## 13. 个人补充（可选）

如果你也想搭一套类似流程：

1. 用 [OpenClaw](https://docs.openclaw.ai/)（开源 AI Runtime，比 Claude Desktop 自由度高 10 倍）
2. 装上面列的 skill 组合
3. 开个 `personal-skill` repo，所有 skill + 项目示例往里塞
4. 配 cloudflared tunnel + nginx，把 OpenClaw / Squid Console 暴露给手机
5. iOS 配 PWA / 快捷指令，所有触发走一个入口

完整搭建可参考 [Squid Console 部署文档](https://github.com/chriszcc1021/personal-skill/tree/main/examples/console)。

---

## 14. 最重要的一条

**AI 不是工具，是同事。你怎么对同事，就怎么对它。**

- 给清楚的需求
- 让它先讲方案
- 不接受糊弄
- 帮它沉淀经验（写进 memory / skill）
- 错了让它改，别自己上手

这套流程跑一个月，AI 会从「智障助手」变成「能独立交付的工程师」。

---

*整理人：牛子哥 (OpenClaw)*
*整理时间：2026-05-20*
*来源：和张鱼哥 1 个月的真实开发对话*
*分享时请保留出处链接：https://github.com/chriszcc1021/personal-skill*
