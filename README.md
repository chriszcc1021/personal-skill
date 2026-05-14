# Personal Skill Library

张鱼哥的个人知识库，存放可复用的 AI Skills 和实战案例。

## 📁 目录结构

```
.
├── skills/                    # 可复用的 AgentSkills
│   └── product-encyclopedia/  # 产品对比页生成 skill
└── examples/                  # 实战案例
    └── appliance-guide/       # 家电选购指南（含登山包）
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

## 📚 Examples

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
