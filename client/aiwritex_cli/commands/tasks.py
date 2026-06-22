"""Tasks commands for AIWriteX CLI."""

from typing import Optional
import typer
from ..client import AIWriteXClient
from ..formatters import print_success, print_error, print_info, print_table

app = typer.Typer(help="定时任务管理")


@app.command()
def list() -> None:
    """列出所有定时任务。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/scheduled-tasks/")
        data = response.get("data", {}).get("tasks", [])
        rows = [
            [
                item.get("id", ""),
                item.get("name", ""),
                item.get("topic", ""),
                item.get("schedule_type", ""),
                str(item.get("enabled", False)),
            ]
            for item in data
        ]
        print_table(["ID", "名称", "话题", "调度类型", "启用"], rows)
    except Exception as e:
        print_error(f"获取任务列表失败: {e}")
        raise typer.Exit(1)


@app.command()
def get(task_id: str) -> None:
    """获取任务详情。"""
    client = AIWriteXClient()
    try:
        response = client.get_json(f"/api/scheduled-tasks/{task_id}")
        print_info(f"任务: {response.get('data', {}).get('name', '')}")
        print_info(f"话题: {response.get('data', {}).get('topic', '')}")
        print_info(f"状态: {'启用' if response.get('data', {}).get('enabled') else '停用'}")
    except Exception as e:
        print_error(f"获取任务详情失败: {e}")
        raise typer.Exit(1)


@app.command()
def delete(task_id: str) -> None:
    """删除任务。"""
    client = AIWriteXClient()
    try:
        response = client.delete_json(f"/api/scheduled-tasks/{task_id}")
        print_success(response.get("message", "任务已删除"))
    except Exception as e:
        print_error(f"删除任务失败: {e}")
        raise typer.Exit(1)


@app.command()
def toggle(
    task_id: str,
    enabled: bool = typer.Option(False, "--enabled", help="启用任务"),
    disabled: bool = typer.Option(False, "--disabled", help="停用任务"),
) -> None:
    """切换任务启用状态。"""
    if enabled and disabled:
        print_error("--enabled 和 --disabled 不能同时使用")
        raise typer.Exit(1)
    if not enabled and not disabled:
        print_error("必须使用 --enabled 或 --disabled")
        raise typer.Exit(1)

    client = AIWriteXClient()
    try:
        response = client.post_json(
            f"/api/scheduled-tasks/{task_id}/toggle",
            json={"enabled": enabled},
        )
        print_success(response.get("message", "任务状态已更新"))
    except Exception as e:
        print_error(f"切换任务状态失败: {e}")
        raise typer.Exit(1)


@app.command()
def run_now(task_id: str) -> None:
    """立即运行任务。"""
    client = AIWriteXClient()
    try:
        response = client.post_json(f"/api/scheduled-tasks/{task_id}/run-now")
        print_success(response.get("message", "任务已开始执行"))
    except Exception as e:
        print_error(f"执行任务失败: {e}")
        raise typer.Exit(1)


@app.command()
def records(task_id: str) -> None:
    """获取任务执行记录。"""
    client = AIWriteXClient()
    try:
        response = client.get_json(f"/api/scheduled-tasks/{task_id}/records")
        data = response.get("data", {}).get("records", [])
        rows = [
            [
                item.get("timestamp", ""),
                str(item.get("success", False)),
                item.get("error_message", ""),
            ]
            for item in data
        ]
        print_table(["时间", "成功", "错误信息"], rows)
    except Exception as e:
        print_error(f"获取执行记录失败: {e}")
        raise typer.Exit(1)


@app.command()
def create(
    name: str = typer.Option(..., "--name", "-n", help="任务名称"),
    topic: str = typer.Option(..., "--topic", "-t", help="文章话题"),
    schedule_type: str = typer.Option("fixed_time", "--schedule-type", "-s", help="调度类型: fixed_time|cron"),
    time_of_day: Optional[str] = typer.Option(None, "--time-of-day", "-T", help="固定时间 HH:MM"),
    cron: Optional[str] = typer.Option(None, "--cron", "-c", help="Cron 表达式"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="是否启用"),
    auto_publish: bool = typer.Option(False, "--auto-publish", help="是否自动发布"),
    max_retries: int = typer.Option(3, "--max-retries", "-r", help="最大重试次数"),
    platform: Optional[str] = typer.Option(None, "--platform", "-P", help="目标平台"),
    urls: Optional[str] = typer.Option(None, "--urls", "-u", help="参考 URL，用 | 分隔"),
    ratio: Optional[int] = typer.Option(30, "--ratio", help="参考比例 0-100"),
    template_category: Optional[str] = typer.Option(None, "--template-category", "-C", help="模板分类"),
    template_name: Optional[str] = typer.Option(None, "--template-name", "-N", help="模板名称"),
) -> None:
    """创建定时任务。"""
    client = AIWriteXClient()

    # 验证调度参数
    if schedule_type == "fixed_time" and not time_of_day:
        print_error("fixed_time 模式需要 --time-of-day 参数")
        raise typer.Exit(1)
    if schedule_type == "cron" and not cron:
        print_error("cron 模式需要 --cron 参数")
        raise typer.Exit(1)

    try:
        response = client.post_json(
            "/api/scheduled-tasks/",
            json={
                "name": name,
                "topic": topic,
                "schedule_type": schedule_type,
                "time_of_day": time_of_day,
                "cron_expression": cron,
                "enabled": enabled,
                "auto_publish": auto_publish,
                "max_retries": max_retries,
            },
        )
        print_success(response.get("message", "任务已创建"))
    except Exception as e:
        print_error(f"创建任务失败: {e}")
        raise typer.Exit(1)
