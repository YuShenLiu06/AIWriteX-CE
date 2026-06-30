# AIWriteX 发布书写标准

> 最后更新: 2026-06-30
> 生效范围: 自 2026-06-30 起的所有发版
> 依据: Semantic Versioning 2.0.0 + Keep a Changelog 1.1.0 + Conventional Commits 1.0.0

---

## 0. 为什么需要这份标准

2026-06-30 前存在的痛点:

- **本仓库(fork 后)早期 tag 格式不统一**:`1.1.5`(无前缀)/ `v1.1.0`(小写 v)混用(`V2.4.x` 等大写 V 标签是 fork 前上游版本线,见 §3.2)。
- **CHANGELOG 是一次性叙述长文**:无分类、无版本号、无日期、无「未发布」段,类似开发报告。
- **版本号变更与功能改动混在同一条 commit**,历史噪声大。
- **没有统一的发版时机规则**:什么时候该升版本、打 tag、发 Release Notes 全凭感觉。

本标准一次性解决上述问题。

---

## 1. 核心原则

三条铁律:

1. **版本号遵循 SemVer** — https://semver.org/lang/zh-CN/
2. **CHANGELOG 遵循 Keep a Changelog** — https://keepachangelog.com/zh-CN/1.1.0/
3. **攒批发版** — 不在每次合并 PR 后发版,只在达到稳定里程碑时切一个版本

---

## 2. 版本号规则

### 2.1 双独立版本

AIWriteX 有两个相互独立的版本号,各自维护,**不要联动**:

| 包 | 格式 | 唯一真实源(改版本时两处必须同步) |
|---|---|---|
| 主应用(Web) | `MAJOR.MINOR.PATCH` | `src/ai_write_x/version.py` 的 `__version__` + `pyproject.toml` 的 `version` |
| CLI | `MAJOR.MINOR.PATCH` | `client/aiwritex_cli/__init__.py` 的 `__version__` + `client/pyproject.toml` 的 `version` |

> 改版本号时,每个包的两个文件必须同步更新,否则构建版本与运行时版本不一致。

### 2.2 bump 决策

一次发版,版本号只跳**一次**,跳哪一级取决于这批改动里**最高级别**的那一项:

| 本次发版含什么 | 跳哪一级 | 举例(从 1.1.5) |
|---|---|---|
| 有不兼容破坏(无论是修复还是新功能) | MAJOR +1 | → `2.0.0` |
| 有新功能(可同时含修复) | MINOR +1 | → `1.2.0` |
| 只修 bug、无新功能 | PATCH +1 | → `1.1.6` |
| 纯文档 / 重构 / 内部清理,对用户无可见影响 | 可不发版,或 PATCH +1 | → `1.1.6` 或不发 |

核心心法:**多个改动合并成一次 bump**。修 3 个 bug 也是一次 PATCH +1,不是三次。

---

## 3. tag 命名规范

### 3.1 命名格式

| 包 | 格式 | 示例 |
|---|---|---|
| 主应用 | `vX.Y.Z`(小写 `v` 前缀) | `v1.1.6` |
| CLI | `cli-vX.Y.Z`(`cli-` 前缀,避免与主应用冲突) | `cli-v1.1.2` |

硬规则:**每个 tag 必须对应一个已写入源文件的真实版本号**。禁止凭空打一个不匹配源文件的 tag。

### 3.2 历史标签(fork 前后两条线,均不回溯)

本仓库是 fork(CE 版),标签历史分两条**独立**的版本线:

| 类别 | 示例 | 来源 | 处理 |
|---|---|---|---|
| 上游继承标签 | `V2.4.4`、`V2.3.x`、`V2.2.x` 等(大写 `V` + 2.x 主版本) | fork **前**的原项目 | 保留原样,作为 fork 点历史快照,**不纳入本仓库版本序列** |
| 本仓库早期标签 | `1.1.5`、`1.1.3`、`v1.1.0`、`v1.0.0`(有 / 无 `v` 前缀混用) | fork **后**本项目自建 | 保留原样,不回溯改名;今后统一 `vX.Y.Z` |

要点:

- **`V2.x.x` 与 `1.1.x` 是两条独立版本线**,不要当成同一序列的前后段。本仓库有效版本序列从 `1.1.0` 起算。
- 两类历史标签都不回溯改名,原因相同:均已推送到 GitHub 远端、部分挂有 Release(`1.1.2`、`v1.0.0`),回溯改名违反 Git 官方建议,风险远大于收益。
- 今后一律使用 §3.1 格式。

---

## 4. CHANGELOG 写法

### 4.1 文件位置

| 包 | 文件 |
|---|---|
| 主应用 | `CHANGELOG.md`(仓库根目录) |
| CLI | `client/CHANGELOG.md`(独立包,单独维护) |

### 4.2 文件结构(模板)

```markdown
# Changelog

本项目所有显著变更将记录于此。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/),
遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [1.1.6] - 2026-07-02

### Fixed
- 修复定时任务卡在「执行中」的问题 (#7)
- 修复 print_json 标量值触发的 JSONDecodeError (#7)

## [1.1.5] - 2026-06-30

### Added
- server-config 命令组 (#5)
- articles accounts 命令 (#5)

### Fixed
- 修复 generate 流式跟踪 bug (#5)
```

### 4.3 规则

- 顶部固定 `## [Unreleased]` 段:开发期间所有变更先进这里,发版时改名为 `[版本号] - 日期`。
- 版本**倒序**:最新版本在最上面。
- 日期用 **ISO 8601**(`2026-07-02`),不要写 `2026/7/2` 或 `2026年7月2日`。
- 六个固定分类,顺序固定,没有该类的版本可省略:

| 分类 | 写什么 |
|---|---|
| Added 新增 | 新功能 |
| Changed 变更 | 已有功能的改动 |
| Deprecated 弃用 | 即将移除,提前告知 |
| Removed 移除 | 本次移除的功能 |
| Fixed 修复 | Bug 修复 |
| Security 安全 | 安全相关 |

- 每条格式:`- 简述 (#PR号 或 commit 短 hash)`。

### 4.4 写法要点

- 面向**使用者**,写「对用户的影响」,不写实现细节、不贴代码、不列「涉及文件」。
- Breaking change **单独突出**标注,例如:`- BREAKING: 重命名 config.api_key 为 config.api.token,需迁移`。
- 每条链接 PR / issue,方便追溯。
- 写就写完整,别留半句。

### 4.5 反模式(明确禁止)

| 反模式 | 说明 |
|---|---|
| 直接拿 git log 当 CHANGELOG | 无分类、无日期、机器味,对人不友好 |
| 无分类的叙述长文 | 旧 `CHANGELOG.md` 就是这种,已废弃 |
| 忘记写 Deprecated | 即将移除的功能必须提前告知 |
| 日期格式不统一 | 必须 ISO 8601 |
| 不标 breaking change | 破坏性改动必须显眼 |
| 整理时删掉旧版本 | 历史不能丢 |
| 堆无关紧要的内部改动 | 只记用户可见的显著变更 |

---

## 5. 发版时机与节奏(攒批发版)

### 5.1 两层概念

| 层 | 时机 | 做什么 | 不做什么 |
|---|---|---|---|
| 开发层 | 平时合并 PR | 变更进 CHANGELOG 的 `[Unreleased]` 段 | 不动版本号、不打 tag、不发 Release Notes |
| 发布层 | 达到稳定里程碑 | bump 版本 → `[Unreleased]` 改名为版本号+日期 → 打 tag → 发 GitHub Release Notes | —— |

判断「稳定里程碑」的参考信号(满足其一即可考虑发版):

- 一批计划内功能 / 修复全部完成并自测通过
- 修复了一个影响线上使用的紧急 bug
- 累积的 `[Unreleased]` 条目已经多到值得固化成一个版本

### 5.2 每个功能不需要单独标记

把三件事的分工分清:

| 东西 | 干什么 | 什么时候 |
|---|---|---|
| commit message | 标记「这次改动是什么」 | 每次提交(走 conventional commit) |
| CHANGELOG `[Unreleased]` | 记录「这个改动将来进哪个版本」 | 合并 PR 后顺手加一行(编辑文件,不打 tag) |
| tag / 版本号 | 标记「这是一个发布的版本」 | 只在发版点 |

**禁止为单个功能打 tag。** tag 是「版本」的标记,不是「功能」的标记。

---

## 6. GitHub Release Notes 写法

### 6.1 标题

| 包 | 标题格式 | 示例 |
|---|---|---|
| 主应用 | `vX.Y.Z` | `v1.1.6` |
| CLI | `CLI vX.Y.Z` | `CLI v1.1.2` |

### 6.2 正文结构(模板)

```markdown
一句话摘要(本版主要做了什么)

### Added
- ...(直接复用 CHANGELOG 该版本段)

### Fixed
- ...

### 升级 / 迁移注意
- BREAKING: ...(若有)

**完整变更**:v1.1.5...v1.1.6
```

### 6.3 与 CHANGELOG 同源

Release Notes 的分类变更段落**直接复制自 CHANGELOG 对应版本段**,不重复手写两份、不另起措辞。两边内容必须一致。

### 6.4 Pre-release 标记

不稳定 / 内测版本发布时,勾选 GitHub 的 **Set as a pre-release**。正式稳定版取消该标记。

---

## 7. 发版点操作清单

每次到达发版点,按顺序执行(以主应用为例,CLI 同理换路径与 tag 前缀):

1. 确认 `[Unreleased]` 段已收集齐本次所有变更。
2. 根据 §2.2 决策本次版本号(从当前版本跳到目标)。
3. 同步更新两个源文件:`src/ai_write_x/version.py` 的 `__version__` + `pyproject.toml` 的 `version`。
4. 把 CHANGELOG 的 `## [Unreleased]` 改名为 `## [新版本号] - 今天日期(ISO 8601)`,并在顶部重新留一个空的 `## [Unreleased]`。
5. 提交:`chore(release): 发布 vX.Y.Z`。
6. 打 tag:`git tag vX.Y.Z`。
7. 推送:`git push && git push origin vX.Y.Z`。
8. 在 GitHub 上发 Release Notes(§6),勾选 / 取消 Pre-release。

CLI 发版把路径换成 `client/`,tag 用 `cli-vX.Y.Z`,标题用 `CLI vX.Y.Z`。

---

## 8. 常见问题

**Q1:一个版本可以包含多个 PR 吗?**
可以,这是常态。一个版本 = 自上次发版以来所有已合并 PR 的集合,按类型汇总进 CHANGELOG。一个 PR 发一版只在紧急 hotfix 时出现。

**Q2:连续修了多个 bug、没有新功能,版本号怎么写?**
只升 PATCH。从 `1.1.5` 修一批 bug 后发 `1.1.6`,所有修复列在 `### Fixed` 下,版本号只跳一次。

**Q3:每个功能需要在本地打个标记吗?**
不需要。commit message 就是标记,合并 PR 后在 CHANGELOG `[Unreleased]` 加一行即可,tag 只在发版点打。

**Q4:主应用和 CLI 版本号要联动吗?**
不要。两者独立维护,各自发版,各自打 tag(`vX.Y.Z` vs `cli-vX.Y.Z`)。

**Q5:历史 tag 那么乱,要不要清理改名?**
不要。已推远端且部分挂有 Release,改名风险大于收益。今后统一新格式即可。

---

## 9. 参考

- Semantic Versioning 2.0.0 — https://semver.org/lang/zh-CN/
- Keep a Changelog 1.1.0 — https://keepachangelog.com/zh-CN/1.1.0/
- Conventional Commits 1.0.0 — https://www.conventionalcommits.org/zh-hans/v1.0.0/
