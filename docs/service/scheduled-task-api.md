# AIWriteX 定时任务 API 说明

> 最后更新: 2026-06-30

---

## 1. 设计目标

定时任务 API 提供任务管理、启停控制、立即执行和执行记录查询能力。

首版 API 必须遵守当前项目的真实约束：

- 当前系统是单任务模型
- 空话题自动热搜不是后端通用能力
- 自动发布由任务级 `auto_publish` 控制(任务级独占,见 §3.2)
- 任务定义与执行记录采用 JSON 持久化

建议新增路由文件：`src/ai_write_x/web/api/scheduled_tasks.py`。

建议路由前缀：`/api/scheduled-tasks`。

---

## 2. 与现有 API 风格对齐

当前项目 API 使用 FastAPI + Pydantic，并采用显式 `include_router(...)` 接入 `src/ai_write_x/web/app.py`。

定时任务 API 需要保持一致：

- 在路由文件中声明 `APIRouter(prefix="/api/scheduled-tasks", tags=["scheduled-tasks"])`
- 在 `src/ai_write_x/web/app.py` 中显式注册
- 返回结构保持现有项目常用风格：`status`、`message`、`data` 组合

建议成功响应统一形态：

```json
{
  "status": "success",
  "message": "操作成功",
  "data": {}
}
```

建议错误响应继续使用 FastAPI `HTTPException`，并在 `detail` 中给出可直接显示给前端的中文提示。

---

## 3. 关键约束

### 3.1 topic 必填

任务创建和更新时，`topic` 必须是非空字符串。

原因：当前空话题自动热搜逻辑只存在于 `src/ai_write_x/web/static/js/creative-workshop.js`，由创意工坊页面在调用生成接口前先行补全。后端任务调度层没有这一步，因此不能把空 topic 视为合法输入。

### 3.2 任务级 auto_publish(1.1.4 起,任务级独占)

任务接口接受 `auto_publish: bool` 字段(默认 `False`)。

发布行为由任务级开关决定:

- `ScheduledTaskExecutor._build_config_data()` 将 `task.auto_publish` 放入 `config_data`
- 子进程内经 `apply_config_data(override_auto_publish=True)` 写入 `config.config["auto_publish"]`
- 由 `UnifiedContentWorkflow._should_publish()` 据此判断是否发布(仍校验全局微信凭据)

语义:`auto_publish=True`→生成后发布;`False`→仅生成。全局 `Config.auto_publish` 对定时任务不再起作用(仍对手动生成生效)。执行记录的 `published` 字段如实反映本次是否真正发布。

### 3.3 单任务互斥

所有执行入口都必须校验当前是否已有生成任务运行。

冲突时返回 409，而不是并发执行。

---

## 4. 数据结构

### 4.1 ScheduledTask

```json
{
  "task_id": "task_001",
  "name": "每日科技资讯",
  "topic": "人工智能最新进展",
  "schedule_type": "fixed_time",
  "time_of_day": "09:00",
  "cron_expression": null,
  "enabled": true,
  "max_retries": 3,
  "current_retry_count": 0,
  "last_run_at": null,
  "next_run_at": "2026-05-20T09:00:00+08:00",
  "last_status": "idle",
  "last_error": null,
  "created_at": "2026-05-19T10:00:00+08:00",
  "updated_at": "2026-05-19T10:00:00+08:00"
}
```

### 4.2 ScheduledTaskExecutionRecord

```json
{
  "record_id": "record_001",
  "task_id": "task_001",
  "started_at": "2026-05-20T09:00:00+08:00",
  "finished_at": "2026-05-20T09:03:10+08:00",
  "status": "success",
  "retry_attempt": 0,
  "message": null,
  "article_path": "output/article/example.html",
  "published": true
}
```

---

## 5. 请求模型建议

### 5.1 CreateScheduledTaskRequest

```json
{
  "name": "每日科技资讯",
  "topic": "人工智能最新进展",
  "schedule_type": "fixed_time",
  "time_of_day": "09:00",
  "cron_expression": null,
  "enabled": true,
  "max_retries": 3
}
```

校验要求：

- `name` 必填
- `topic` 必填，去除首尾空白后不能为空
- `schedule_type` 仅允许 `fixed_time` 或 `cron`
- `fixed_time` 模式下必须提供 `time_of_day`
- `cron` 模式下必须提供 `cron_expression`
- `max_retries` 建议限制在 0~3 或 0~5 的小范围内

### 5.2 UpdateScheduledTaskRequest

```json
{
  "name": "每日科技资讯-更新版",
  "topic": "AI 应用落地案例",
  "schedule_type": "fixed_time",
  "time_of_day": "10:00",
  "cron_expression": null,
  "enabled": true,
  "max_retries": 2
}
```

更新时仍需完整校验，不允许把 `topic` 更新为空。

---

## 6. 路由清单

### 6.1 获取任务列表

`GET /api/scheduled-tasks`

返回所有任务定义，供列表页渲染。

响应示例：

```json
{
  "status": "success",
  "data": {
    "tasks": [
      {
        "task_id": "task_001",
        "name": "每日科技资讯",
        "topic": "人工智能最新进展",
        "schedule_type": "fixed_time",
        "time_of_day": "09:00",
        "cron_expression": null,
        "enabled": true,
        "max_retries": 3,
        "current_retry_count": 0,
        "last_run_at": null,
        "next_run_at": "2026-05-20T09:00:00+08:00",
        "last_status": "idle",
        "last_error": null,
        "created_at": "2026-05-19T10:00:00+08:00",
        "updated_at": "2026-05-19T10:00:00+08:00"
      }
    ]
  }
}
```

### 6.2 创建任务

`POST /api/scheduled-tasks`

请求体：`CreateScheduledTaskRequest`

响应示例：

```json
{
  "status": "success",
  "message": "定时任务创建成功",
  "data": {
    "task": {
      "task_id": "task_001",
      "name": "每日科技资讯",
      "topic": "人工智能最新进展",
      "schedule_type": "fixed_time",
      "time_of_day": "09:00",
      "cron_expression": null,
      "enabled": true,
      "max_retries": 3,
      "current_retry_count": 0,
      "last_run_at": null,
      "next_run_at": "2026-05-20T09:00:00+08:00",
      "last_status": "idle",
      "last_error": null,
      "created_at": "2026-05-19T10:00:00+08:00",
      "updated_at": "2026-05-19T10:00:00+08:00"
    }
  }
}
```

### 6.3 获取任务详情

`GET /api/scheduled-tasks/{task_id}`

用于编辑表单回填或详情展示。

### 6.4 更新任务

`PUT /api/scheduled-tasks/{task_id}`

请求体：`UpdateScheduledTaskRequest`

用于修改名称、话题、时间、启用状态、重试次数等。

### 6.5 删除任务

`DELETE /api/scheduled-tasks/{task_id}`

删除任务定义，并取消其调度注册。

响应示例：

```json
{
  "status": "success",
  "message": "定时任务删除成功"
}
```

### 6.6 启用或禁用任务

`POST /api/scheduled-tasks/{task_id}/toggle`

请求体建议：

```json
{
  "enabled": true
}
```

说明：

- `enabled=true` 时重新注册调度
- `enabled=false` 时取消注册，但保留任务定义与执行历史

### 6.7 立即执行任务

`POST /api/scheduled-tasks/{task_id}/run-now`

该接口必须遵守当前单任务互斥规则。

成功响应示例：

```json
{
  "status": "success",
  "message": "任务已开始执行",
  "data": {
    "task_id": "task_001"
  }
}
```

冲突响应示例：

```json
{
  "detail": "当前已有生成任务运行，无法立即执行定时任务"
}
```

### 6.8 获取任务执行记录

`GET /api/scheduled-tasks/{task_id}/records`

响应示例：

```json
{
  "status": "success",
  "data": {
    "task_id": "task_001",
    "records": [
      {
        "record_id": "record_001",
        "task_id": "task_001",
        "started_at": "2026-05-20T09:00:00+08:00",
        "finished_at": "2026-05-20T09:03:10+08:00",
        "status": "success",
        "retry_attempt": 0,
        "message": null,
        "article_path": "output/article/example.html",
        "published": true
      }
    ]
  }
}
```

### 6.9 获取运行时状态

`GET /api/scheduled-tasks/runtime/status`

用于前端显示调度器运行状态、当前运行任务和全局自动发布状态。

响应示例：

```json
{
  "status": "success",
  "data": {
    "scheduler_status": "running",
    "current_running_task": null,
    "generate_status": "idle",
    "global_auto_publish": false,
    "tasks_count": 3,
    "enabled_tasks_count": 2
  }
}
```

其中：

- `generate_status` 应反映当前全局生成状态
- `global_auto_publish` 直接反映 `Config.auto_publish`
- `current_running_task` 为当前定时任务上下文，没有则为 `null`

---

## 7. 错误码约定

### 400 Bad Request

用于请求参数不合法，例如：

- `topic` 为空
- `schedule_type` 非法
- `time_of_day` 格式错误
- `cron_expression` 格式错误

示例：

```json
{
  "detail": "topic 不能为空，定时任务初版必须填写预设话题"
}
```

### 404 Not Found

用于任务不存在。

```json
{
  "detail": "定时任务不存在"
}
```

### 409 Conflict

用于与当前单任务模型冲突，例如：

- 当前已有生成任务运行
- 当前目标任务已在运行中

```json
{
  "detail": "当前已有生成任务运行，暂不支持并发执行"
}
```

### 500 Internal Server Error

用于持久化失败、调度器异常、执行启动失败等服务端错误。

```json
{
  "detail": "定时任务执行启动失败"
}
```

---

## 8. 执行与重试约定

### 8.1 跳过策略

当任务命中时，如发现当前已有手动生成或其他定时任务正在运行：

- 本次执行不排队
- 直接记为 `skipped`
- 在执行记录中写明原因

### 8.2 重试策略

重试只用于“执行失败”，不用于“互斥跳过”。

推荐：

- 最多重试 3 次
- 延迟 30s → 60s → 120s
- 每次重试单独写入一条执行记录或明确更新重试字段

---

## 9. 前端调用方式

前端管理器建议统一使用 `fetch`，风格与现有 `creative-workshop.js`、`config-manager.js` 保持一致。

典型调用流程：

### 9.1 页面初始化

1. 调 `GET /api/scheduled-tasks`
2. 调 `GET /api/scheduled-tasks/runtime/status`
3. 渲染任务列表与顶部状态区

### 9.2 新建任务

1. 表单校验 `topic` 非空
2. 调 `POST /api/scheduled-tasks`
3. 成功后刷新列表

### 9.3 立即执行

1. 点击“立即执行”
2. 调 `POST /api/scheduled-tasks/{task_id}/run-now`
3. 若返回 409，则提示“当前已有任务运行”
4. 若成功，则刷新运行时状态与记录列表

### 9.4 查看记录

1. 选中任务
2. 调 `GET /api/scheduled-tasks/{task_id}/records`
3. 渲染执行记录区域

---

## 10. API 结论

定时任务 API 首版必须坚持以下原则：

1. 所有任务都必须填写 `topic`，不支持空值热搜补全。
2. 任务级 `auto_publish` 字段以任务级独占语义控制是否发布(1.1.4 起)。
3. 所有执行入口都必须遵守当前单任务互斥模型。
4. 路由以独立业务域形式接入，但执行链路必须复用现有生成能力。
5. 所有数据最终落在 JSON 持久化文件中，并通过 `PathManager` 统一定位。
