# 海绵宝宝鱼举哑铃 · 三方案动画 Demo

主入口对比页：`/anim-demos/compare-curl/index.html`

## 方案 1 · PNG 序列帧
- 路径：`s1-png-sequence/`
- 文件：`index.html` + `frame-1.png` ~ `frame-6.png`
- 思路：OpenAI gpt-image-2 同 prompt 模板生成 6 个姿势，浏览器用 CSS `steps(6)` 离散跳帧
- 帧率：5 fps（每帧 200ms）
- 体积：~6.2 MB（PNG 主导）
- 优：视觉最"卡通海绵宝宝"
- 劣：AI 帧间脸有微 drift（瞳孔/嘴角）

## 方案 2 · SVG + GSAP 骨骼动画
- 路径：`s2-svg-gsap/index.html`（单文件）
- 思路：inline SVG 手画鱼，分层 group：`#body / #shoulder-{L,R} / #upper-arm-{L,R} / #forearm-{L,R} / #dumbbell-{L,R}`。GSAP timeline 控制上臂 + 前臂独立旋转，哑铃反向旋转保持水平 → 重力错觉
- 帧率：60 fps（浏览器原生）
- 体积：~10 KB
- 优：矢量无损 · 关节真旋转（不是抖动）· 体积极小 · 缓动顺滑
- 劣：鱼外形是手画 SVG，比 AI 生成的"真卡通感"稍弱

## 方案 3 · Rive 运行时
- 路径：`s3-rive/index.html`
- 思路：没有 Rive 编辑器环境造不出原创 .riv，所以用 `@rive-app/canvas` 加载 Rive 官方公开 `vehicles.riv` 演示运行时能力；同时写明原创制作流程
- 帧率：60 fps
- 体积：~30 KB（.riv 文件）
- 优：state machine、矢量、文件小
- 劣：必须 GUI Rive Editor 制作原创资源

## 诚实评估
🏆 **方案 2 动作最自然** — 因为做了真正的两段骨骼旋转 + 顶峰停顿 + 哑铃水平校正。
🎨 **方案 1 视觉最像海绵宝宝**，但帧间 drift 明显。
🛠️ **方案 3** 是诚实演示，不是原创。
