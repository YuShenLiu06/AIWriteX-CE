"""服务端配置命令组入口：5 个底层通用命令 + 注册 llm/creative 子 app。"""

from typing import Optional

import typer

from ...client import AIWriteXClient
from ...errors import AIWriteXError
from ...formatters import (
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    print_json,
)
from ._common import (
    app,
    EP_CONFIG,
    EP_CONFIG_DEFAULT,
    _patch_and_save,
)


@app.command()
def get(
    section: Optional[str] = typer.Option(
        None, "--section", "-s", help="只读取某个 section（如 api、dimensional_creative）"
    ),
) -> None:
    """读取服务端配置（默认全部，可选 section 过滤）。"""
    client = AIWriteXClient()
    try:
        response = client.get_json(EP_CONFIG)
        data = response.get("data", {})
        if section and section not in data:
            print_warning(f"section '{section}' 不存在，返回全部配置")
            result = data
        else:
            result = data.get(section, data) if section else data
        print_json(result)
    except AIWriteXError as e:
        print_error(f"读取配置失败: {e}")
        raise typer.Exit(1)


@app.command("set")
def set_(
    section: str = typer.Argument(
        ...,
        help="顶层 section 名或点号路径（如 article_format / api.OpenRouter.api_key）",
    ),
    value: str = typer.Argument(
        ...,
        help='该字段的新值，JSON 字符串（如 \'"markdown"\' / \'true\' / \'["xxx"]\' / \'{"key":1}\'）',
    ),
) -> None:
    """通用配置写入：支持点号路径嵌套（a.b.c → {a:{b:{c:v}}}），PATCH + 自动落盘。"""
    import json as _json

    try:
        parsed = _json.loads(value)
    except _json.JSONDecodeError as e:
        print_error(f"无法解析 JSON 值: {e}")
        raise typer.Exit(1)

    # 点号路径 → 嵌套 dict；单段（无点号）保持 {section: parsed} 兼容旧用法。
    payload: object = parsed
    for key in reversed(section.split(".")):
        payload = {key: payload}

    client = AIWriteXClient()
    try:
        _patch_and_save(client, payload)
        print_success(f"已更新 {section} 并落盘")
    except AIWriteXError as e:
        print_error(f"更新配置失败: {e}")
        raise typer.Exit(1)


@app.command()
def export(
    file: Optional[str] = typer.Option(
        None, "--file", "-f", help="输出文件路径，不指定则打印到 stdout"
    ),
) -> None:
    """导出完整服务端配置为 YAML。"""
    import yaml

    client = AIWriteXClient()
    try:
        response = client.get_json(EP_CONFIG)
        data = response.get("data", {})
        text = yaml.safe_dump(
            data, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
        if file:
            import pathlib

            pathlib.Path(file).write_text(text, encoding="utf-8")
            print_success(f"已导出到 {file}")
        else:
            # 直接打到 stdout，避免 rich 着色破坏 YAML
            import sys

            sys.stdout.write(text)
    except AIWriteXError as e:
        print_error(f"导出失败: {e}")
        raise typer.Exit(1)


@app.command("import")
def import_(
    file: str = typer.Option(..., "--file", "-f", help="要导入的 YAML 文件路径"),
) -> None:
    """从 YAML 文件导入配置（PATCH 整批 + 自动落盘）。"""
    import pathlib
    import yaml

    p = pathlib.Path(file)
    if not p.exists():
        print_error(f"文件不存在: {file}")
        raise typer.Exit(1)
    try:
        payload = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        print_error(f"YAML 解析失败: {e}")
        raise typer.Exit(1)
    if not isinstance(payload, dict):
        print_error("YAML 顶层必须是字典/映射")
        raise typer.Exit(1)
    client = AIWriteXClient()
    try:
        _patch_and_save(client, payload)
        print_success(f"已导入 {len(payload)} 个 section 并落盘")
    except AIWriteXError as e:
        print_error(f"导入失败: {e}")
        raise typer.Exit(1)


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认提示"),
) -> None:
    """将已知字段恢复为默认值（不删除 default 未列出的自定义 section；不可逆）。"""
    if not yes:
        confirm = typer.confirm(
            "此操作将已知字段覆盖为默认值（不删除自定义 section），确认继续？",
            default=False,
        )
        if not confirm:
            print_warning("已取消")
            raise typer.Exit()
    client = AIWriteXClient()
    try:
        default_resp = client.get_json(EP_CONFIG_DEFAULT)
        default_data = default_resp.get("data", {})
        _patch_and_save(client, default_data)
        print_success("已恢复默认配置并落盘")
    except AIWriteXError as e:
        print_error(f"恢复失败: {e}")
        raise typer.Exit(1)


# Register nested sub-apps (llm, creative). Import here to avoid circular imports
# at module load time — _common defines the Typer instances; sub modules attach commands.
from .llm import llm_app as _llm_app  # noqa: E402
from .creative import creative_app as _creative_app  # noqa: E402

app.add_typer(_llm_app, name="llm")
app.add_typer(_creative_app, name="creative")
