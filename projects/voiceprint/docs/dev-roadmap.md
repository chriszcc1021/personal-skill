# voiceprint 分批开发路线 (Roadmap)

> 张鱼哥问:肯定分批开发,怎么拆?本文给完整开发路线 + 每批交付物 + 依赖关系 + 谁来做(主agent/子agent)。

## 核心原则
- **不可能一个主 agent 一口气做完**。按"探针 → 后端 → 建库 → 前端 → 联调 → 上线"分批,每批有明确交付物和验收 Gate,过一批开一批。
- 后端是命根子先做,前端建库可并行,子 agent 各管一摊。

---

## Batch 0 — 技术探针 (半天,主 agent 亲自跑)
**目的**:验证"唱歌到底能不能声纹匹配 + 区分度够不够",跑砸了整个方案要调。
- 服务器装 Resemblyzer + Demucs + librosa
- 拿 3-5 个歌手代表作 → Demucs 分离唱歌人声 → 提 embedding 建微型库
- 张鱼哥/牛子哥录一段清唱 → 匹配 → 看排名合不合理
- 同时验证音高检测(音域)能否正常出 F2-G4 这种结果
**Gate**:区分度 OK + 结果不离谱 → 放行 Batch 1;否则调方案(如加大依赖音域维度)
**产出**:探针报告 + 相似度阈值初值

---

## Batch 1 — 后端核心 API (2-3天,子agent: backend)
**依赖**:Batch 0 通过
- FastAPI 骨架 + `/match` `/singers` 接口(按 api-spec)
- 音频管线:任意格式 → ffmpeg wav16k → VAD去静音 → 校验(6种错误码)
- 声纹提取(Resemblyzer/ECAPA)
- 音域检测(CREPE/pyin → low/high note + 声部)
- 双维度匹配:tone_matches(音色) + range_matches(音域)
- scoring 映射(余弦→百分比)
- 空库也能跑通(库后灌)
**Gate**:Postman 打通所有接口,mock库能返回结果,延迟<3s
**产出**:可部署后端 + API 文档

---

## Batch 2 — 歌手库建设 (3-4天,子agent: library,可与Batch1/3并行)
**依赖**:Batch 0 的 pipeline 脚本(提取+分离流程)
- 50人名单定稿(内地13/港台13/日本12/欧美12)
- 每人:找 official acapella 或 Demucs 分离代表作 → 清洗 → 提 embedding + 音域 → 存库
- 质量守门:每人≥3段有效,内部相似度>0.6
- 建库脚本化,可增量补歌手
**Gate**:50人向量库建成,抽查匹配合理
**产出**:singers 声纹库(向量+元数据+头像) + 建库脚本

---

## Batch 3 — Web 前端 H5 (2-3天,子agent: frontend,可与Batch2并行)
**依赖**:Batch 1 的 api-spec(接口定死就能并行,不等后端做完)
- Spotify 风格 UI(深色#121212 + 绿#1DB954)
- 录音模块(MediaRecorder,引导"清唱15-30s")
- 上传 + loading + 结果页(歌手卡片横滑+匹配度条+音域模块)
- 分享卡片(Spotify Wrapped 风)
- 错误态处理(太短/太吵/无人声)
**Gate**:接 mock API 跑通全流程,手机H5流畅
**产出**:Web 前端

---

## Batch 4 — 联调 + 部署 (1-2天,主agent)
**依赖**:Batch 1+2+3 完成
- 前端接真实后端 + 真实库
- 端到端测试(按 mvp-acceptance 验收)
- 找5-10真人实测,收主观认可率
- 部署到 43.134.32.223 子路径
**Gate**:MVP 验收全过(认可率≥50%,延迟达标,区分度OK)
**产出**:线上可访问的 Web MVP

---

## Batch 5 — 微信小程序 (Phase 2,验证成功后再启动)
**依赖**:Web MVP 验证市场反应 OK
- 后端零改动复用
- 小程序前端:换录音API(wx.getRecorderManager)+ UI 重写
- 走审核上架(娱乐类目+麦克风权限说明+免责)
**产出**:上线小程序

---

## 依赖 & 并行关系图
```
Batch0(探针) ──放行──> Batch1(后端) ┐
                                    ├─> Batch4(联调部署) ──> Batch5(小程序)
              api-spec定死 ─> Batch3(前端) ┘
              pipeline脚本 ─> Batch2(建库) ┘
```
- Batch1/2/3 三条线可并行(前提:api-spec 和 pipeline 在 Batch0 后先冻结)
- 主 agent 管 Batch0/4/5(探针+联调+上线) + 总协调
- 子 agent 分管 Batch1(后端)/Batch2(建库)/Batch3(前端)

## 总工期估算
- 串行关键路径:探针0.5 + 后端3 + 联调2 = 5.5天(建库/前端并行不占关键路径)
- 实际约 **6-7 天出 Web MVP**,小程序另算

## 为什么这么拆
1. **探针先行**:最大风险(唱歌能否匹配)提前暴露,别做完才发现不行
2. **api-spec 先冻结**:前后端解耦,三线并行省时间
3. **建库独立**:体力活,可并行/可外包,不卡技术线
4. **子agent分工**:各管一摊边界清晰,主agent只做验证+协调,不当瓶颈

---

## 🛡️ 防丢 + 分工机制（固化 · 张鱼哥 2026-07-19 要求）

> 目的:主 session 上下文一满,后面 Batch 全崩。用"文件即记忆 + 子agent隔离"防爆防丢。

### 原则1:文件即记忆,git 是唯一真相源
- 所有规划文档 + 代码 + 声纹库元数据全部落盘 git(chriszcc1021/personal-skill/projects/voiceprint)
- 主 session 上下文丢光/重启也不怕:**读一遍 README 总索引即可完整恢复项目状态**
- 任何进度节点必须 commit + push,不留在内存里

### 原则2:主 session 只做"协调+验收+记账",保持轻
- 主 agent **不写具体业务代码**(后端/建库/前端的实现)
- 主 agent 只负责:跑探针(Batch0)、派活、收子agent摘要、验收 Gate、联调上线(Batch4)、记账
- 严禁把三大块的代码/日志/报错倒进主 session → 那是上下文爆炸的根源

### 原则3:每个子agent独立干净上下文,自带边界
| 子agent | 管 | 输入(读) | 产出(写+commit) |
|---|---|---|---|
| A · backend | Batch1 后端 | api-spec.md + scoring.md | 后端代码 + API文档 |
| B · library | Batch2 建库 | singer-library.md + material-source.md + pipeline脚本 | 声纹库 + 建库脚本 |
| C · frontend | Batch3 前端接口 | api-spec.md + 现有 web/index.html | 真API对接的前端 |

### 原则4:每个子任务必须自闭环(三步铁律)
1. **开工先读**:README 总索引 + 对应 docs(恢复上下文,不依赖主session口述)
2. **干完立即** commit + push(成果落盘,防丢)
3. **回主session只报摘要**(几百字完成报告,不倒几万行过程)
→ 好处:哪个子agent中途挂了,重开一个读 git 接着干,进度零丢失

### 原则5:探针不派子agent,主agent亲跑
- Batch0 要跟张鱼哥互动(录清唱样本),且是全项目风险闸门,主 agent 亲自在主session跑
- 探针过了 → 冻结 api-spec + pipeline 脚本 → 才派 A/B/C 三个子agent并行

### 执行顺序(固化)
```
[主agent] Batch0 探针(亲跑,需张鱼哥录音)
    │ 过Gate → 冻结 api-spec + pipeline
    ▼
[并行] 子agent A(后端) ∥ 子agent B(建库) ∥ 子agent C(前端)
    │ 各自:读docs → 干活 → commit → 报摘要
    ▼
[主agent] Batch4 联调+部署+真人验收
    ▼
[主agent] Batch5 小程序(验证OK再启动)
```

### 上下文水位红线
- 主 session 到 ~60% 主动做记忆刷写(写 memory + 确认 git 已 push),必要时压缩
- 派子agent前先确认本轮成果已落盘,再卸载

— 牛子哥 v2026.7.19 · 01:46 SGT
