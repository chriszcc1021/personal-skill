# Whysper iOS 快捷指令配置

## 目标
按 Action Button（长按）→ 截屏 → 自动上传到 Whysper → AI 抽事件/码/任务

## 配置步骤

### 1. 打开「捷径」App，新建快捷指令

### 2. 添加动作（顺序）

| # | 动作 | 参数 |
|---|---|---|
| 1 | **截屏** | （iOS 自动捕获当前屏幕，分享时会跳出隐私确认） |
| 2 | **获取「截屏」的内容** | 用上一步输出 |
| 3 | **通过 URL 获取内容** | URL: `https://broadway-aim-discuss-occasions.trycloudflare.com/whysper-api/entries` |
|   |   | 方法: **POST** |
|   |   | 请求体: **表单** |
|   |   | 字段 1: `image` (文件) = 上一步输出 |
|   |   | 字段 2: `source` (文本) = `shortcut` |
| 4 | **显示通知** | 标题: "Whysper" / 正文: "已上传，AI 处理中" |

### 3. 命名 + 绑定 Action Button

1. 起名「Whysper 截图」
2. 设置 → Action Button → 选「快捷指令」→ 选「Whysper 截图」
3. 长按 Action Button 触发

### 4. 首次运行
- 系统会弹「允许访问 broadway-aim...trycloudflare.com」→ 选「允许」
- 之后每次自动跑

## 注意

- **trycloudflare URL 不稳定**：临时隧道偶尔换域名，等做了固定域名再固化
- **响应快慢**：上传约 1-2 秒，AI 处理 5-15 秒（异步），通知是「已上传」，处理结果进 Whysper「记」列表
- **失败排查**：通知里加一行「获取上一步输出的 `状态`」就能看到 HTTP 状态码
