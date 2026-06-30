# Issue #2 定时任务状态 E2E 取证说明

本目录由 `docs/issue2-screenshots/run_e2e.py` 生成,针对「定时任务完成后 Web 面板仍显示
『执行中』」的修复,真实捕获三种状态。PNG 与同名 JSON 一一对应(UI 截图 + 该时刻的 /records 响应)。

## 文件清单
- `00-task-manager.png` 定时任务管理视图入口
- `01-failed.png` / `01-failed.json` 失败(Fix2 启动一致性修复产生的 failed 记录)
- `02-running.png` / `02-running.json` 执行中(run-now 触发后瞬时态)
- `03-success.png` / `03-success.json` 完成(生成成功,发布失败 → 未发布)
- `ERROR.txt` / `*-ERROR.txt` 采集异常堆栈(若有)

被驱动任务: `task_2bd4f655`

## 配套真实取证命令(操作员粘贴**真实**容器输出,严禁编造)

# 启动一致性修复(Fix2)+ 任务执行日志
docker logs aiwritex-server 2>&1 | grep -E "一致性修复|开始执行|执行成功|执行失败" | tail -40

# 持久化执行记录(权威证据)
docker compose exec aiwritex cat /app/runtime_config/scheduled_task_execution_records.json

# 任务定义 last_status
docker compose exec aiwritex cat /app/runtime_config/scheduled_tasks.json

## 运行方式
docker run --rm --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/docs/issue2-screenshots:/out" \
  [-e TASK_ID=task_2bd4f655] \
  mcr.microsoft.com/playwright/python:v1.49.0-noble python /out/run_e2e.py

## 本次运行备注
- 控制台错误数: 0
- 终态记录: {'record_id': 'rec_9724c8f1', 'task_id': 'task_2bd4f655', 'started_at': '2026-06-30T16:49:37.839112+08:00', 'finished_at': '2026-06-30T16:54:21.398108+08:00', 'status': 'success', 'retry_attempt': 0, 'message': '发布失败：所有 1 个账号都发布失败', 'article_path': '/app/output/article/AI 驱动的自动化内容生产.html', 'published': False}
