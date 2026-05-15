# SKILL: 生成项目贡献画像报告（Project Contribution Process Report）

## 描述
扫描一个 git 仓库（含 skills / agents / knowledge / 数据文件），对每个贡献者做多维量化打分，输出一份 Nothing-Design 风格的单文件 HTML 报告，含 5 指标卡片、时间序列热图、Skill 主笔分布、贝叶斯加权评级。

**输入**：本地 git 仓库路径 + 30 天采样窗口
**输出**：单文件 HTML（OLED 黑底 + Doto 点阵大数字），可直接部署或本地打开

---

## 什么时候用

- 月度 / 季度团队回顾，需要"谁做了什么、做得怎么样"的客观画像
- 跨同事的产出对比，但 commit 数会骗人 → 需要拆开看主笔 skills / knowledge / 工具 / 研究资料
- 给老板汇报小组贡献度，但要避免"提交多 = 价值高"的错误结论
- 仓库画像复盘（不是 PR review，是更大尺度的贡献结构分析）

---

## 需要的输入

**必须有**
- 本地 git 仓库的绝对路径
- 该仓库需有清晰目录约定（至少能区分 `skills/`、`agents/`、`docs/` 或 `knowledge/`）
- Python 3.8+，可调用 `git log --numstat`

**最好有**
- 贡献者邮箱→中文名 / 显示名 的映射（避免 `unknown` author）
- Skill 质量评分维度的领域共识（S 数据源 / R 逻辑 / E 可执行 / Ref 引用 / F 输出格式 各 5 分）

---

## 执行步骤

### 1. 数据采集（`analyze.py`）

```bash
cd <repo>
git log --since="30 days ago" --numstat --pretty='format:COMMIT%n%H%n%ai%n%an%n%s' > /tmp/numstat.txt
```

把每条 commit 解析成 `{hash, date, author, files[], churn}`，按 author 聚合。

### 2. 文件分类（5 类加权评分）

| 类型 | 权重 | 判定规则 |
|---|---|---|
| **SKILLS** | ×1.0 | `skills/*/SKILL.md` 主笔（first author of the file） |
| **KNOWLEDGE** | ×0.6 | `docs/*`、`knowledge/*`、`content/*` 等长文档 |
| **TOOLING** | ×0.5 | `.py / .sh / .cjs / .ts / .mjs` 脚本（注意 `.cjs` 别漏） |
| **RAW** | ×0.2 | 数据文件、FGD 资料、原始转录、CSV / JSON 等 |
| **EXCLUDED** | ×0 | `.tmp`、`node_modules`、生成产物、二进制 |

### 3. Skill 质量分（25 → 100 制）

每个主笔 skill 用 5 维评分 × 5 分 = 25 分，乘 4 转 100 制。

| 维度 | 看什么 |
|---|---|
| **S** 数据源 | 是否说明从哪取数 / 输入约束 |
| **R** 逻辑 | 处理流程是否清晰可推 |
| **E** 可执行 | 有无脚本 / 命令 / 步骤序号 |
| **Ref** 引用 | 有无 references/ 案例 / 参考文档 |
| **F** 输出 | 产出格式是否定义清楚 |

### 4. 贝叶斯加权修正（**关键**）

样本量 ≤ 5 的人均分会虚高。用贝叶斯先验：

```python
avg_adjusted = (n * avg + prior_n * prior_avg) / (n + prior_n)
# prior_avg = 仓库 SKILL 均分（通常 ~71）
# prior_n = 5
```

举例：某人 1 个 skill 打了 84 → 修正后约 73；同时另一个有 8 个 skill 平均 67 的人几乎不变。

### 5. 综合分 + 评级

```
composite = SKILLS×40 + KNOWLEDGE×3 + TOOLING×2 + RAW×1 + 质量分×0.5
```

阈值：`A≥400 / A-≥200 / B+≥130 / B≥90 / B-≥50 / C+≥25 / C<25`

### 6. HTML 渲染（`build_html_v8.py`）

Nothing-Design 风格模板，参考 `references/template_v8.html`：

- **OLED 黑底**：`--bg:#000000 / --raised:#111111 / --border:#1F1F1F`
- **Doto 点阵字体**：240px hero 大数字 / 72px 卡片大数字
- **红色仅作 "interrupt"**：`--accent:#D71921`，用于"零引用"、"警告"、UPDATED 呼吸点
- **6 张人物卡片 5 指标**：提交 / 主笔 SKILLS / 知识文档 / 研究资料 / SKILL 质量分
- **时间序列**：每人 30 天 churn 热图（log 归一化亮度）
- **顶部 hero-stamp**：UPDATED YYYY-MM-DD HH:MM GMT+8 红点呼吸

---

## 产出要求

- **格式**：单文件 HTML，自包含字体 link 和 SVG
- **大小**：50-70KB（不含外部字体）
- **必须包含**：
  - hero 大数字（总 commits）+ UPDATED 时间戳
  - 4 stat 块（参与评分 SKILLS / 贡献者数 / 采样窗口 / 零引用 SKILLS）
  - Skill 主笔分布（按主笔数排序）
  - 时间序列 SVG 热图
  - 6 张人物卡片，按 composite_score 排序
  - 卡片 verdict 写法：先量化亮点（带具体分数）+ 后点短板
  - Rubric 区块（评分维度说明 + 贝叶斯先验说明）
  - Footer：`VER X.X · YYYY-MM-DD · ANALYZE.PY + BUILD_HTML.PY`
- **字体加载**：`<link href="...family=Doto:wght@400;700;800;900&family=Space+Grotesk:...&family=Space+Mono:..."`（**Doto 必须在 link 里**，否则点阵字会回退成 serif）
- **不能出现**：emoji、标题党、未量化的描述（"非常出色"、"略显不足"等）

---

## 质量标准

**合格**
- 所有数字有据可查（git log 可复现）
- 评级阈值固定，不因评价倾向手动调整分数
- Verdict 短句 + 至少一个量化点（"agent-browser 84 分"比"技术质量高"强）
- 移动端 720/420 断点不破

**常见错误**
- ❌ 用平均分排序而忽略样本量 → 必须贝叶斯
- ❌ `.cjs` / `.mjs` 没进白名单 → 工具分丢失
- ❌ 把 `unknown` author 当一个人计 → 必须按邮箱 mapping
- ❌ verdict 写成解释/客套话 → 要带褒贬
- ❌ 改 CSS 字体没同步改 `<link>` 加载 → Doto 退化成 serif（**字体探针**：grep `font-family.*Doto` 后必查 `<link>` 是否含 `family=Doto`）

---

## 参考案例

- 完整模板与脚本：见 `references/template_v8.html`、`references/analyze.py`、`references/build_html_v8.py`
- 实战产出：`https://broadway-aim-discuss-occasions.trycloudflare.com/fastpublish/`

---

## 经验规则
<!-- 格式：[YYYY-MM-DD] 场景：... 结论：... -->

- [2026-05-14] 场景：第一版用 commit 数排序，结论"DeeDee 是大佬"。 结论：错。commit 数 ≠ 价值，必须拆 SKILLS / KNOWLEDGE / TOOLING 4 桶，加权后 Charles 才是真 A。
- [2026-05-14] 场景：Chenchen 只主笔 3 个 skill，平均 80 分，看起来全场最高。 结论：用贝叶斯修正（prior_n=5, prior_avg=71）后降到 74，跟样本多但分数平均的人才能公平比。
- [2026-05-15] 场景：编辑 CSS 改字体配色，浏览器里 Doto 大数字变 serif 了。 结论：CSS 用什么字体 → `<link>` 必须加载什么字体，两边契约必须同步检查。修完做"字体探针" grep 一遍。
- [2026-05-15] 场景：截图验收卡 3 次没出来。 结论：截图非硬卡口，直接给 URL 让用户眼验，**通信优先级 > 验收完美度**。
