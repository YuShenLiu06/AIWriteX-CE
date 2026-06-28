# Issue #1 修复报告 — 鉴权失败 + 配置失效 + API 500

**仓库**: `YuShenLiu06/AIWriteX-CE` · **基线**: `a15c39f` · **日期**: 2026-06-28 · **P0**

## 一、结论

三个 P0 问题全部修复，并在**全新 Docker 容器（与 issue 完全一致的部署场景）**下端到端验证通过；执行了一次真实 AI 写作任务并成功生成 2697 字文章。修复全程使用 **Teammates（多 Agent 并行）** 加速。

| Bug | 现象 | 根因 | 状态 |
|---|---|---|---|
| #1 鉴权失败 | `GET /` 直接 200，公网可越权 | `lifespan` 单一 `try/except` 吞掉 `load_auth_config` 异常 → `_auth_config` 停在 `enabled=False` | ✅ 已修复（fail-safe） |
| #2 配置失效/500 | `/api/config/` → `'tuple' object has no attribute 'get'` | 报告中的 tuple 是**旧镜像残留**（源码本就是 dict）；真实可复现的失败是非 dict 到达 `.get()` | ✅ 已修复（防御 + 自愈） |
| #3 模板 500 | `/api/templates/categories` → `FileNotFoundError` | `get_template_dir()` dev 分支不 `mkdir` + `iterdir()` + Dockerfile 不 `COPY knowledge` | ✅ 已修复（确定性） |

## 二、根因（实测验证，非推测）

**Bug #3（确定性，已复现）**：全新容器内 `/app/knowledge/templates` 不存在 → `templates.py:165 iterdir()` 抛 `FileNotFoundError`。本地不触发是因为 `knowledge/templates` 已存在（13 个分类）。

**Bug #1（失败模式）**：`app.py` 的 `lifespan` 把配置加载、鉴权初始化、调度器初始化全部包在一个 `try/except` 里；任何一处抛异常都会被吞，导致鉴权静默关闭。

**Bug #2（tuple 是陈旧产物）**：静态分析证明 `config.py:63` 的 `default_config` 是干净的 dict 字面量（第 1308 行 `}` 收尾、无尾逗号、仅一处赋值）；**全新 `docker compose build` 实测** `config` 为 dict、`/api/config/` 返回 200。报告中的 tuple 来自旧镜像层/陈旧 `.pyc`。真实可复现的失败是：非 dict 的 `config.config` 一旦到达 `.get()` 就 500。

## 三、修复内容（最小、定向、Teammates 并行实施）

3 个并行 Teammate 分别落地，lead 整合 + 评审 + 加固：

- **Fix A — 配置 dict 不变式**（`config.py`）：新增 `_ensure_config_dict()` 守卫（`__init__` 末尾调用）；`load_config` 对 YAML 解析结果做 `isinstance(loaded, dict)` 校验，非 dict 回退默认；所有 `self.config = self.default_config` 改为 `copy.deepcopy`（修复 review 发现的 HIGH：引用别名会让 PATCH `/api/config/` 污染 `default_config`）。
- **Fix B — 鉴权鲁棒 + 独立于配置**（`auth.py` + `app.py`）：`load_auth_config` 容忍非 dict 输入（env 变量为唯一可信源）；`lifespan` 拆分为三个独立异常边界，**鉴权无条件初始化**，失败再用 `load_auth_config({})` 兜底（fail-safe，不再 fail-open）。
- **Fix C — 模板目录恒存在**（`path_manager.py` + `templates.py` + `Dockerfile` + `.dockerignore`）：dev 分支 `mkdir`；`iterdir()` 前加 `exists()` 守卫；Dockerfile `COPY knowledge` + 预建目录；`.dockerignore` 放行 `knowledge`。

## 四、验收（全新容器，clean volumes）

| 端点 | 修复前 | 修复后 |
|---|---|---|
| `GET /`（无凭证） | 200（越权） | **401 + `WWW-Authenticate: Basic realm="AIWriteX"`** |
| `GET /`（Basic / X-API-Key） | — | **200** |
| `GET /api/config/`（带凭证） | 500 tuple | **200**（11 平台、api_type 等齐全） |
| `GET /api/templates/categories` | 500 FileNotFoundError | **200**（13 分类） |
| `GET /api/scheduled-tasks/runtime/status` | 500 NoneType | **200** |

防御性自愈实测：在容器内把 `config` 人为污染成 tuple，`_ensure_config_dict` 自动恢复为 dict（含 platforms），`load_auth_config(tuple)` 不再抛异常——**Bug #1/#2 即便历史污染复发也无法再出现**。

## 五、浏览器 E2E（截图见 `docs/issue1-screenshots/`）

| 截图 | 说明 |
|---|---|
| `01-auth-challenge-401.png` | 未携带凭证 → 浏览器收到 401（Bug #1 修复证据） |
| `02-dashboard.png` | 登录后主界面（创意工坊） |
| `03-templates.png` | 模板管理页加载分类（Bug #3 修复证据） |
| `04-config-basic.png` | 基础设置页含「大模型 / API / 模型」（Bug #2 修复证据） |
| `05-article-list.png` | 文章管理列表，含本次生成文章 |
| `05b-article-view.png` | UI 内查看生成文章 |
| `06-generated-article-rendered.png` | 渲染后的 AI 生成文章（AI 任务产物） |

## 六、AI 任务（DeepSeek `deepseek-v4-flash`）

- 直接 API 实测：`deepseek-v4-flash` 在 `https://api.deepseek.com/v1` **有效**（调查 Agent 曾误判其无效，实测推翻）；为带 `reasoning_content` 的推理模型。
- 系统代码路径实测：`crewai.LLM(model="deepseek/deepseek-v4-flash", api_key=KEY)` 正常返回中文内容。
- 经 `PATCH /api/config/` 配置 DeepSeek（证明 Bug #2 修复使真实 AI 可用），`/api/config/validate` → 200。
- `POST /api/generate`（主题「人工智能如何改变普通人的日常生活」）→ **status: completed**，文章保存 `/app/output/article/wechat_人工智能如何改变普通人的日常生活.html`（21.2 KB，正文约 2697 字），文学化「深度访谈」体裁，质量良好。

## 七、Team 并行（多 Agent 加速）

- **Step 1 实现**：3 个 Teammate 并行（config+auth / paths+templates / docker），文件集互不重叠。
- **Step 2 评审**：3 个 Agent 并行（security-reviewer / python-reviewer / 生成流调查）；security 评审结论 fail-safe、无 CRITICAL/HIGH；python 评审发现并已修复 HIGH（deep-copy 别名）。

## 八、回归测试

- 新增 `tests/test_issue1_fixes.py`（AAA 模式）：覆盖 dict 不变式自愈、非 dict YAML 回退、`load_auth_config` 容忍 tuple/None、`get_template_dir` 自动建目录、`lifespan` 配置失败仍初始化鉴权。（注：被测代码用 3.10+ 语法，需在容器内 Python 3.11 运行。）

## 九、改动文件清单

```
Dockerfile                           (+COPY knowledge, +mkdir)
.dockerignore                        (放行 knowledge)
docker-compose.yml                   (移除 obsolete version)
src/ai_write_x/config/config.py      (_ensure_config_dict + load_config 校验 + deepcopy)
src/ai_write_x/web/auth.py           (load_auth_config 容忍非 dict)
src/ai_write_x/web/app.py            (lifespan 拆分异常边界, 鉴权恒初始化)
src/ai_write_x/utils/path_manager.py (dev 分支 mkdir)
src/ai_write_x/web/api/templates.py  (iterdir 守卫)
tests/test_issue1_fixes.py           (新增回归测试)
docs/issue1-screenshots/             (E2E 截图 + 生成文章)
```

## 十、待办 / 建议（非阻塞，来自评审）

- LOW：`.env.example` 仍带占位密码，建议加启动期占位值校验。
- LOW：鉴权失败无速率限制（建议反代或 `slowapi`）。
- MEDIUM：`_resolve_enabled` 的 `cfg_auth` 形参未使用，可清理。
- 运维：发布前 `docker compose build --no-cache` 确保无陈旧层（本次 tuple 即此类残留）。

> 改动均为本地，未提交。需要我按 `fix:` 规范提交并推送可告知。
