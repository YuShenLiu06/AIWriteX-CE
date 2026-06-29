"""创意维度命令组：show/list/groups/enable/disable/options/pick/custom + config get/set。

与 Web 设置页能力对齐：5 分组、15 维度、每维度 N 预设 + 自定义、
auto_dimension_selection=true 时拒绝细分配置（用 --force 强制）。
"""

from typing import Optional
import typer

from ...client import AIWriteXClient
from ...errors import AIWriteXError
from ...formatters import (
    print_success, print_error, print_warning, print_info,
    print_table,
)
from ._common import (
    creative_app,
    DIMENSIONAL_KEYS, DIMENSIONAL_NAMES_ZH,
    DIMENSION_GROUPS, DIMENSIONAL_GLOBAL_FIELDS,
    EP_CONFIG, _patch_and_save, _validate_dims,
)

# 嵌套子组：全局字段配置
config_app = typer.Typer(help="全局维度配置 (总开关/强度/自动选择等)")


def _fetch_dc(client: AIWriteXClient) -> dict:
    """GET dimensional_creative section."""
    resp = client.get_json(EP_CONFIG)
    return resp.get("data", {}).get("dimensional_creative", {}) or {}


def _check_manual_mode(client: AIWriteXClient, force: bool) -> None:
    """对齐 Web: auto_dimension_selection=true 时拒绝细分维度操作。
    用户需先关闭该开关（与 Web UI 一致），或显式 --force 强制。"""
    try:
        dc = _fetch_dc(client)
    except AIWriteXError:
        return  # 读失败交给后续 PATCH 报错
    if dc.get("auto_dimension_selection", True):
        print_warning("当前 auto_dimension_selection=true（系统自动选维度）")
        print_info("Web 行为：关闭此开关后才可单独配置细分维度")
        if not force:
            print_error("拒绝执行。请先关闭：")
            print_info("  aiwritex server-config creative config set auto_dimension_selection false")
            print_info("或加 --force 强制（不推荐，结果可能被自动选择覆盖）")
            raise typer.Exit(1)
        print_warning("--force 已启用，继续执行")


@creative_app.command()
def show() -> None:
    """显示创意维度总览：全局开关 + 启用维度。"""
    client = AIWriteXClient()
    try:
        dc = _fetch_dc(client)
    except AIWriteXError as e:
        print_error(f"读取失败: {e}"); raise typer.Exit(1)

    enabled_dims = dc.get("enabled_dimensions", {}) or {}
    active = [k for k, v in enabled_dims.items() if v and k in DIMENSIONAL_KEYS]

    print_info(f"总开关 enabled: {'启用' if dc.get('enabled') else '禁用'}")
    print_info(f"创意强度 creative_intensity: {dc.get('creative_intensity', '?')}")
    print_info(f"自动选择 auto_dimension_selection: {'启用' if dc.get('auto_dimension_selection') else '禁用'}")
    print_info(f"最大维度 max_dimensions: {dc.get('max_dimensions', '?')}")
    print_info(f"兼容阈值 compatibility_threshold: {dc.get('compatibility_threshold', '?')}")
    print_info(f"保持核心 preserve_core_info: {'是' if dc.get('preserve_core_info') else '否'}")
    print_info(f"允许实验 allow_experimental: {'是' if dc.get('allow_experimental') else '否'}")
    print_info(f"启用维度: {len(active)} / {len(DIMENSIONAL_KEYS)}")
    if active:
        print_success("已启用: " + ", ".join(f"{k}({DIMENSIONAL_NAMES_ZH.get(k, k)})" for k in active))


@creative_app.command("list")
def list_(
    group: Optional[str] = typer.Option(
        None, "--group", "-g",
        help="按分组过滤: expression|culture|character|structure|audience",
    ),
) -> None:
    """按 5 分组列出维度、启用状态、当前选择。"""
    if group and group not in DIMENSION_GROUPS:
        print_error(f"未知分组: {group}")
        print_info("合法分组: " + ", ".join(f"{g}({v['name']})" for g, v in DIMENSION_GROUPS.items()))
        raise typer.Exit(1)

    client = AIWriteXClient()
    try:
        dc = _fetch_dc(client)
    except AIWriteXError as e:
        print_error(f"读取失败: {e}"); raise typer.Exit(1)

    enabled_dims = dc.get("enabled_dimensions", {}) or {}
    opts = dc.get("dimension_options", {}) or {}
    groups_to_show = {group: DIMENSION_GROUPS[group]} if group else DIMENSION_GROUPS

    for gkey, ginfo in groups_to_show.items():
        rows = []
        for dim in ginfo["dimensions"]:
            is_on = bool(enabled_dims.get(dim, False))
            o = opts.get(dim, {}) or {}
            custom = o.get("custom_input", "")
            sel = o.get("selected_option", "")
            choice = f"自定义:{custom}" if custom else (sel or "-")
            rows.append([dim, DIMENSIONAL_NAMES_ZH.get(dim, "-"), "✓" if is_on else "", choice])
        print_table(
            ["Key", "中文名", "启用", "当前选择"], rows,
            title=f"{ginfo['name']} ({gkey})",
        )


@creative_app.command()
def groups() -> None:
    """列出 5 个维度分组。"""
    rows = []
    for gkey, ginfo in DIMENSION_GROUPS.items():
        dims_zh = ", ".join(DIMENSIONAL_NAMES_ZH.get(d, d) for d in ginfo["dimensions"])
        rows.append([gkey, ginfo["name"], str(len(ginfo["dimensions"])), dims_zh])
    print_table(["分组 Key", "中文名", "维度数", "包含维度"], rows, title="创意维度分组 (5)")


@creative_app.command()
def enable(
    dims: str = typer.Argument(..., help="要启用的维度 key，逗号分隔"),
    force: bool = typer.Option(False, "--force", help="auto_selection=true 时强制执行"),
) -> None:
    """启用指定创意维度（自动落盘）。"""
    keys = _validate_dims(dims)
    client = AIWriteXClient()
    _check_manual_mode(client, force)
    payload = {"dimensional_creative": {"enabled_dimensions": {k: True for k in keys}}}
    try:
        _patch_and_save(client, payload)
        print_success("已启用 " + ", ".join(f"{k}({DIMENSIONAL_NAMES_ZH[k]})" for k in keys))
    except AIWriteXError as e:
        print_error(f"启用失败: {e}"); raise typer.Exit(1)


@creative_app.command()
def disable(
    dims: str = typer.Argument(..., help="要禁用的维度 key，逗号分隔"),
    force: bool = typer.Option(False, "--force", help="auto_selection=true 时强制执行"),
) -> None:
    """禁用指定创意维度（自动落盘）。"""
    keys = _validate_dims(dims)
    client = AIWriteXClient()
    _check_manual_mode(client, force)
    payload = {"dimensional_creative": {"enabled_dimensions": {k: False for k in keys}}}
    try:
        _patch_and_save(client, payload)
        print_success("已禁用 " + ", ".join(f"{k}({DIMENSIONAL_NAMES_ZH[k]})" for k in keys))
    except AIWriteXError as e:
        print_error(f"禁用失败: {e}"); raise typer.Exit(1)


@creative_app.command()
def options(
    dim: str = typer.Argument(..., help="维度 key（如 style）"),
) -> None:
    """列出某维度的预设选项 + 当前选中 + 是否允许自定义。"""
    if dim not in DIMENSIONAL_KEYS:
        print_error(f"未知维度: {dim}，合法: {', '.join(DIMENSIONAL_KEYS)}")
        raise typer.Exit(1)
    client = AIWriteXClient()
    try:
        dc = _fetch_dc(client)
    except AIWriteXError as e:
        print_error(f"读取失败: {e}"); raise typer.Exit(1)
    opt = (dc.get("dimension_options", {}) or {}).get(dim, {}) or {}
    if not opt:
        print_error(f"维度 {dim} 无 dimension_options"); raise typer.Exit(1)
    print_info(f"{dim}({DIMENSIONAL_NAMES_ZH.get(dim, '')}) 允许自定义: {'是' if opt.get('allow_custom') else '否'}")
    cur = opt.get("selected_option", "")
    custom = opt.get("custom_input", "")
    if custom:
        print_info(f"当前自定义: {custom}")
    elif cur:
        print_info(f"当前选中: {cur}")
    rows = []
    for p in opt.get("preset_options", []) or []:
        is_sel = "✓" if p.get("name") == cur and not custom else ""
        rows.append([p.get("name", ""), p.get("value", ""), p.get("description", ""), is_sel])
    print_table(["选项 key", "显示名", "描述", "选中"], rows, title=f"{dim} 预设选项")


@creative_app.command()
def pick(
    dim: str = typer.Argument(..., help="维度 key"),
    option: str = typer.Argument(..., help="预设选项 key（先 options <dim> 查看）"),
    force: bool = typer.Option(False, "--force", help="auto_selection=true 时强制执行"),
) -> None:
    """选中某维度的预设选项（自动落盘，会清空 custom_input）。"""
    if dim not in DIMENSIONAL_KEYS:
        print_error(f"未知维度: {dim}"); raise typer.Exit(1)
    client = AIWriteXClient()
    _check_manual_mode(client, force)
    try:
        dc = _fetch_dc(client)
    except AIWriteXError as e:
        print_error(f"读取失败: {e}"); raise typer.Exit(1)
    presets = (dc.get("dimension_options", {}).get(dim, {}) or {}).get("preset_options", []) or []
    preset_keys = [p.get("name") for p in presets]
    if option not in preset_keys:
        print_error(f"未知预设选项: {option}")
        print_info(f"合法选项: {', '.join(preset_keys)}")
        raise typer.Exit(1)
    payload = {"dimensional_creative": {"dimension_options": {dim: {"selected_option": option, "custom_input": ""}}}}
    try:
        _patch_and_save(client, payload)
        display = next((p.get("value", option) for p in presets if p.get("name") == option), option)
        print_success(f"已选中 {dim}({DIMENSIONAL_NAMES_ZH.get(dim, '')}) -> {option}({display})")
    except AIWriteXError as e:
        print_error(f"选中失败: {e}"); raise typer.Exit(1)


@creative_app.command()
def custom(
    dim: str = typer.Argument(..., help="维度 key"),
    text: str = typer.Argument(..., help="自定义文本"),
    force: bool = typer.Option(False, "--force", help="auto_selection=true 时强制执行"),
) -> None:
    """为维度设置自定义输入（自动落盘，要求 allow_custom=true；会清空 selected_option）。"""
    if dim not in DIMENSIONAL_KEYS:
        print_error(f"未知维度: {dim}"); raise typer.Exit(1)
    client = AIWriteXClient()
    _check_manual_mode(client, force)
    try:
        dc = _fetch_dc(client)
    except AIWriteXError as e:
        print_error(f"读取失败: {e}"); raise typer.Exit(1)
    opt = (dc.get("dimension_options", {}) or {}).get(dim, {}) or {}
    if not opt.get("allow_custom", False):
        print_error(f"维度 {dim} 不允许自定义（allow_custom=false）"); raise typer.Exit(1)
    payload = {"dimensional_creative": {"dimension_options": {dim: {"custom_input": text, "selected_option": ""}}}}
    try:
        _patch_and_save(client, payload)
        print_success(f"已设置 {dim}({DIMENSIONAL_NAMES_ZH.get(dim, '')}) 自定义: {text}")
    except AIWriteXError as e:
        print_error(f"设置失败: {e}"); raise typer.Exit(1)


# ----- config 嵌套子组 -----

@config_app.command("get")
def config_get() -> None:
    """显示所有全局维度配置字段。"""
    client = AIWriteXClient()
    try:
        dc = _fetch_dc(client)
    except AIWriteXError as e:
        print_error(f"读取失败: {e}"); raise typer.Exit(1)
    rows = []
    for field, meta in DIMENSIONAL_GLOBAL_FIELDS.items():
        rows.append([field, str(dc.get(field, "?")), meta["desc"]])
    print_table(["字段", "当前值", "说明"], rows, title="全局维度配置")


@config_app.command("set")
def config_set(
    field: str = typer.Argument(..., help="字段名（见 config get）"),
    value: str = typer.Argument(..., help="字段值（bool: true/false；int/float: 数字）"),
) -> None:
    """修改全局维度配置字段（自动落盘）。"""
    if field not in DIMENSIONAL_GLOBAL_FIELDS:
        print_error(f"未知字段: {field}")
        print_info(f"合法字段: {', '.join(DIMENSIONAL_GLOBAL_FIELDS.keys())}")
        raise typer.Exit(1)
    ftype = DIMENSIONAL_GLOBAL_FIELDS[field]["type"]
    try:
        if ftype is bool:
            parsed: object = value.lower() in ("true", "1", "yes", "on")
        elif ftype is int:
            parsed = int(value)
        elif ftype is float:
            parsed = float(value)
        else:
            parsed = value
    except ValueError as e:
        print_error(f"值类型转换失败（期望 {ftype.__name__}）: {e}"); raise typer.Exit(1)
    client = AIWriteXClient()
    payload = {"dimensional_creative": {field: parsed}}
    try:
        _patch_and_save(client, payload)
        print_success(f"已设置 {field} = {parsed} 并落盘")
    except AIWriteXError as e:
        print_error(f"设置失败: {e}"); raise typer.Exit(1)


# Register nested config sub-app onto creative_app.
creative_app.add_typer(config_app, name="config")
