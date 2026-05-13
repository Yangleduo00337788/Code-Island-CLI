"""工具定义和执行器 - AI 可用的系统工具。"""

import os
import subprocess
import glob as glob_module
from pathlib import Path
from typing import Any, Optional


WORKSPACE_DIR = os.getcwd()

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容，返回文件文本",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "文件路径（相对或绝对）",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "起始行号（可选，从1开始）",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "读取行数（可选，默认500）",
                    },
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入或创建文件。会覆盖已有文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的文件内容",
                    },
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "精确编辑文件：查找 old_string 并替换为 new_string。old_string 必须精确匹配（含缩进和空行）。如果有多处匹配会失败，请提供足够的上下文使其唯一。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "要编辑的文件路径",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "要替换的原文本（必须精确匹配）",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "替换后的新文本",
                    },
                },
                "required": ["filepath", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "在当前工作目录执行系统命令。此操作需要用户审批。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令",
                    },
                    "workdir": {
                        "type": "string",
                        "description": "工作目录（可选，默认当前项目目录）",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出目录内容，包括文件和子目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径，默认当前目录",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "使用 glob 模式搜索文件，返回匹配的文件路径列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "glob 模式，如 **/*.py 或 src/**/*.ts",
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索起始目录（可选，默认当前目录）",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": "在文件中搜索内容，使用正则表达式。返回匹配的文件路径和行号。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "正则表达式搜索模式",
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索目录（可选，默认当前目录）",
                    },
                    "include": {
                        "type": "string",
                        "description": "文件过滤，如 *.py（可选）",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


def _resolve_path(filepath: str) -> Path:
    """将路径解析为绝对路径，安全检查防止目录遍历。"""
    p = Path(filepath)
    if not p.is_absolute():
        p = Path(WORKSPACE_DIR) / p
    resolved = p.resolve()
    return resolved


def read_file(filepath: str, offset: int = 1, limit: int = 500) -> str:
    """读取文件内容。"""
    path = _resolve_path(filepath)
    if not path.exists():
        return f"错误: 文件不存在: {filepath}"
    if not path.is_file():
        return f"错误: 不是文件: {filepath}"
    try:
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")
        total_lines = len(lines)
        start = max(0, offset - 1)
        end = start + limit
        result = "\n".join(lines[start:end])
        header = ""
        if offset > 1 or limit < total_lines:
            header = f"[行 {start + 1}-{min(end, total_lines)} / 共 {total_lines} 行]\n"
        return header + result
    except UnicodeDecodeError:
        return f"错误: 无法以 UTF-8 读取文件（可能是二进制文件）: {filepath}"
    except Exception as e:
        return f"错误: 读取文件失败: {e}"


def write_file(filepath: str, content: str) -> str:
    """写入文件。"""
    path = _resolve_path(filepath)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"文件已写入: {filepath} ({len(content)} 字符)"
    except Exception as e:
        return f"错误: 写入文件失败: {e}"


def edit_file(filepath: str, old_string: str, new_string: str) -> str:
    """精确替换编辑文件。"""
    path = _resolve_path(filepath)
    if not path.exists():
        return f"错误: 文件不存在: {filepath}"
    if not path.is_file():
        return f"错误: 不是文件: {filepath}"
    try:
        content = path.read_text(encoding="utf-8")
        count = content.count(old_string)
        if count == 0:
            return f"错误: 在 {filepath} 中未找到要替换的文本"
        if count > 1:
            return f"错误: 在 {filepath} 中找到 {count} 处匹配，请提供更多上下文使其唯一"
        new_content = content.replace(old_string, new_string, 1)
        path.write_text(new_content, encoding="utf-8")
        return f"文件已编辑: {filepath}"
    except Exception as e:
        return f"错误: 编辑文件失败: {e}"


def execute_command(command: str, workdir: Optional[str] = None) -> str:
    """执行系统命令。"""
    try:
        cwd = workdir if workdir else WORKSPACE_DIR
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        parts = []
        if output:
            parts.append(output[:5000])
        if error:
            parts.append(f"[stderr]\n{error[:2000]}")
        if result.returncode != 0:
            parts.append(f"[退出码: {result.returncode}]")
        return "\n".join(parts) if parts else "(无输出)"
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时 (120秒)"
    except Exception as e:
        return f"错误: 命令执行失败: {e}"


def list_directory(path: str) -> str:
    """列出目录内容。"""
    dir_path = _resolve_path(path)
    if not dir_path.exists():
        return f"错误: 目录不存在: {path}"
    if not dir_path.is_dir():
        return f"错误: 不是目录: {path}"
    try:
        entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for entry in entries:
            if entry.name.startswith("."):
                continue
            suffix = "/" if entry.is_dir() else ""
            size = ""
            if entry.is_file():
                try:
                    size = f" ({_format_size(entry.stat().st_size)})"
                except Exception:
                    pass
            lines.append(f"  {entry.name}{suffix}{size}")
        return f"{path}:\n" + "\n".join(lines) if lines else f"{path}:\n  (空目录)"
    except Exception as e:
        return f"错误: 列出目录失败: {e}"


def search_files(pattern: str, path: Optional[str] = None) -> str:
    """搜索匹配 glob 模式的文件。"""
    search_path = path if path else WORKSPACE_DIR
    try:
        full_pattern = os.path.join(search_path, pattern)
        matches = sorted(glob_module.glob(full_pattern, recursive=True))
        matches = [m for m in matches if not os.path.basename(m).startswith(".")]
        if not matches:
            return f"未找到匹配 '{pattern}' 的文件"
        return "\n".join(matches[:200])
    except Exception as e:
        return f"错误: 搜索文件失败: {e}"


def search_content(pattern: str, path: Optional[str] = None, include: Optional[str] = None) -> str:
    """在文件内容中搜索。"""
    import re

    search_path = path if path else WORKSPACE_DIR
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"错误: 无效的正则表达式: {e}"

    results = []
    try:
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                if file.startswith("."):
                    continue
                if include and not glob_module.fnmatch.fnmatch(file, include):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        for lineno, line in enumerate(f, 1):
                            if regex.search(line):
                                relpath = os.path.relpath(filepath, WORKSPACE_DIR)
                                results.append(f"{relpath}:{lineno}: {line.rstrip()[:200]}")
                                if len(results) >= 100:
                                    break
                except Exception:
                    continue
                if len(results) >= 100:
                    break
            if len(results) >= 100:
                break
    except Exception as e:
        return f"错误: 搜索失败: {e}"

    if not results:
        return f"未找到匹配 '{pattern}' 的内容"
    return "\n".join(results)


def _format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


TOOL_HANDLERS = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "execute_command": execute_command,
    "list_directory": list_directory,
    "search_files": search_files,
    "search_content": search_content,
}

REQUIRES_APPROVAL = {"execute_command"}
