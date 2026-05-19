# AIWriteX 定时任务架构说明

> 最后更新: 2026-05-19

---

## 1. 模块目标

定时任务模块用于在应用运行期间，按预设时间自动触发一次现有文章生成链路，并在满足全局配置时沿用现有自动发布流程。

初版目标只有三项：

1. 管理可重复执行的任务定义。
2. 在固定时间或 cron 表达式命中时触发一次生成。
3. 记录任务执行结果，便于前端查看状态与历史。

该模块不负责重写写作工作流，不引入第二套生成入口，也不把当前系统改造成多任务调度平台。

---

## 2. 当前真实执行模型

### 2.1 单任务模型

当前项目的真实执行入口位于 `src/ai_write_x/web/api/generate.py`。

该文件使用模块级全局状态管理运行中的任务：

- `_current_process`
- `_current_log_queue`
- `_task_status`

这意味着当前 Web 应用本身就是单任务模型：任一时刻只允许一个生成任务运行。手动生成、立即执行、定时触发都必须共享这一约束。

### 2.2 空话题热搜只存在于前端创意工坊

空话题时自动获取热搜的逻辑并不在后端通用生成链路中，而是在 `src/ai_write_x/web/static/js/creative-workshop.js` 内部完成：

- 先读取 `#topic-input`
- 若为空，再调用 `GET /api/hot-topics`
- 成功后再向 `POST /api/generate` 发起请求

因此“留空自动热搜”只是创意工坊页面的前端交互，不是后端通用能力。定时任务初版必须要求填写 `topic`，不支持留空后自动补热搜。

### 2.3 auto_publish 由全局 Config 决定

自动发布开关由 `src/ai_write_x/config/config.py` 中的 `Config.auto_publish` 提供，实际执行判断位于 `src/ai_write_x/core/unified_workflow.py::_should_publish()`。

结论：

- 初版定时任务不新增任务级 `auto_publish` 覆盖项。
- 定时任务执行时直接沿用全局 `Config.auto_publish`。
- 前端可以展示“当前生效的自动发布状态”，但不允许在任务表单中单独修改。

---

## 3. 模块边界

### 3.1 定时任务模块负责的内容

建议新增独立业务域 `src/ai_write_x/scheduler/`，职责如下：

| 模块 | 职责 |
|------|------|
| `scheduled_task_models.py` | 任务定义与执行记录数据模型 |
| `scheduled_task_repository.py` | JSON 文件读写 |
| `scheduled_task_service.py` | 任务 CRUD、启停、计算下次执行时间 |
| `scheduled_task_executor.py` | 执行一次任务并写入记录 |
| `scheduled_task_scheduler.py` | 调度器启动、恢复注册、关闭清理 |

### 3.2 不负责的内容

定时任务模块不负责以下事项：

- 重写 `UnifiedContentWorkflow`
- 复制一套新的生成/发布逻辑
- 将当前单任务进程模型升级为并发队列系统
- 引入数据库任务表或多实例协同能力

### 3.3 与现有链路的关系

定时任务执行时必须复用现有生成链路：

```
定时命中 / run-now
    ↓
ScheduledTaskExecutor
    ↓
现有生成入口能力
    ↓
ai_write_x_main(...)
    ↓
UnifiedContentWorkflow.execute()
```

是否通过抽取共享服务来复用 `generate.py` 启动逻辑，可以在实现阶段决定；但架构目标是“共用一条执行链路”，而不是“共存两套入口”。

---

## 4. 生命周期

### 4.1 启动时

在 `src/ai_write_x/web/app.py` 的应用生命周期中完成：

1. 初始化 repository / service / scheduler
2. 读取 JSON 持久化文件
3. 恢复所有 `enabled=true` 的任务注册
4. 将运行时对象挂入应用状态，供 API 调用

### 4.2 运行时

- 调度器只在应用进程存活期间工作
- 任务命中后先检查全局生成互斥状态
- 若当前已有生成任务运行，则本次触发记为 `skipped`
- 若允许执行，则进入现有生成链路

### 4.3 关闭时

应用关闭时需要：

1. 停止调度器
2. 刷新任务定义与执行记录
3. 释放运行时引用

结论：初版不是系统级常驻计划任务系统，软件关闭后不会继续触发。

---

## 5. 串行执行原则

### 5.1 统一互斥规则

初版统一采用“严格串行”原则：

- 手动生成与定时任务互斥
- `run-now` 与定时触发互斥
- 多个定时任务同时到点也互斥

### 5.2 冲突处理策略

推荐初版策略：**冲突即跳过并记录原因**。

原因：

1. 最符合当前 `generate.py` 的全局单任务模型。
2. 不需要额外引入排队系统。
3. 不会把执行状态、日志通道、Config 单例隔离问题复杂化。

执行记录中的 `status` 建议至少包含：

- `idle`
- `running`
- `success`
- `failed`
- `retrying`
- `skipped`

---

## 6. 数据模型

### 6.1 ScheduledTask

| 字段 | 说明 |
|------|------|
| `task_id` | 任务唯一标识 |
| `name` | 任务名称 |
| `topic` | 预设话题，必填 |
| `schedule_type` | `fixed_time` 或 `cron` |
| `time_of_day` | 固定时间模式使用，如 `09:00` |
| `cron_expression` | cron 模式使用 |
| `enabled` | 是否启用 |
| `max_retries` | 最大重试次数 |
| `current_retry_count` | 当前重试次数 |
| `last_run_at` | 最近执行时间 |
| `next_run_at` | 下次计划执行时间 |
| `last_status` | 最近一次状态 |
| `last_error` | 最近一次错误 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

说明：

- `topic` 必填，不支持空值热搜回填。
- 不定义任务级 `auto_publish` 字段。
- 前端若需要展示发布行为，应读取“全局生效状态”。

### 6.2 ScheduledTaskExecutionRecord

| 字段 | 说明 |
|------|------|
| `record_id` | 记录唯一标识 |
| `task_id` | 所属任务 |
| `started_at` | 开始时间 |
| `finished_at` | 完成时间 |
| `status` | 执行结果 |
| `retry_attempt` | 第几次执行/重试 |
| `message` | 简要说明 |
| `article_path` | 生成文件路径，可为空 |
| `published` | 是否进入并完成发布 |

时间字段统一使用 ISO 8601 字符串。

---

## 7. JSON 持久化与 PathManager 落位

初版采用 JSON 文件持久化，不引入 SQLite。

### 7.1 文件落位

建议通过 `PathManager` 新增专用路径方法，并统一落在可写配置目录：

| 文件 | 建议路径 |
|------|----------|
| 任务定义 | `PathManager.get_config_dir() / "scheduled_tasks.json"` |
| 执行记录 | `PathManager.get_config_dir() / "scheduled_task_execution_records.json"` |

这样做的原因：

1. 与当前 `ui_config.json` 的文件型持久化方式一致。
2. 发布版可自动落到用户可写目录。
3. 避免把调度元数据混入文章输出目录。

### 7.2 建议的 PathManager 扩展

建议补充以下方法：

- `get_scheduled_tasks_path()`
- `get_scheduled_task_execution_records_path()`

由 `PathManager` 统一屏蔽开发模式与发布模式的目录差异，不在业务代码中直接拼路径。

---

## 8. 为什么不是多任务系统

不直接把 `generate.py` 改造成多任务系统，原因如下：

1. 当前日志、状态、进程句柄都是全局单例语义。
2. `Config` 为全局单例，直接并发执行会引入配置串值风险。
3. 前端当前只有一套运行中状态展示与日志通道。
4. 本次目标是“定时触发已有能力”，不是“重构整套运行模型”。

因此初版应在现有单任务基础上增量扩展，而不是先做并发调度平台重构。

---

## 9. 为什么初版不用 SQLite

初版不直接引入 SQLite，原因如下：

1. 当前项目已有明显的文件型持久化风格。
2. 任务量和记录量在首版范围内可由 JSON 承担。
3. 单机、单进程、单任务模型下，SQLite 不是刚需。
4. 先落地业务闭环，再决定是否升级为数据库存储，成本更低。

后续若出现以下需求，再考虑升级：

- 大量执行记录分页检索
- 多实例共享任务状态
- 系统级常驻任务
- 更复杂的排队与恢复机制

---

## 10. 架构结论

定时任务模块的首版设计结论如下：

1. 它是对现有单任务生成链路的调度包装，不是新的内容生产系统。
2. 它必须明确要求填写 `topic`，因为空话题热搜只存在于创意工坊前端逻辑。
3. 它必须沿用全局 `Config.auto_publish`，不做任务级覆盖。
4. 它必须采用严格串行执行，冲突时跳过并记录。
5. 它必须使用 JSON + `PathManager` 做轻量持久化，并在 `app.py` 生命周期中完成恢复与清理。
