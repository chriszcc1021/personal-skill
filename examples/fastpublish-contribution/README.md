# Example: fastpublish 仓库贡献画像

由 `skills/project-contribution-report` 生成的实战产出。

- 仓库：`charlesliu66/fastpublish`
- 采样窗口：2026-04-13 → 2026-05-14（30 天）
- 113 commits, 6 contributors
- 在线版：https://broadway-aim-discuss-occasions.trycloudflare.com/fastpublish/

## 关键设计点

- OLED 黑底 + Doto 点阵字体（240px hero 大数字）
- 红色仅做 interrupt（accent #D71921，呼吸点 + 零引用警告）
- 5 维加权评分 + 贝叶斯先验修正（prior_n=5, prior_avg=71）
- 6 张人物卡，按 composite_score 排序，verdict 必含量化点
