"""Utility functions."""

import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def read_file(filepath: str) -> Optional[str]:
    """Read file content.

    Args:
        filepath: Path to the file

    Returns:
        File content or None if error
    """
    try:
        path = Path(filepath)
        if not path.exists():
            console.print(f"[red]文件未找到: {filepath}[/red]")
            return None
        if not path.is_file():
            console.print(f"[red]不是文件: {filepath}[/red]")
            return None
        return path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]读取文件出错: {e}[/red]")
        return None


def read_stdin() -> Optional[str]:
    """Read from stdin if data is available.

    Returns:
        Stdin content or None
    """
    if sys.stdin.isatty():
        return None
    try:
        return sys.stdin.read()
    except Exception:
        return None


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
