---
name: aiwritex-cli
description: 通过 aiwritex 命令行操作 AIWriteX 服务器,完成 AI 公众号文章生成(提示词/仿写/模板三种模式)、多账号发布、定时自动写作与发布、文章/模板/知识库管理,以及把微信网页文章转换成保留内联样式的可复用模板。凡是用户提到批量生成公众号文章、定时自动写稿发文、仿写参考链接、套用模板写作、把微信文章转成模板、管理知识库或模板,或任何涉及 AIWriteX 内容创作平台的自动化与批量化操作,都应使用本 SKILL——即使用户没有明确说出"aiwritex"或"CLI"。
---

# AIWriteX CLI 操作 SKILL

`aiwritex` 是 AIWriteX 服务器的轻量命令行客户端。AI 助手通过它调用服务器的全部能力(生成、发布、定时任务、模板、知识库、微信文章转换),无需手搓 HTTP 请求。所有命令都是 `aiwritex <资源> <动作> [参数]` 形式,资源名均为复数(`articles`/`templates`/`tasks`)。

## 前置:一次性配置

首次使用,配置服务器地址与凭证(持久化到 `~/.aiwritex/config.yaml`):

```bash
aiwritex config set base_url http://你的服务器:8888
# 二选一:API Key(推荐,适合脚本/CI)
aiwritex config set api_key awx-你的key
# 或 Basic 认证
aiwritex config set username admin
aiwritex config set password 你的密码
```

验证连通:

```bash
aiwritex system health          # 健康检查
aiwritex test-connection        # 综合连通测试
aiwritex config list            # 查看当前配置
```

> 服务器鉴权由部署方配置(环境变量 `AIWRITEX_AUTH_API_KEY` / `AIWRITEX_AUTH_USER` / `AIWRITEX_AUTH_PASSWORD`)。CLI 侧用上面的 `config set` 存对应凭证。

## 命令速查

| 场景 | 命令 |
|------|------|
| 生成(提示词) | `aiwritex generate run --topic "主题"` |
| 生成(仿写) | `aiwritex generate run --topic "主题" --mode rewrite --urls "u1\|u2" --ratio 30` |
| 生成(模板) | `aiwritex generate run --topic "主题" --mode template --template-category TechDigital --template-name xxx` |
| 生成(异步,不阻塞) | `aiwritex generate run --topic "主题" --async` |
| 查生成状态 | `aiwritex generate status` |
| 热搜选题 | `aiwritex generate hot-topics` |
| 文章列表 | `aiwritex articles list` |
| 查公众号账号 | `aiwritex articles accounts [-v]` |
| 发布文章 | `aiwritex articles publish --article-paths /path/a.html --account-indices 0 --platform wechat` |
| 模板列表 | `aiwritex templates list` |
| 建模板 | `aiwritex templates create --name N --category C --content-file tpl.html` |
| 定时任务 | `aiwritex tasks create --name N --topic T --schedule-type fixed_time --time-of-day 09:00` |
| 微信转模板 | `aiwritex convert wechat --url "https://mp.weixin.qq.com/s/xxx" --output-type template --category TechDigital --name tpl` |
| 知识库统计 | `aiwritex knowledge stats` |
| 加文本知识 | `aiwritex knowledge text-create --title T --content C --tags "AI,技术" --category 科技` |
| 读服务端配置 | `aiwritex server-config get [-s dimensional_creative]` |
| 改 LLM Key | `aiwritex server-config llm set-key OpenRouter sk-or-v1-xxx` |
| 切换 LLM | `aiwritex server-config llm switch Deepseek` |
| 切 LLM 模型 | `aiwritex server-config llm use-model OpenRouter 2` |
| 创意总览 | `aiwritex server-config creative show` |
| 启用创意维度 | `aiwritex server-config creative enable emotion,culture` |
| 选创意预设 | `aiwritex server-config creative pick style poetry` |
| 导出/导入配置 | `aiwritex server-config export -f cfg.yaml` / `import -f cfg.yaml` |

## 核心命令详解

### 1. AI 生成文章(generate)

`generate run` 支持三种模式,由 `--mode` 显式指定或由参数自动判定:

```bash
# 提示词模式:仅给主题(默认)
aiwritex generate run --topic "2026 年 AI 编程趋势" --platform 微博

# 仿写模式:参考若干 URL,按比例借鉴
aiwritex generate run \
  --topic "AI 编程趋势" \
  --mode rewrite \
  --urls "https://a.com/1|https://b.org/2" \
  --ratio 30 \
  --platform 微博

# 模板模式:套用已有模板
aiwritex generate run \
  --topic "AI 编程趋势" \
  --mode template \
  --template-category TechDigital \
  --template-name 爆款开头
```

生成在服务器后台异步执行。默认行为是 **CLI 阻塞到完成**:通过 WebSocket 实时拉取进度日志并打印,WebSocket 不可用时自动降级为 2 秒一次的轮询。

```bash
aiwritex generate status    # running / completed / failed
aiwritex generate stop      # 中止当前生成
```

进阶选项(`generate run`):

- `--async`:不阻塞,提交后立即返回,自行用 `generate status` 轮询。
- `--poll`:强制走轮询,跳过 WebSocket。
- `--no-fallback`:WebSocket 连接失败时不降级,直接报错退出(退出码 3)。
- `--timeout 600`:最大等待秒数,超时退出码 2。
- `--interval 2.0`:轮询间隔秒。

退出码:0=completed,1=failed(含鉴权/参数错误),2=超时,3=WebSocket 失败且 `--no-fallback`。

### 2. 发布文章(articles publish)

```bash
# 单篇发布到第一个微信账号
aiwritex articles publish \
  --article-paths /app/output/文章.html \
  --account-indices 0 \
  --platform wechat

# 批量发布到多个账号(逗号分隔)
aiwritex articles publish \
  --article-paths a.html,b.html \
  --account-indices 0,1 \
  --platform wechat
```

账号索引自 0,发布前用 `aiwritex articles accounts` 查看 index 对应哪个公众号:

```bash
aiwritex articles accounts        # 列出所有已配置微信账号(Index/Author/AppID 脱敏/群发/状态)
aiwritex articles accounts -v     # 显示完整 appid(默认仅前 6 + 后 4 位)
```

未配置或 `appid/appsecret` 为空的账号会标记「缺 key」,需先用 `aiwritex server-config set wechat '{"credentials":[...]}'` 或直接改服务端配置补全。

### 3. 定时任务(tasks)— 支持完整生成配置

定时任务可配置为提示词、仿写或模板模式(字段与 `generate run` 对齐):

```bash
# 每日 9 点,提示词模式 + 自动发布
aiwritex tasks create \
  --name "每日科技" \
  --topic "科技要闻" \
  --schedule-type fixed_time \
  --time-of-day 09:00 \
  --enabled \
  --auto-publish

# Cron 表达式 + 仿写模式
aiwritex tasks create \
  --name "每周仿写" \
  --topic "AI 周报" \
  --schedule-type cron \
  --cron "0 9 * * 1" \
  --urls "https://a.com|https://b.org" \
  --ratio 40 \
  --platform 微博 \
  --enabled
```

管理:

```bash
aiwritex tasks list                          # 全部任务
aiwritex tasks run-now <task_id>             # 立即执行(测试用)
aiwritex tasks toggle <task_id> --disabled   # 启停
aiwritex tasks records <task_id>             # 执行历史
aiwritex tasks delete <task_id>
```

Cron 用标准 5 段格式 `分 时 日 月 周`:`0 9 * * 1` = 每周一 9 点。

### 4. 微信文章转换(convert wechat)

把微信公众号文章转成**仅保留内联样式、去除外部 JS/CSS 与广告组件**的自包含 HTML,图片下载到本地。可输出为模板或文章:

```bash
# URL → 模板(可被 generate --mode template 复用)
aiwritex convert wechat \
  --url "https://mp.weixin.qq.com/s/xxx" \
  --output-type template \
  --category TechDigital \
  --name 爆款样式

# URL → 文章(直接进文章库)
aiwritex convert wechat \
  --url "https://mp.weixin.qq.com/s/xxx" \
  --output-type article \
  --name 我的文章

# 本地 HTML 文件 → 文章
aiwritex convert wechat --html-file local.html --output-type article --name x

# 异步(立即返回 task_id,不阻塞)
aiwritex convert wechat --url "..." --output-type template --category C --name N --async
```

默认同步阻塞直到转换完成(含网络抓取与图片下载,耗时较长)。`--async` 立即返回 task_id。

### 5. 模板与知识库(templates / knowledge)

```bash
# 模板
aiwritex templates list [--category TechDigital]
aiwritex templates categories
aiwritex templates create --name N --category C --content "HTML..."   # 或 --content-file f.html
aiwritex templates get --path <path>
aiwritex templates delete <path>

# 文本知识库
aiwritex knowledge text-list [--category 科技] [--search AI] [--limit 20]
aiwritex knowledge text-create --title T --content C [--summary S] [--tags "AI,技术"] [--category 科技]
aiwritex knowledge text-get <id>
aiwritex knowledge text-delete <id>

# 图片知识库
aiwritex knowledge image-list
aiwritex knowledge image-upload --file img.jpg [--description D] [--tags "图,标"] [--category C]
aiwritex knowledge image-delete <id>

# 统计与刷新
aiwritex knowledge stats
aiwritex knowledge refresh
```

### 6. 服务端配置(server-config)

`server-config` 让 CLI 能管理**服务端业务配置**(LLM Key、模型切换、创意维度、文章格式等),能力与 Web 设置页对齐。**所有写命令末尾自动落盘**(对齐 Web UI 行为),无需手动 save。

底层通用(5 个):

```bash
aiwritex server-config get                              # 读全量配置(JSON)
aiwritex server-config get -s dimensional_creative      # 按 section 过滤
aiwritex server-config set article_format '"markdown"'  # PATCH 单字段 + 落盘
aiwritex server-config set wechat '{"credentials":[...]}'  # PATCH 整段 + 落盘(JSON 字符串)
aiwritex server-config export -f cfg.yaml               # 导出全量到文件(默认 stdout)
aiwritex server-config import -f cfg.yaml               # 整批 PATCH + 落盘
aiwritex server-config reset --yes                      # 拉默认配置覆盖写回(不可逆)
```

LLM 管理(4 个,高层语义):

```bash
aiwritex server-config llm list                         # 表格:provider / keys / 当前模型 / 是否当前
aiwritex server-config llm list -p OpenRouter           # 详情:列出该 provider 全部模型与 key 数
aiwritex server-config llm set-key OpenRouter sk-or-v1-xxx   # 设 key + 落盘
aiwritex server-config llm switch Deepseek              # 切换 api_type(切换主 LLM 提供商)
aiwritex server-config llm use-model OpenRouter 2       # 切换到该 provider 的 model[2]
```

创意维度(11 个,5 分组 / 15 维度,与 Web 设置页严格对齐):

```bash
aiwritex server-config creative show                    # 总览:开关/强度/启用维度数
aiwritex server-config creative groups                  # 列出 5 个分组(文体/文化/角色/结构/受众)
aiwritex server-config creative list                    # 全维度表格:key/中文名/启用/当前选择
aiwritex server-config creative list -g expression      # 仅看「文体表达维度」组
aiwritex server-config creative enable emotion,culture  # 启用维度(可逗号分隔多个)
aiwritex server-config creative disable emotion         # 禁用维度
aiwritex server-config creative options style           # 列出某维度的全部预设选项 + 当前选中
aiwritex server-config creative pick style poetry       # 选中预设(自动清空 custom)
aiwritex server-config creative custom style "口语化"   # 自定义(需 allow_custom=true,自动清空 selected)
aiwritex server-config creative config get              # 全局字段表(7 项:总开关/强度/自动选择/上限等)
aiwritex server-config creative config set auto_dimension_selection false   # 关闭自动维度选择
```

> **依赖约束(对齐 Web)**:`auto_dimension_selection=true` 时,系统按上下文自动选维度,`enable/disable/pick/custom` 会被拒绝。需先 `creative config set auto_dimension_selection false` 切到手动模式,或加 `--force` 强制执行。

完整合法维度 key(15):`style culture time personality emotion format scene audience theme technique language tone perspective structure rhythm`。完整合法分组(5):`expression culture character structure audience`。

## 典型工作流

### 工作流 A:生成 → 发布

```bash
aiwritex generate run --topic "AI 编程的未来" --platform 微博
aiwritex generate status                       # 轮询直到 completed
aiwritex articles list                         # 取最新文章路径
aiwritex articles publish --article-paths /app/output/xxx.html --account-indices 0
```

### 工作流 B:微信爆款 → 模板 → 批量套用

```bash
# 1. 把一篇爆款微信文章转成模板
aiwritex convert wechat --url "https://mp.weixin.qq.com/s/xxx" \
  --output-type template --category TechDigital --name 爆款版式
# 2. 用该模板批量生成
aiwritex generate run --topic "主题1" --mode template \
  --template-category TechDigital --template-name 爆款版式
```

### 工作流 C:定时自动写作 + 自动发布

```bash
aiwritex tasks create --name "每日早报" --topic "科技要闻" \
  --schedule-type fixed_time --time-of-day 09:00 --enabled --auto-publish
# 次日查看执行结果
aiwritex tasks list
aiwritex tasks records <task_id>
```

### 工作流 D:首次部署 → 配 LLM → 生成

```bash
# 1. 配好连接(假设服务器已启动)
aiwritex config set base_url http://127.0.0.1:8888
aiwritex config set api_key awx-你的key
aiwritex test-connection

# 2. 配 LLM(全程 CLI,无需开 Web)
aiwritex server-config llm set-key OpenRouter sk-or-v1-xxx
aiwritex server-config llm switch OpenRouter
aiwritex server-config llm use-model OpenRouter 0       # 选第 0 个模型

# 3. 开 2 个创意维度(先关自动选择)
aiwritex server-config creative config set auto_dimension_selection false
aiwritex server-config creative enable emotion,style

# 4. 生成
aiwritex generate run --topic "AI 编程趋势"
```

## 常见错误

| 现象 | 排查 |
|------|------|
| `401 Unauthorized` | `aiwritex config list` 确认 api_key 或 username/password 与服务器 `AIWRITEX_AUTH_*` 一致 |
| `ConnectionError` | `aiwritex system health` 检查服务器;确认 base_url 与端口(默认 8888) |
| 生成一直 running | `aiwritex generate status`;查服务器日志是否缺 LLM api_key;必要时 `generate stop` |
| convert 超时 | 加 `--timeout 60 --retries 5`;或 `--async` 后台执行 |
| Cron 不触发 | 用标准 5 段 `分 时 日 月 周`;`tasks get <id>` 看下次执行时间 |
| 发布失败 | `articles publish` 返回含 error_details;确认微信 appid/appsecret 已配置、账号索引正确 |

## 参数速查(常用)

- `generate run`:`--topic/-t`(必填) `--mode/-m` `--platform/-P` `--urls/-u`(仿写) `--ratio/-r`(仿写,0-100) `--template-category/-c`(模板) `--template-name/-n`(模板) `--async`(不阻塞) `--poll`(强制轮询) `--no-fallback` `--timeout` `--interval`
- `articles publish`:`--article-paths/-p`(必填,逗号分隔) `--account-indices/-a`(必填,逗号分隔) `--platform/-P`
- `articles accounts`:`--verbose/-v`(显示完整 appid)
- `tasks create`:`--name/-n` `--topic/-t` `--schedule-type/-s` `--time-of-day/-T` `--cron/-c` `--enabled/--disabled` `--auto-publish` `--platform/-P` `--urls/-u` `--ratio` `--template-category/-C` `--template-name/-N`
- `convert wechat`:`--url/-u`(必填) `--output-type/-o` `--category/-c` `--name/-n` `--timeout` `--retries/-r` `--html-file/-f` `--async`
- `server-config get`:`--section/-s`(api/dimensional_creative/wechat/...)
- `server-config set`:`<section> <json>`(JSON 字符串)
- `server-config export/import`:`--file/-f`(必填,import;export 默认 stdout)
- `server-config reset`:`--yes`(跳过确认)
- `server-config llm list`:`--provider/-p`(详情模式)
- `server-config llm set-key`:`<provider> <key>`
- `server-config llm switch`:`<provider>`(OpenRouter/Deepseek/Grok/Claude/Qwen/Gemini/Ollama/SiliconFlow/Kimi/GLM/MiniMax)
- `server-config llm use-model`:`<provider> <index>`
- `server-config creative list`:`--group/-g`(expression/culture/character/structure/audience)
- `server-config creative enable/disable`:`<dim1,dim2,...>` `--force`
- `server-config creative options/pick/custom`:`<dim>` + 选项 key / 自定义文本;`--force`

> 完整参数见 `aiwritex <命令> --help`;完整 REST API 见 `docs/api-reference.md`;部署见 `docs/deployment.md`。
