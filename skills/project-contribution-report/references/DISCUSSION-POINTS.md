# DISCUSSION-POINTS.md

> 这份文件记录张鱼哥 ↔ 牛子哥在迭代 fastpublish 仓库画像报告过程中的**所有关键决策、踩过的坑、回退过的版本和用户偏好**。
> 目的：未来任何 AI / 工程师二次修改这份报告时**先读这个文件**，避免重复犯错或破坏已经达成的设计共识。
> 维护者：牛子哥（贾维斯）· 最后更新 2026-05-15

---

## 0. 核心约束（先读这一段）

| # | 约束 | 触发场景 |
|---|---|---|
| 1 | **改前必须 `grep` 列保留清单**（验证不会破坏已有改动）| 任何文件编辑 |
| 2 | **用 `edit` 工具精改，禁用 `write` 整文件覆盖** | 改已有文件 |
| 3 | **改后必跑 8+ 项回归探针** | 每次改动后 |
| 4 | **绝不脱离 Nothing Design 调性** | 视觉调整 |
| 5 | **报告必须 100 分制**（不是 25 分制） | 所有分数显示 |
| 6 | **绝不加 emoji**（"AI 味会非常浓"）| 标签、文案、UI |
| 7 | **要"评价"不要"解释"**（含数字 + 褒贬）| 短评、verdict |
| 8 | **不要顺手做**（用户拍板什么就做什么）| 多任务时 |
| 9 | **稳定 URL 用 IP，不用 trycloudflare 临时域名** | 链接给用户时 |
| 10 | **群聊不主动报具体业务数据**（DAU/留存/收入等）| Seatalk 群 |

---

## 1. 设计语言（Nothing Design）

### 必守的对比层次（曾被破坏过一次）

| 维度 | 错误做法 | 正确做法 |
|---|---|---|
| `line-height` | 一刀切 1.6 | display 字 0.85 / body 1.6（**对比即层次**）|
| `letter-spacing` | 一刀切 0.08em | labels 分级 0.06 / 0.08 / 0.12 / 0.14（**间距即层级**）|
| `margin-bottom` | 全压 48px | 关键章节 64-96px（vast 留白）|
| `table padding` | 强制 12×14 | 信息密度要有节奏 |
| `font-size` | 11px 全部拉到 14px | `--label:11px` 是 Nothing 仪表盘 ALL CAPS 标准 |

**Nothing skill 原话**：
> "Common mistake: Making everything 'secondary.' Evenly-sized elements with even spacing = visual flatness. Be brave — make the primary absurdly large and the tertiary absurdly small."

### Doto 字体加载

- CSS 用 `font-family:'Doto'` 必须在 `<link>` Google Fonts URL 里加 `family=Doto:wght@400;700;800;900`
- 浏览器静默 fallback 不会报错 → 必须截图验证或 grep `family=Doto` 命中

### 颜色（仅可用）

- `--accent: #D71921`（红，主色）
- `#0a0a0a` / `#161616` / `#222` / `#444` / `#888` / `#E8E8E8` / `#fff`
- 任何渐变、彩虹色、淡彩底都**违反 Nothing**

---

## 2. 内容分类（CODE 标签被合并）

### 决策：3 类 → SKILL / KNOWLEDGE / TOOL

| 标签 | 颜色类 | 触发条件 |
|---|---|---|
| **SKILL** | `k-skill` 红 | path 含 `/skills/` 或 `SKILL.md` |
| **KNOWLEDGE** | `k-know` 绿 | 其余文档型 |
| **TOOL** | `k-tool` 黄 | path 含 `/tool-stations/` |

**已废弃**：`CODE` / `DOC` 标签 — 因为 tool-station 才是仓库主轴（PRD + 脚本的"原型项目"），CODE 标签会误判。

---

## 3. 评分系统（学到的教训）

### 100 分制（不是 25 分制）

- `total = (structure + reuse + exec + ref_s + fresh) * 4`
- 每个维度 1-5 分，5 维相加 25，× 4 = 100
- **曾犯错**：关键词上线时不小心 `* 4` 翻倍 → 出现 `368/100`，已修

### 贝叶斯先验加权（小样本修正）

公式：`adjusted = (sum + N×prior_avg) / (n + N)`，`N=5, prior_avg=71`

**原因**：Chenchen 主笔 3 个 skill 均分 80，刷出全员第一是统计错觉。修正后 80 → 74（仍为质量第一，但合理）。

**修正后最终评级**：

| 评级 | 人 | 主笔 skill | 修正后质量分 |
|---|---|---|---|
| A | Charles Liu | 15 | 73 |
| A- | Huang Yu | 1 | 70 |
| A- | Pingfan | 8 | 67 |
| A- | Chenchen Zhang | 3 | **74**（质量第一）|
| B | Peicheng Zheng | 2 | 69 |
| C+ | Zhang Yaokuang | 0 | — |

### 评分维度 ≠ 全员均分

- 5 维：`structure / reuse / exec / refs / fresh`
- **"fresh" / "新鲜度"不能用来评判 skill 质量**（用户明确否决）
- 评分公式里仍保留 fresh 维度计算总分，但**关键词标签不展示"新鲜/过期"**

---

## 4. 关键词标签（核心 Top 10 + 低质量 Top 10）

### 决策路径

1. v1：原版只有「零引用」section → **空了**（仓库当前 41 skills 全部 ref ≥ 1）
2. v2：用户建议 → 改成「低质量 Top 10」
3. v3：用户要求加"原因关键词"
4. v4：牛子哥提案带 emoji → **被否**："AI 味会非常浓"
5. v5：去 emoji，但同时不小心引入 `*4` 翻倍 → **分数爆 368/100**
6. v6：修分数 + 标签视觉增强（白色实心好 / 灰边框坏）→ ✅ 终版

### 终版关键词集合

**核心技能「亮点」**（4 个）：
- 高引用（refs ≥ 5）
- 可执行（exec ≥ 4）
- 强结构（structure ≥ 4）
- 高复用（reuse ≥ 4）

**低质量技能「问题」**（5 个）：
- 零引用（refs = 0）
- 薄文档（words < 100）
- 无脚本（exec ≤ 2）
- 结构弱（structure ≤ 2）
- 低复用（reuse ≤ 2）

### 视觉

- 好标签：**白色实心 + 黑字**（高对比）
- 坏标签：**灰边框 + 白字 + 透明底**（弱化）
- 字号 10px，letter-spacing 0.10，等宽字
- `white-space: nowrap` 单行不换行（否则**错层**）

---

## 5. 卡片设计

### 卡片排序

按**综合分**降序（不是 skill 数 / 不是 avg_quality）：

`Charles 663 → Huang Yu 225 → Pingfan 223 → Chenchen 204 → Peicheng 98 → Yaokuang 30`

**曾错过**：用 `sort(skills_authored, avg_quality)` → 用户截图反弹

### Verdict 红框

`padding:14px 18px; background:rgba(215,25,33,0.06); border-left:3px solid var(--accent)`

**曾错过**：被 `write` 整文件覆盖时丢失 → 用户两次回退反弹

### 头像

- **白色 2px 边框**（不是红色 — 用户改过 1 次）
- 96×96 圆形，hover 微缩放 1.06 + 红色光晕
- 6 张图：charles / chenchen / huangyu / peicheng / pingfan / yaokuang
- 路径：`/var/www/fastpublish/avatars/av_<name>.png`

### Tags 标签位置

- **5 项指标下方、亮点上方**（不是卡片底部）
- 移到上面理由：底部容易被滚动忽略

### Bus Factor

- **整行删了**
- 用户反馈："容易被读成评价个人而不是评估风险结构，有点冒犯"
- 信息（"skill 体系的单点支柱"）已在短评里表达

### 短评（verdict）风格

- ❌ 不写："这个 skill 干什么的"（解释）
- ✅ 要写："质量分 X 全员前列 / 但 Y 是短板 / 风险是 Z"（评价）
- 模板：先量化亮点 → 再量化短板/风险，每张卡两句话内出褒贬
- 例子：Pingfan 终版 = "技术质量全员前列（agent-browser 84 分），项目大脑定位。靠 8 个编排类 skill 串起 agent 协作链，但业务一线交付要靠下游兑现。"

---

## 6. 交互（4 项 + 5 项动效）

### 4 项交互（用户拍板做的）

1. **Commit 行整条点击跳 GitHub**（`<a>` 包裹整行）
2. **时间序列自定义气泡**（`position:fixed` + 深灰底浅灰边，不用红框 — 否则跟红 cell 重叠太"火"）
3. **UPDATE 按钮 hover 显示"距上次更新 X 分钟"**（JS 30s 刷新）
4. **时间序列横向红色游标线 + 日期/周几气泡**

### 10 项动效（A组 + B组 + C组 全做）

| 组 | # | 动效 |
|---|---|---|
| A | 1 | 6 卡淡入上浮 stagger（80ms × 6）|
| A | 2 | 分数条 scaleX 0→1（900ms cubic-bezier）|
| A | 3 | 热力图**打字机模式**逐行从左到右"啪"上去（行间 380ms / 格间 22ms / 弹性缓动）|
| B | 1 | commit 行红条 hover（左侧 2px 红条滑入 + padding-left 微移）|
| B | 2 | skill 行 hover 分数条变红 |
| B | 3 | avatar hover 缩放 1.06 + 红色光晕 |
| B | 4 | UPDATE 按钮 hover 红色边框扫描循环 |
| C | 1 | 顶部 1.5px 红线滚动进度 |
| C | 2 | IntersectionObserver 滚到时 section 入场（用户主动追加问"滚动有动效么"）|
| C | 3 | 滚 > 800px 显示回顶按钮 |

### 动效原则（Nothing 调性）

- 全 CSS transition，不用 JS 动画库
- 时长 ≤ 900ms
- 缓动统一：`cubic-bezier(0.25, 0.1, 0.25, 1)`（natural 曲线）
- 弹性反弹用：`cubic-bezier(0.34, 1.56, 0.64, 1)`
- 只动 `transform` / `opacity` / `width`（GPU 加速）
- 必须支持 `prefers-reduced-motion`（用户系统关动效就全禁）

### 已踩过的坑

- **tooltip 撑高容器 → 滚动条 + 抖动**
  - 根因：`position:absolute` 挂在容器内
  - 修法：改 `position:fixed` + `.hmwrap{overflow:hidden}` 双保险
- **双 tooltip**：SVG `<rect>` 嵌了 `<title>` 又叠自定义气泡
  - 修法：删 `<title>`，只留自定义

---

## 7. 「核心技能 / 低质量技能」表格跳转

- 整行 hover 高亮（`.skill-row:hover`）
- skill 名字 = `<a>` → `https://github.com/charlesliu66/fastpublish/tree/master/<path>`
- `target="_blank"` 新窗口
- 作者名**不跳转**（GitHub 没用户主页可跳）

---

## 8. 后端：一键更新按钮

- Python stdlib `http.server`（不依赖 Flask）
- systemd: `fastpublish-refresh.service` 监听 `127.0.0.1:8081`
- 5 步管线：git pull → prepare_data.sh → analyze.py → build_html.py → cp
- SSE 实时进度推送
- **冷却 60 秒**（用户要求，原 20s）
- nginx 反代必须 `proxy_buffering off` 才能 SSE 流式推

---

## 9. 工具循环防御（重要 — 防止死循环）

1. **截图是 nice-to-have，不是验收硬卡口** → 改完 → 部署 → 给链接让用户眼验
2. **重试 3 次法则**：同一目的失败 ≥ 3 次强制切路径，用变量计数
3. **截图替代路径排序**：chrome screenshot → browser tool → curl + grep → 直接给链接
4. **卡死自救**：重试 ≥ 2 次没出来 → 立刻停 → 发"X 卡了，先交付 Y" → 别闷头试第 4 次
5. **通信优先级 > 验收完美度**

---

## 10. 用户偏好笔记（必记）

- **话术简单直白**：少废话、少术语、多用表格
- **看到回退会很不爽**：自检能力强，会一眼挑出旧版样式丢失
- **追问 3 次 = AI 前 2 次都错**：他记忆比 LLM 准，立刻切搜索路径不要再凭印象
- **给候选 ABC 选一个比一次性输出 1 个版本高效**
- **不要 emoji 不要标题党 要量化**
- **稳定 IP 链接，不用临时隧道**
- **要"评价"不要"解释"，要带数字带褒贬**

---

## 11. 回退史（按时间顺序）

| 时间 | 回退点 | 用户反应 | 修法 |
|---|---|---|---|
| 13:00 | Charles 卡跨两列、SVG 缩水、Doto 失效 | 截图反弹 | grep + edit |
| 13:10 | 卡片排序错、评级错、verdict 红框丢 | 二次截图反弹 | 创建 karpathy-coding skill |
| 13:50 | 关键词上线时 `*4` 翻倍 → 分数 368/100 | 截图 | 删 `*4` |
| 13:50 | 关键词错层（flex-wrap） | 同截图 | `white-space:nowrap` |
| 14:10 | tooltip 撑高容器 → 滚动条 + table 抖动 | 截图 | `position:fixed` |
| 14:15 | 原生 `<title>` 和自定义气泡同时弹 | 截图 | 删 `<title>` |

**核心教训**：每次修改后必须 grep 检查所有旧改动点（"保留清单"），并部署后让用户眼验。

---

## 12. 文件清单（这次 commit 包含）

**fastpublish 仓库**：
- `reports/contribution/2026-05-15_contribution_report.html`（最新报告）
- `skills/project-contribution-report/references/scripts/analyze.py`
- `skills/project-contribution-report/references/scripts/build_html.py`（v8 完整版）
- `skills/project-contribution-report/references/scripts/refresh_server.py`
- `skills/project-contribution-report/references/scripts/fastpublish-refresh.service`
- `skills/karpathy-coding/SKILL.md`（新 skill）

**personal-skill 仓库**（镜像）：
- 同上 `skills/karpathy-coding/`
- 同上 `skills/project-contribution-report/references/scripts/`
- `examples/fastpublish-report/2026-05-15_contribution_report.html`

---

## 13. 下一次修改前 Checklist

```
[ ] 1. 读这个 DISCUSSION-POINTS.md
[ ] 2. 读 karpathy-coding SKILL.md
[ ] 3. grep 列保留清单
[ ] 4. 用 edit 精改（不用 write）
[ ] 5. 跑回归探针（8+ 项）
[ ] 6. 部署 → 给链接 → 让用户眼验
[ ] 7. 修改后更新本文件的"回退史"或"决策"
```
