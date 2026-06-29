"""Generate commands for AIWriteX CLI."""

import time
from typing import Optional
import typer
from ..client import AIWriteXClient
from ..errors import AIWriteXError, ConnectionError
from ..formatters import print_success, print_error, print_info, print_warning, print_status, print_log_line

app = typer.Typer(help="内容生成")

# 单次轮询失败时容忍 N 次再放弃，避免服务端短暂抖动误判任务失败。
_MAX_CONSECUTIVE_ERRORS = 3


def _poll_status(client: AIWriteXClient, timeout: int, interval: float) -> int:
    """轮询 /api/generate/status 直至任务结束或超时。

    返回退出码：0=completed, 1=failed/stopped, 2=timeout。
    单次查询失败不立即放弃，连续 _MAX_CONSECUTIVE_ERRORS 次才返回 1。
    """
    print_info(f"开始轮询任务状态（间隔 {interval}s，超时 {timeout}s）...")
    deadline = time.monotonic() + timeout
    last_status: Optional[str] = None
    consecutive_errors = 0

    while time.monotonic() < deadline:
        try:
            response = client.get_json("/api/generate/status")
            consecutive_errors = 0
        except AIWriteXError as e:
            consecutive_errors += 1
            if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                print_error(f"连续 {consecutive_errors} 次查询失败，放弃: {e}")
                return 1
            print_warning(
                f"查询状态失败（{consecutive_errors}/{_MAX_CONSECUTIVE_ERRORS}），将重试: {e}"
            )
            time.sleep(interval)
            continue

        status = response.get("status", "unknown")
        if status != last_status:
            print_status(status, response.get("error") or status)
            last_status = status

        if status == "completed":
            print_success("任务完成")
            return 0
        if status == "failed":
            print_error(f"任务失败: {response.get('error', '未知错误')}")
            return 1
        if status == "stopped":
            print_warning("任务已停止")
            return 1

        time.sleep(interval)

    print_error(f"轮询超时（{timeout}s）")
    return 2


def _ws_follow(client: AIWriteXClient, timeout: int) -> int:
    """通过 WebSocket 实时跟随任务进度。

    返回退出码：0=completed, 1=failed。
    抛出 ConnectionError 表示握手/传输失败（由上层决定是否降级）。
    抛出 TimeoutError 表示超时未完成。
    """
    print_info("正在连接 WebSocket 日志流...")
    final = client.stream_generate_logs(
        on_message=lambda data: print_log_line(
            data.get("type", "info"),
            data.get("message", ""),
        ),
        timeout=timeout,
    )
    if final == "completed":
        print_success("任务完成")
        return 0
    print_error("任务失败")
    return 1


@app.command()
def run(
    topic: str = typer.Option(..., "--topic", "-t", help="文章主题"),
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="生成模式: prompt|rewrite|template"),
    platform: Optional[str] = typer.Option(None, "--platform", "-P", help="目标平台"),
    urls: Optional[str] = typer.Option(None, "--urls", "-u", help="参考 URL，用 | 分隔"),
    ratio: Optional[int] = typer.Option(30, "--ratio", "-r", help="参考比例 0-100"),
    template_category: Optional[str] = typer.Option(None, "--template-category", "-c", help="模板分类"),
    template_name: Optional[str] = typer.Option(None, "--template-name", "-n", help="模板名称"),
    async_mode: bool = typer.Option(False, "--async", help="异步模式，POST 后立即返回"),
    poll: bool = typer.Option(False, "--poll", help="强制轮询 /api/generate/status"),
    no_fallback: bool = typer.Option(False, "--no-fallback", help="WebSocket 失败时不降级到轮询"),
    timeout: int = typer.Option(600, "--timeout", help="总超时秒数"),
    interval: float = typer.Option(2.0, "--interval", help="轮询间隔秒数（仅 --poll 生效）"),
) -> None:
    """生成内容。默认通过 WebSocket 实时输出进度日志直至任务完成。"""
    client = AIWriteXClient()

    # 构建参考配置
    reference = None
    if urls or (template_category and template_name):
        reference = {"reference_ratio": ratio}
        if urls:
            reference["reference_urls"] = urls
        if template_category:
            reference["template_category"] = template_category
        if template_name:
            reference["template_name"] = template_name

    # 根据 mode 验证参数
    if mode == "prompt" and reference:
        print_error("prompt 模式不需要参考参数")
        raise typer.Exit(1)
    if mode == "rewrite" and not urls:
        print_error("rewrite 模式需要 --urls 参数")
        raise typer.Exit(1)
    if mode == "template" and not (template_category and template_name):
        print_error("template 模式需要 --template-category 和 --template-name 参数")
        raise typer.Exit(1)

    # 提交生成任务
    try:
        response = client.post_json(
            "/api/generate",
            json={
                "topic": topic,
                "platform": platform or "",
                "reference": reference,
            },
        )
    except AIWriteXError as e:
        print_error(f"提交失败: {e}")
        raise typer.Exit(1)

    if response.get("status") != "success":
        print_status(response.get("status", ""), response.get("message", ""))
        raise typer.Exit(1)

    # --async：立即返回，保留旧的 fire-and-forget 行为
    if async_mode:
        print_success(response.get("message", "任务已提交"))
        print_info("使用 `aiwritex generate status` 查询进度，`aiwritex generate stop` 中止")
        return

    # --poll：强制轮询
    if poll:
        raise typer.Exit(_poll_status(client, timeout, interval))

    # 默认：WebSocket 跟随，连接失败则降级到轮询（除非 --no-fallback）
    try:
        exit_code = _ws_follow(client, timeout)
    except TimeoutError as e:
        print_error(str(e))
        raise typer.Exit(2)
    except ConnectionError as e:
        if no_fallback:
            print_error(f"WebSocket 不可用且未启用降级: {e}")
            raise typer.Exit(3)
        print_warning(f"WebSocket 不可用，降级为轮询: {e}")
        exit_code = _poll_status(client, timeout, interval)

    raise typer.Exit(exit_code)


@app.command()
def status() -> None:
    """获取生成状态。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/generate/status")
        print_status(response.get("status"))
    except Exception as e:
        print_error(f"获取状态失败: {e}")
        raise typer.Exit(1)


@app.command()
def stop() -> None:
    """停止当前生成任务。"""
    client = AIWriteXClient()
    try:
        response = client.post_json("/api/generate/stop")
        print_status(response.get("status"), response.get("message", ""))
    except Exception as e:
        print_error(f"停止任务失败: {e}")
        raise typer.Exit(1)


@app.command()
def hot_topics() -> None:
    """获取热搜话题。"""
    client = AIWriteXClient()
    try:
        response = client.get_json("/api/hot-topics")
        platform = response.get("platform", "")
        topic = response.get("topic", "")
        print_success(f"平台: {platform}")
        print_info(f"话题: {topic}")
    except Exception as e:
        print_error(f"获取热搜失败: {e}")
        raise typer.Exit(1)
