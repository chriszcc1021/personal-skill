---
name: muscle-fund
version: 1.0
description: 比奇堡风格 6 人健身打卡 + 罚款基金 web app。完整可部署的单页应用，含轻账号系统、权限分级、自动罚款入账、比基尼海滩日历、角色形象、动画方案 3 选 1 探索。技术栈纯 HTML/JS + localStorage，无构建工具。
---

# SKILL: 肌肉基金 / Muscle Fund

## 一句话

6 个朋友的健身打卡 + 罚款基金网站，**主题：海绵宝宝比奇堡**。线上访问：https://broadway-aim-discuss-occasions.trycloudflare.com/muscle-fund/

## 项目结构

```
muscle-fund/
├── site/                         # 主站可直接部署
│   ├── index.html                # 单页主入口（登录门 + 角色展厅 + 打卡 + 日历）
│   ├── state.js                  # localStorage 状态管理 + 账号系统
│   ├── peeps.js                  # Open Peeps SVG 角色渲染（部位 scale 公式）
│   ├── common.css                # 通用样式
│   ├── characters.js             # 分层 SVG 角色库（A 方案试做）
│   ├── base.html / checkin.html  # 早期多页版（已废弃，留作参考）
│   ├── ledger.html / onboard.html / settings.html
│   ├── nav.js / test.js
│   └── README.md
└── anim-demos/                   # 角色动画方案探索（3 大方案）
    ├── index.html                # demos 主页
    ├── compare-curl/             # 3 方案举哑铃对比页（推荐先看）
    ├── v1-css/                   # 早期：CSS 动一动
    ├── v2-js/                    # 早期：6 鱼健身房动作池
    ├── v2b-fish/                 # 早期：AI 鱼 lv0 vs lv4 进化过场
    ├── v3-lottie/                # 早期：Lottie 公开示例
    ├── s1-png-sequence/          # 方案 1：AI 6 帧序列轮播
    ├── s2-svg-gsap/              # 方案 2：SVG + GSAP 骨骼旋转
    └── s3-rive/                  # 方案 3：Rive 演示
```

## 核心机制

### 1. 账号系统（轻量无密码）
- localStorage 存 `mf_current_user`
- 第一次访问看到登录门，输入名字匹配 6 人池
- 设备记忆，再次访问直接进
- 6 个种子成员：P神 / 查尔斯 / 张鱼哥 / 狗哥 / Shadow / YK

### 2. 权限分级
| 操作 | 张鱼哥（管理员） | 其他人 |
|---|---|---|
| 改罚款金额 | ✅ | ❌ |
| 加 / 删成员 | ✅ | ✅ |
| 给自己打卡 | ✅ | ✅ |
| 看账本 | ✅ | ✅ |

### 3. 打卡 + 自动入账
- 工作日（周一-五）必须打卡
- 缺勤次日开站时 `settleOverdue()` 自动结算：
  - `member.debt += fineAmount`
  - `member.missDays += 1`
  - `fundTotal += fineAmount`
- 部位累计：手臂 / 胸 / 背 / 腹 / 肩 / 腿 6 部位
- 角色 SVG 按部位等级放大对应区域

### 4. 比基尼海滩日历
- 6 人 × 月份所有日子横滑
- 海绵黄圆点 = 已打卡 / 蟹老板红 ✕ = 缺勤 / 灰 = 周末
- 手机端日历可横滑，名字 sticky

### 5. 部位等级公式（peeps.js / characters.js）
```js
function levelFor(count){
  if(count<5) return 0;
  if(count<10) return 1;
  if(count<20) return 2;
  if(count<30) return 3;
  return 4;
}
const SCALES=[1.0, 1.2, 1.5, 1.8, 2.2];
```

## 比奇堡色卡

```css
--bg-ocean:#4DD0E1   /* 比基尼海滩浅水蓝（主背景） */
--bg-deep:#00838F    /* 深海青绿（暗部对比） */
--bg-sand:#F9E4A6    /* 海底沙色（卡片底） */
--ink:#0D3B4F        /* 深海墨（正文 + 描边） */
--sponge:#FFD600     /* 海绵宝宝黄（金额主角色） */
--patrick:#FF80AB    /* 派大星粉（已打卡高亮） */
--coral:#FF7043      /* 蟹老板红（罚款负向色） */
```

## 字体

- 标题：`Luckiest Guy`（Google Fonts，海绵宝宝 logo 感）
- 中文标题：`ZCOOL KuaiLe`
- 正文 / 数字：`Fredoka 700`
- 中文正文：`Noto Sans SC`
- **¥ 符号坑**：Luckiest Guy 把 ¥ 画成日元双横，必须用 `Noto Sans SC` 单独渲染

## 动画方案探索（3 选 1）

### 数据对比
| 方案 | 体积 | 帧率 | 动作真实度 | 工作流 |
|---|---|---|---|---|
| 1 PNG 序列 | 6 MB | 5 fps | AI 海绵宝宝写实风但帧间漂移 | AI 生 6 帧 + CSS steps() 轮播 |
| **2 SVG+GSAP** | **10 KB** | **60 fps** | **真骨骼旋转 ✅** | SVG 分层 + GSAP timeline |
| 3 Rive | 12 KB | 60 fps | 社区示例（非鱼） | 需 GUI 编辑器 + 登录账号 |

### 已知结论
- 方案 2 技术最干净但 **SVG 几何拼接画风糙**，张鱼哥反馈不达海绵宝宝原作级别
- 方案 1 画风对路但 AI 6 帧之间脸表情漂移 + 体积过大
- 方案 3 必须 GUI 编辑器（沙箱跑不了），需哥本人或外部美术做 .riv

### 未来方向（待哥拍板）
- **混合方案**：AI 写实身体 + SVG 关节骨骼（保画风 + 真动作）
- **Lottie 外包**：美术 AE/Figma 做角色 + 导出 JSON

## 部署

### 线上
- 服务器：`ubuntu@43.134.32.223`
- 目录：`/var/www/fastpublish/muscle-fund/`
- nginx 配置：`/etc/nginx/sites-enabled/appliance-guide` 中 `location /muscle-fund/`
- 访问：https://broadway-aim-discuss-occasions.trycloudflare.com/muscle-fund/

### 部署流程
```bash
sshpass -p ${PASS} scp local.html ubuntu@43.134.32.223:/tmp/
sshpass -p ${PASS} ssh ubuntu@43.134.32.223 \
  "sudo cp /tmp/local.html /var/www/fastpublish/muscle-fund/"
```

## 张鱼哥偏好（开发约束）

- **不喜欢「整张 PNG 抖动」要真动作**
- **「每次改完都要发我下链接」**
- 推崇 Flash 风格骨骼绑定
- 海绵宝宝原作动画级别
- 「宁愿做的慢，也要做的好」
- 视觉 > 可编辑（PPT v6 死规则同款）
- 改前必读 karpathy-coding SKILL.md

## 已知 bug 史（避免回退）

1. `who-select` 改 `who-tag` 时残留 addEventListener → 整 JS 挂
2. `render()` 残留 who-select 渲染代码
3. `checkin()` 用了 `selectedWho` 应改 `currentMemberId`
4. `renderParts()` 内 `m` 重复声明
5. 字体 ¥ 显示日元双横 → Noto Sans SC 渲染修复

## 待办

- [ ] 选定动画方案落地到主站替换 peeps.js
- [ ] 5 档等级递进画法（lv0-lv4 肌肉如何 SVG 递进）
- [ ] 6 个角色独占池机制（之前讨论被覆盖）
- [ ] 混合方案 demo（AI 身体 + SVG 关节）
