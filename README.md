# Personal Skill Library

张鱼哥的个人知识库，存放可复用的 AI Skills 和实战案例。

## 📁 目录结构

```
.
├── skills/                    # 可复用的 AgentSkills
│   ├── product-encyclopedia/  # 产品对比页生成 skill
│   ├── project-contribution-report/  # 仓库贡献画像 skill
│   └── pitch-skill/           # 数据型 pitch / 商业机会 deck skill
└── examples/                  # 实战案例
    ├── appliance-guide/       # 家电选购指南（含登山包）
    └── console/               # Squid Console — agent 多项目控制台
```

## 🧰 Skills

### product-encyclopedia
生成单文件 HTML 产品对比页（产品百科 / 选购指南）。

**用途：**
- 跨品牌/型号产品对比，含规格与价格
- 选购指南或决策工具
- 交互式产品目录
- "哪款 X 值得买" 决策页

**特点：**
- 单文件 HTML，可通过任意渠道分享
- Apple 风格设计，黑白章节交替节奏
- 移动端响应式
- 交互式筛选 / 排序 / 对比
- 反 AI-slop 设计准则

详见 [`skills/product-encyclopedia/SKILL.md`](skills/product-encyclopedia/SKILL.md)。

### project-contribution-report
仓库贡献画像报告（Nothing-Design 风格，贝叶斯加权评分）。

**用途：**
- 月度/季度团队回顾，"谁做了什么、做得怎么样" 的客观画像
- 避免“commit 多 = 价值高”的错误结论
- 跨同事产出对比（主笔 skills / knowledge / tooling / raw 4 桶拆开）

**特点：**
- 5 类加权评分 + 贝叶斯先验修正（prior_n=5, prior_avg=71）
- OLED 黑底 + Doto 点阵字体，红色仅作 interrupt
- 6 张人物卡，5 指标 + verdict 带量化亮点

详见 [`skills/project-contribution-report/SKILL.md`](skills/project-contribution-report/SKILL.md)。

### pitch-skill
数据型 pitch / 商业机会 deck 构建方法论。

**用途：**
- 市场机会 pitch、发行判断、投资/立项 deck
- 游戏海外发行预测、下载/RPD/收入模型拆解
- Sensor Tower / Excel / PnL / 竞品资料整合
- 把浏览器批注、研究材料和数字模型沉淀成可讲述的 deck

**特点：**
- 先定义决策问题，再拆模型变量
- 竞品只校准一个变量，避免过度类比
- 区分下载市场、RPD市场、社交传播市场
- 支持保守/乐观两档场景和 PnL 对账
- 强制版本快照和 changelist，方便回退

详见 [`skills/pitch-skill/SKILL.md`](skills/pitch-skill/SKILL.md)。

### squid-console-skill
为 CLI 驱动的 agent runtime（OpenClaw / Codex / Claude Code）打造 IM 风格浏览器控制台的方法论。

**用途：**
- 多项目 / 多线程并行管理你的 agent 会话
- 给只能本地跑的 agent 加上远程/手机访问能力
- 在不引入 React/Vue/DB 的前提下实现专业控制台

**特点：**
- Codex 风格 turn 渲染（右气泡 + 折叠头 + 纯文本回复）
- 多 channel 来源色签 + 未读 dot 状态机
- 纯 stdlib 后端（~900 行） + 单文件 HTML 前端（~1500 行）
- jsonl 作为所有持久化源，元数据外挂 JSON
- 配 cloudflared tunnel + nginx 远程访问

详见 [`skills/squid-console-skill/SKILL.md`](skills/squid-console-skill/SKILL.md)，参考实现在 [`examples/console/`](examples/console)。

## 📚 Examples

### console
Squid Console — 多项目多线程并行的浏览器 agent 控制台。

- Codex 风格对话渲染
- IM 来源 channel tag（seatalk蓝 / telegram青 / discord紫 ...）
- 运行/未读/已读 三态状态机
- 纯 stdlib + 单文件 HTML + cloudflared

详见 [`examples/console/README.md`](examples/console/README.md)。

### appliance-guide
家电选购指南门户网站，部署于 `http://43.134.32.223:8080/appliance-guide/`。

**包含 7 个品类：**
- 扫地机器人（拖布对比）
- 洗烘一体机
- 洗碗机
- 微蒸烤一体机
- 电陶炉
- 内衣洗衣机
- 户外登山包（41 款型号，12 个品牌）

**技术栈：**
- 纯静态 HTML/CSS/JS（无构建工具）
- Apple Design 风格
- 服务器端图片本地化（解决防盗链）

## 🚀 如何使用

把 `skills/` 下的目录复制到 OpenClaw skill 目录即可调用：

```bash
cp -r skills/product-encyclopedia ~/.openclaw/workspace/skills/
```

## 📝 维护

- 持续追加新 skill 到 `skills/`
- 实战项目沉淀到 `examples/`，提供给后续 skill 优化的参考
