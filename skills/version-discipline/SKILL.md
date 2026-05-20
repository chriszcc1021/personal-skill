---
name: version-discipline
version: 1.0
description: 强制每个项目都有 VERSION + CHANGELOG.md + git tag，每次部署 bump 一次。改动可追溯、可回退、可分享给用户看更新日志。所有代码改动都触发此 skill。
---

# SKILL: 版本管理纪律

## 触发条件

**所有代码改动**都走这个流程。无例外。

---

## 每个项目必备 3 件套

```
projects/<name>/
├── VERSION             # 纯数字，如 0.4.2
├── CHANGELOG.md        # 人话写的迭代记录
└── ...
```

新项目从 `0.1.0` 起跑。

---

## 版本号规则（SemVer）

- `MAJOR.MINOR.PATCH`
- **MAJOR**：破坏性改动（API 变了 / 数据结构换了 / 用户必须重新配置）
- **MINOR**：新 feature（向后兼容）
- **PATCH**：bug fix / 文案 / 样式 / 重构

**默认 bump PATCH**。能 minor 才 minor，能 major 才 major。

---

## CHANGELOG 格式（Keep a Changelog）

```markdown
# <Project> Changelog

## [Unreleased]

## [0.4.2] - 2026-05-20
### Fixed
- iOS 加日历按钮点击空白页（.ics Content-Disposition: attachment → inline）

### Added
- `/api/entries/{id}/event` endpoint，给快捷指令拿扁平事件结构

## [0.4.1] - 2026-05-19
### Fixed
- whysper-api 跑在手动 nohup 进程没加载 AI key，视觉抽取永远失败
```

**Section 类目**（按需用，没就不写）：
- `Added` — 新功能
- `Changed` — 现有功能改动
- `Fixed` — bug 修复
- `Removed` — 删功能
- `Deprecated` — 即将删
- `Security` — 安全修复

**写法要求**：
- 人话，1-3 行/条
- 不写实现细节（commit 里有）
- 写"用户看得到的影响"（"点按钮不跳空白页"，不是"改了 nginx config"）

---

## 每次改完代码强制流程

1. **改代码**（按 karpathy-coding 流程）
2. **决定 bump 哪一位**（默认 PATCH）
3. **写 CHANGELOG.md**（在 `[Unreleased]` 下面加条目）
4. **bump VERSION** 文件
5. **commit message** 带项目 + 版本前缀：
   ```
   [whysper v0.4.2] iOS .ics 改 inline，加日历不再跳空白页
   ```
6. **部署后打 tag**：
   ```bash
   git tag -a whysper-v0.4.2 -m "iOS 加日历修复"
   git push --tags
   ```

回退一行命令：`git checkout whysper-v0.4.1`。

---

## bump 时机

**每次部署 bump 一次**。
- 小改一行 → 攒到下次部署一起 bump
- 大改一个 feature → 单独部署单独 bump

**不要**：每个 commit 都 bump（CHANGELOG 会太碎）
**不要**：积攒一周才 bump（出问题不知道回退到哪）

---

## 部署元数据（可选但强烈推荐）

服务端跑 `/api/version` endpoint 返回：

```json
{
  "version": "0.4.2",
  "git_sha": "1950eba",
  "deployed_at": "2026-05-20T14:14:00+08:00"
}
```

前端顶栏 / footer 显示当前版本，看一眼就知道生产部署的是哪一版。

### 实现模板（FastAPI）

```python
@app.get("/api/version")
def version():
    return {
        "version": (ROOT/"VERSION").read_text().strip(),
        "git_sha": os.environ.get("GIT_SHA", ""),
        "deployed_at": os.environ.get("DEPLOYED_AT", ""),
    }
```

部署脚本注入：
```bash
GIT_SHA=$(git rev-parse --short HEAD) \
DEPLOYED_AT=$(date -Iseconds) \
systemctl restart whysper-api
```

---

## 反例

| ❌ | ✅ |
|---|---|
| commit「fix xxx」没版本号 | `[whysper v0.4.2] iOS .ics 修复` |
| CHANGELOG 写"重构了下" | "Fixed: 点加日历按钮不再跳空白页" |
| 攒一周才 bump | 每次部署 bump |
| 所有改动都 MAJOR | 默认 PATCH，破坏性才 MAJOR |
| tag 命名 `v1`、`final` | `whysper-v0.4.2` 项目名+版本 |
| 部署忘了打 tag | 部署脚本最后一步强制 `git tag` |

---

## 经验规则

<!-- 格式：[YYYY-MM-DD] 场景：... 结论：... -->

- [2026-05-20] 场景：whysper 改了 30 次没版本号，用户问"现在第几版了"答不出来。
  结论：所有项目强制 VERSION + CHANGELOG，每次部署 bump 一次。

---

*创建：2026-05-20，张鱼哥拍板「所有开发都按这套来」*
