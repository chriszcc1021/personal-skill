
## 像素网球待办（从旧 session 迁移 2026-06-06 11:43）

### 待做功能
1. **回球辅助** — 击球出手时自动修正角度，保证球落在场内。不是飞出去再拉，是出手就对
2. **大招双模式**：
   - **扣杀 Smash**（球在高处 z>20）：边角变黑 vignette + 子弹时间 0.3x 0.8秒 + 角色跳起放大 1.5x + 力量回球球速 2x + AI hitRange 缩小 50%
   - **弧线球 Zone Shot**（球在低处）：屏幕闪蓝光 + 慢动作 0.5x 0.5秒 + 蓄力光圈 + 高弧线旋转球精准角落 + 对手被推远
3. **红土球场** — 红土色 #C2703E/#B8633A + 标准网球场线（底线/边线/发球线/中线/发球区中线）
4. **新精灵图** — 扣杀跳起 4帧 + 蓄力挥拍 4帧（两个角色各一张）
5. **触网修复** — 已修（只有没弹过地的低球才判触网）

### 文件位置
- 游戏：`~/.openclaw/workspace/fastpublish/projects/pixel-tennis/index.html`
- 透明精灵图：`/tmp/fish-p1-t.png` / `/tmp/fish-p2-t.png`（RGBA 512x512，fuzz 5% 去黑底）
- 原始精灵图：`/home/openclaw/.openclaw/media/tool-image-generation/fish-pixel-p1-v2---16411441-3608-4377-a3d5-9c130cdd0176.png` / `fish-pixel-p2-v2---d80b977b-fae8-4e81-ad6c-6e633cf4b964.png`
- 线上：https://broadway-aim-discuss-occasions.trycloudflare.com/fastpublish/projects/pixel-tennis/
- 部署路径：`/var/www/fastpublish/projects/pixel-tennis/`
- 服务器：`ubuntu@43.134.32.223` 密码 `IJARWAMShQ9KgRiNwvIzUFAq`
- pixel-sprite-animation skill：`~/.openclaw/workspace/skills/pixel-sprite-animation/SKILL.md`

### 当前游戏参数
- 单手操控：点击=平击，↑滑=上旋，↓滑=切球，长按=蓄力，双击=必杀
- 角色自动追球跑位
- hitRange=70*SCALE, ball.z<45
- pendingHit 20帧击球缓冲
- 球场：scoreAreaH=60*SCALE, controlH=80*SCALE
- 精灵图 4x4 grid，128px/帧（512/4），ANIMS: idle/run/forehand/backhand
- SpriteAnimator 类在文件顶部

### 参考
- 马里奥网球 Aces 的 Zone Shot / Special Shot 机制
- 张鱼哥发过的海洋生物参考图
