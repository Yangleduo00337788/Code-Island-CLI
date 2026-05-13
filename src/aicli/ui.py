"""Terminal UI management for aicli."""

import asyncio
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text


class Status(Enum):
    """Application status states."""
    READY = "ready"
    THINKING = "thinking"
    REQUESTING = "requesting"
    STREAMING = "streaming"
    TOOL_CALL = "tool_call"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class MessageStats:
    """Statistics for a message."""
    model: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    char_count: int = 0
    token_count: int = 0

    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def duration_str(self) -> str:
        """Get formatted duration string."""
        d = self.duration
        minutes = int(d // 60)
        seconds = int(d % 60)
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


@dataclass
class UIState:
    """Current UI state."""
    status: Status = Status.READY
    current_model: str = ""
    current_provider: str = ""
    message_count: int = 0
    error_message: str = ""
    stats: Optional[MessageStats] = None
    history_size: int = 0


class TerminalUI:
    """Terminal UI manager."""

    def __init__(self, console: Console):
        self.console = console
        self.state = UIState()
        self._live: Optional[Live] = None
        self._response_text = ""

    def show_welcome(self, provider: str, model: str, api_configured: bool):
        """Show welcome screen."""
        import os

        api_dot = "[#a6e3a1]● 已配置[/#a6e3a1]" if api_configured else "[#f38ba8]○ 未配置[/#f38ba8]"
        cwd = os.getcwd()

        content = f""" [#89b4fa]模型[/#89b4fa] [#cdd6f4]{model}[/#cdd6f4]  ·  [#89b4fa]提供商[/#89b4fa] [#cdd6f4]{provider}[/#cdd6f4]  ·  {api_dot}
 [#6c7086]{cwd}[/#6c7086]"""

        self.console.print()
        self.console.print("[#585b70]  ── aicli v0.1.0 ──[/#585b70]")
        self.console.print(content)
        self.console.print()

        self.state.current_provider = provider
        self.state.current_model = model

    def update_status(self, status: Status, message: str = ""):
        """Update current status."""
        self.state.status = status
        if message:
            self.state.error_message = message

    def get_status_bar(self) -> str:
        """Get status bar text."""
        status_icons = {
            Status.READY: "●",
            Status.THINKING: "◉",
            Status.REQUESTING: "◌",
            Status.STREAMING: "◎",
            Status.TOOL_CALL: "⚡",
            Status.COMPLETED: "✓",
            Status.ERROR: "✗",
        }

        status_colors = {
            Status.READY: "green",
            Status.THINKING: "yellow",
            Status.REQUESTING: "yellow",
            Status.STREAMING: "cyan",
            Status.TOOL_CALL: "yellow",
            Status.COMPLETED: "green",
            Status.ERROR: "red",
        }

        icon = status_icons.get(self.state.status, "●")
        color = status_colors.get(self.state.status, "white")
        status_text = self.state.status.value.capitalize()

        parts = [
            f"[{color}]{icon}[/{color}] {status_text}",
            f"[dim]{self.state.current_model}[/dim]",
            f"[dim]msg:{self.state.message_count}[/dim]",
        ]

        if self.state.stats and self.state.status in (Status.STREAMING, Status.COMPLETED):
            parts.append(f"[dim]{self.state.stats.duration_str}[/dim]")

        return "  ".join(parts)

    def start_response(self, model: str):
        """Start a new response."""
        self.state.message_count += 1
        self.state.current_model = model
        self.state.stats = MessageStats(model=model, start_time=time.time())
        self.update_status(Status.THINKING)

    def start_streaming(self):
        """Start streaming response."""
        self.state.stats.start_time = time.time()
        self.update_status(Status.STREAMING)

        # Show header
        self.console.print()
        self.console.print(
            f"[bold #89b4fa]  {self.state.current_model}[/bold #89b4fa]"
            f"[#585b70]  ──────────────────────────[/#585b70]"
        )
        self.console.print()

        # Start live display
        self._response_text = ""
        self._live = Live(
            console=self.console,
            refresh_per_second=15,
            vertical_overflow="visible",
        )
        self._live.start()

    def update_stream(self, chunk: str):
        """Update streaming response."""
        if chunk:
            self._response_text += chunk
            self.state.stats.char_count = len(self._response_text)
            if self._live:
                self._live.update(Markdown(self._response_text))

    def end_streaming(self):
        """End streaming response."""
        if self._live:
            self._live.stop()
            self._live = None

        self.state.stats.end_time = time.time()
        self.update_status(Status.COMPLETED)

        # Show footer
        self.console.print()
        self.console.print(
            f"[#585b70]  ── [/#585b70]"
            f"[#6c7086]{self.state.stats.duration_str}[/#6c7086]"
            f"[#45475a] · [/#45475a]"
            f"[#6c7086]{self.state.stats.char_count} 字符[/#6c7086]"
        )
        self.console.print()

    def get_animation_frame(self) -> str:
        """Get current animation frame."""
        animation_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        return animation_chars[int(time.time() * 10) % len(animation_chars)]

    def show_error(self, error: str):
        """Show error message."""
        self.update_status(Status.ERROR, error)
        self.console.print()
        self.console.print(f"[bold #f38ba8]   错误[/bold #f38ba8]")
        self.console.print(f"[#f38ba8]  {error}[/#f38ba8]")
        self.console.print()

    def show_thinking_animation(self):
        """Show thinking animation context manager (legacy, kept for compatibility)."""
        return self.thinking(message="思考中...")

    @contextmanager
    def thinking(self, message: str = "思考中..."):
        """Show animated thinking indicator with custom spinner.

        Usage:
            with ui.thinking("分析项目中..."):
                response = await provider.chat(...)
        """
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_idx = [0]
        start_time = time.time()

        def render():
            frame = spinner_frames[spinner_idx[0] % len(spinner_frames)]
            spinner_idx[0] += 1
            elapsed = time.time() - start_time
            elapsed_str = f"{elapsed:.1f}s"
            return Text(
                f"  {frame} {message}  ·  {elapsed_str}",
                style="#f9e2af",
            )

        with Live(
            render(),
            console=self.console,
            refresh_per_second=12,
            transient=False,
        ) as live:
            import threading

            stop_event = threading.Event()

            def animate():
                while not stop_event.is_set():
                    live.update(render())
                    stop_event.wait(0.08)

            thread = threading.Thread(target=animate, daemon=True)
            thread.start()
            try:
                yield
            finally:
                stop_event.set()
                thread.join(timeout=0.5)
                live.update(Text("", style=""))

    def pulse_action(self, message: str, duration: float = 0.6):
        """Show a pulsing progress animation for short transitions.

        Usage:
            ui.pulse_action("正在切换模型...", duration=0.5)
        """
        with Progress(
            SpinnerColumn(style="#89b4fa"),
            TextColumn(f"[#89b4fa]{message}[/#89b4fa]"),
            BarColumn(style="#45475a", complete_style="#89b4fa", pulse=True),
            console=self.console,
            transient=True,
            expand=False,
        ) as progress:
            task = progress.add_task("", total=None)
            start = time.time()
            while time.time() - start < duration:
                progress.update(task, advance=0.1)
                time.sleep(0.05)
        # Clear the line after
        self.console.print(" " * (len(message) + 20), end="\r")

    async def with_thinking(self, coro, message: str = "思考中..."):
        """Run a coroutine with animated thinking display.

        Usage:
            response = await ui.with_thinking(
                provider.chat(messages, model),
                message="分析中..."
            )
        """
        with self.thinking(message):
            return await coro

    def show_model_list(self, models: list[str], current_model: str):
        """Show model selection list."""
        self.console.print()
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print(f"[#89b4fa]  可用模型[/#89b4fa]")
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )

        for i, model in enumerate(models, 1):
            status = " [#a6e3a1] 当前[/#a6e3a1]" if model == current_model else ""
            self.console.print(f"  [#585b70]{i:2d}.[/#585b70] [#cdd6f4]{model}[/#cdd6f4]{status}")

        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print()

    def show_help(self):
        """Show help panel."""
        help_text = """[#89b4fa]  命令[/#89b4fa]

  [#cba6f7]/model[/#cba6f7]          [#6c7086]显示模型列表并切换[/#6c7086]
  [#cba6f7]/model <名称>[/#cba6f7]   [#6c7086]切换到指定模型[/#6c7086]
  [#cba6f7]/provider[/#cba6f7]       [#6c7086]切换提供商[/#6c7086]
  [#cba6f7]/setup[/#cba6f7]          [#6c7086]配置 API Key[/#6c7086]
  [#cba6f7]/clear[/#cba6f7]          [#6c7086]清除对话历史记录[/#6c7086]
  [#cba6f7]/config[/#cba6f7]         [#6c7086]显示当前配置[/#6c7086]
  [#cba6f7]/help[/#cba6f7]           [#6c7086]显示此帮助[/#6c7086]
  [#cba6f7]/exit[/#cba6f7]           [#6c7086]退出程序[/#cba6f7]

[#89b4fa]  会话管理[/#89b4fa]

  [#cba6f7]/save [名称][/#cba6f7]    [#6c7086]保存当前对话会话[/#6c7086]
  [#cba6f7]/load [名称][/#cba6f7]    [#6c7086]加载已保存的会话[/#6c7086]
  [#cba6f7]/export <名称>[/#cba6f7]  [#6c7086]导出会话为 JSON + Markdown[/#6c7086]
  [#cba6f7]/undo[/#cba6f7]           [#6c7086]撤销最后一轮对话[/#6c7086]
  [#cba6f7]/retry[/#cba6f7]          [#6c7086]重试最后一个请求[/#6c7086]

[#89b4fa]  文件操作[/#89b4fa]

  [#f9e2af]@文件名[/#f9e2af]          [#6c7086]在消息中引用文件[/#6c7086]
  [#f9e2af]/file <路径>[/#f9e2af]    [#6c7086]读取并分析文件[/#6c7086]

[#89b4fa]  键盘快捷键[/#89b4fa]

  [#a6e3a1]Enter[/#a6e3a1]           [#6c7086]发送消息[/#6c7086]
  [#a6e3a1]Alt+Enter[/#a6e3a1]       [#6c7086]换行[/#6c7086]
  [#a6e3a1]Esc[/#a6e3a1]             [#6c7086]中断当前请求[/#6c7086]
  [#a6e3a1]Ctrl+C[/#a6e3a1]          [#6c7086]中断 / 退出 (按两次)[/#6c7086]
  [#a6e3a1]Ctrl+P[/#a6e3a1]          [#6c7086]命令面板[/#6c7086]
  [#a6e3a1]↑/↓[/#a6e3a1]             [#6c7086]浏览历史记录[/#6c7086]"""

        self.console.print()
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print(help_text)
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print()

    def show_config(self, provider: str, model: str, api_configured: bool,
                    stream: bool, history_size: int):
        """Show current configuration."""
        api_status = "[bold #a6e3a1]  已配置[/bold #a6e3a1]" if api_configured else "[bold #f38ba8]  未配置[/bold #f38ba8]"

        self.console.print()
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print(f"[#89b4fa]  配置[/#89b4fa]")
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print(
            f"[#89b4fa]  提供商[/#89b4fa]     [#cdd6f4]{provider}[/#cdd6f4]"
        )
        self.console.print(
            f"[#89b4fa]  模型[/#89b4fa]       [#cdd6f4]{model}[/#cdd6f4]"
        )
        self.console.print(
            f"[#89b4fa]  API Key[/#89b4fa]   {api_status}"
        )
        self.console.print(
            f"[#89b4fa]  流式输出[/#89b4fa]    [#cdd6f4]{stream}[/#cdd6f4]"
        )
        self.console.print(
            f"[#89b4fa]  历史记录[/#89b4fa]    [#cdd6f4]{history_size}[/#cdd6f4]"
        )
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print()

    def show_saved_sessions(self, sessions: list[dict]):
        """Show saved conversation sessions."""
        self.console.print()
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print(f"[#89b4fa]  已保存的会话[/#89b4fa]")
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        for i, s in enumerate(sessions, 1):
            self.console.print(
                f"  [#585b70]{i:2d}.[/#585b70] [#cdd6f4]{s['name']}[/#cdd6f4]"
                f"  [#6c7086]{s['modified']}[/#6c7086]"
                f"  [#585b70]{s['size']} 字节[/#585b70]"
            )
        self.console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        self.console.print()
