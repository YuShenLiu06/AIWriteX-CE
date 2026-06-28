"""Output formatters using rich for CLI."""

import json
from typing import Any, Optional
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def print_success(message: str) -> None:
    """Print success message in green."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print error message in red."""
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    """Print info message in blue."""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_table(
    columns: list[str],
    rows: list[list[Any]],
    title: Optional[str] = None,
) -> None:
    """Print data as a table."""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*(str(cell) for cell in row))
    console.print(table)


def print_json(data: Any, pretty: bool = True) -> None:
    """Print JSON data."""
    if pretty:
        # rich.JSON expects a JSON string; serialize dicts/objects first.
        payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        console.print(JSON(payload))
    else:
        console.print(data)


def print_panel(content: str, title: Optional[str] = None) -> None:
    """Print content in a panel."""
    console.print(Panel(content, title=title, border_style="blue"))


def print_code(code: str, language: str = "python", title: Optional[str] = None) -> None:
    """Print syntax-highlighted code."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=title, border_style="blue"))


def print_status(status: str, message: str = "") -> None:
    """Print status with appropriate color."""
    if status in ("success", "completed", "healthy"):
        print_success(message or status)
    elif status in ("error", "failed", "unhealthy"):
        print_error(message or status)
    elif status in ("warning", "running", "pending"):
        print_warning(message or status)
    else:
        print_info(message or status)
