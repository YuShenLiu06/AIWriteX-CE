"""LLM 提供商配置命令：列出 provider 状态、设置 API Key、切换激活 provider 与模型。"""
from typing import Optional

import typer

from ...client import AIWriteXClient
from ...errors import AIWriteXError
from ...formatters import (
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
)
from ._common import EP_CONFIG, LLM_PROVIDERS, _patch_and_save, llm_app


@llm_app.command("list")
def list_(
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="只查看指定 provider 详情"
    ),
) -> None:
    """列出所有 LLM provider 及其 key/model 状态。"""
    client = AIWriteXClient()
    try:
        response = client.get_json(EP_CONFIG)
    except AIWriteXError as e:
        print_error(f"读取配置失败: {e}")
        raise typer.Exit(1)

    api_cfg = response.get("data", {}).get("api", {})
    active = api_cfg.get("api_type", "")
    providers_in_cfg = {
        k: v for k, v in api_cfg.items() if isinstance(v, dict) and "api_key" in v
    }

    if provider:
        if provider not in providers_in_cfg:
            print_error(
                f"provider '{provider}' 不存在，已知: {', '.join(providers_in_cfg.keys())}"
            )
            raise typer.Exit(1)
        print_json(providers_in_cfg[provider])
        return

    rows = []
    for name in LLM_PROVIDERS:
        cfg = providers_in_cfg.get(name, {})
        keys = cfg.get("api_key", []) or []
        models = cfg.get("model", []) or []
        mi = cfg.get("model_index", 0)
        current_model = models[mi] if 0 <= mi < len(models) else "-"
        is_active = "✓" if name == active else ""
        rows.append([name, is_active, str(len(keys)), current_model])
    print_table(["Provider", "激活", "Key 数", "当前模型"], rows, title="LLM 配置")
    print_info(f"当前激活: {active}")


@llm_app.command("set-key")
def set_key(
    provider: str = typer.Argument(
        ..., help=f"LLM provider 名（如 {', '.join(LLM_PROVIDERS[:3])}...）"
    ),
    key: str = typer.Argument(..., help="API Key 值"),
) -> None:
    """设置指定 provider 的 API Key（自动落盘）。"""
    if provider not in LLM_PROVIDERS:
        print_error(f"未知 provider: {provider}")
        print_info(f"已知 providers: {', '.join(LLM_PROVIDERS)}")
        raise typer.Exit(1)
    client = AIWriteXClient()
    try:
        _patch_and_save(client, {"api": {provider: {"api_key": [key]}}})
        print_success(f"已设置 {provider} 的 API Key 并落盘")
    except AIWriteXError as e:
        print_error(f"设置失败: {e}")
        raise typer.Exit(1)


@llm_app.command()
def switch(
    provider: str = typer.Argument(..., help="要激活的 provider 名"),
) -> None:
    """切换当前激活的 LLM provider（修改 api_type，自动落盘）。"""
    if provider not in LLM_PROVIDERS:
        print_error(f"未知 provider: {provider}")
        print_info(f"已知 providers: {', '.join(LLM_PROVIDERS)}")
        raise typer.Exit(1)
    client = AIWriteXClient()
    try:
        _patch_and_save(client, {"api": {"api_type": provider}})
        print_success(f"已切换激活 provider 为 {provider} 并落盘")
    except AIWriteXError as e:
        print_error(f"切换失败: {e}")
        raise typer.Exit(1)


@llm_app.command("use-model")
def use_model(
    provider: str = typer.Argument(..., help="provider 名"),
    index: int = typer.Argument(
        ...,
        help="model 列表的索引（0-based，先用 `llm list -p <provider>` 查可选）",
    ),
) -> None:
    """切换指定 provider 的当前模型索引（自动落盘）。"""
    if provider not in LLM_PROVIDERS:
        print_error(f"未知 provider: {provider}")
        print_info(f"已知 providers: {', '.join(LLM_PROVIDERS)}")
        raise typer.Exit(1)
    if index < 0:
        print_error("index 必须 >= 0")
        raise typer.Exit(1)
    client = AIWriteXClient()
    try:
        resp = client.get_json(EP_CONFIG)
        api_cfg = resp.get("data", {}).get("api", {})
        models = (api_cfg.get(provider, {}) or {}).get("model", []) or []
        if index >= len(models):
            print_error(
                f"index {index} 超出范围（{provider} 有 {len(models)} 个模型）"
            )
            raise typer.Exit(1)
    except AIWriteXError as e:
        print_error(f"读取配置失败: {e}")
        raise typer.Exit(1)
    try:
        _patch_and_save(client, {"api": {provider: {"model_index": index}}})
        print_success(f"已切换 {provider} 模型为 [{index}] {models[index]} 并落盘")
    except AIWriteXError as e:
        print_error(f"切换失败: {e}")
        raise typer.Exit(1)
