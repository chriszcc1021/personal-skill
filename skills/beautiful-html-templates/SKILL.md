---
name: beautiful-html-templates
version: 1.0
description: 34 套精美 HTML slide 模板库（zarazhangrui/beautiful-html-templates），用于让 coding agent 自动生成漂亮的演讲稿 / 介绍页 / 品牌稿。使用流程详见同目录 AGENTS.md。触发条件：用户要做 HTML deck / 介绍页 / slide / 演示稿且提到"好看 / beautiful template"。
---

# SKILL: Beautiful HTML Templates

来源仓库：https://github.com/zarazhangrui/beautiful-html-templates

## 模板列表
34 套：8-bit-orbit / biennale-yellow / block-frame / blue-professional / bold-poster / broadside / capsule / cartesian / cobalt-grid / coral / creative-mode / daisy-days / editorial-forest / editorial-tri-tone / emerald-editorial / grove / long-table / mat / monochrome / neo-grid-bold / peoples-platform / pin-and-paper / pink-script / playful / raw-grid / retro-windows / retro-zine / sakura-chroma / scatterbrain / signal / soft-editorial / stencil-tablet / studio / vellum 等。

## 工作流（详见 AGENTS.md）

1. 先问用户「场合 + 心情」
2. 读 `index.json` 选 3 个候选
3. 各做一张 title slide preview 给用户挑
4. 用户选定后克隆完整模板填内容
5. preserve / replace / extend 规则改每页

## 关键文件
- `AGENTS.md` 操作手册
- `index.json` 模板元数据（mood / tone / best_for / formality）
- `templates/<name>/template.html` 各模板源
- `screenshots/` 预览图

## 用法
触发时先读 `AGENTS.md`，按 5 步走。
