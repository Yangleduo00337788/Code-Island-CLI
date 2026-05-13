"""Core chat functionality - Claude Code style."""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from .config import AppConfig, ProviderConfig, get_provider_config, save_config
from .history import ChatHistory
from .providers import Message, create_provider
from .tools import TOOL_DEFINITIONS, TOOL_HANDLERS, REQUIRES_APPROVAL
from .ui import Status, TerminalUI

console = Console()
ui = TerminalUI(console)

PROVIDER_LIST = ["deepseek", "openai", "claude", "moonshot", "ollama"]

DEFAULT_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com",
    "claude": "https://api.anthropic.com",
    "moonshot": "https://api.moonshot.cn",
    "ollama": "http://localhost:11434",
}

DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4o",
    "claude": "claude-3-5-sonnet-20241022",
    "moonshot": "moonshot-v1-8k",
    "ollama": "llama3",
}

SYSTEM_PROMPT = """你是一个 AI 编程助手。你可以帮助用户：
- 编写、审查和调试代码
- 解释技术概念
- 解决编程问题
- 处理文件和项目

你有以下工具可用：
- read_file: 读取文件内容
- write_file: 写入或创建文件
- edit_file: 精确编辑文件（查找替换）
- execute_command: 执行系统命令（需要用户批准）
- list_directory: 列出目录内容
- search_files: 用 glob 模式搜索文件
- search_content: 在文件内容中搜索（正则表达式）

使用工具时：
- 先读取文件了解现状，再编辑
- edit_file 的 old_string 必须精确匹配（含缩进）
- 如果 old_string 有多处匹配会失败，提供更多上下文使其唯一
- 执行命令前确认不会造成损害"""


def get_current_directory() -> str:
    """Get current working directory."""
    return os.getcwd()


def check_api_key(config: AppConfig, provider_name: str) -> bool:
    """Check if API key is configured for a provider."""
    if provider_name == "ollama":
        return True
    provider_config = get_provider_config(config, provider_name)
    return provider_config.api_key is not None and len(provider_config.api_key) > 0


def interactive_setup(config: AppConfig, provider_name: str) -> Optional[AppConfig]:
    """Interactive setup for API key."""
    from rich.prompt import Prompt, Confirm

    console.print()
    console.print(f"[#f9e2af]  提供商 [#cdd6f4]{provider_name}[/#cdd6f4] 未配置 API Key[/#f9e2af]")
    console.print("[#6c7086]  现在进行配置...[/#6c7086]")
    console.print()

    # Select provider
    console.print("[#89b4fa]  可用提供商:[/#89b4fa]")
    for i, p in enumerate(PROVIDER_LIST, 1):
        console.print(f"  [#585b70]{i}.[/#585b70] [#cdd6f4]{p}[/#cdd6f4]")

    choice = Prompt.ask(
        "选择提供商",
        default=str(PROVIDER_LIST.index(provider_name) + 1) if provider_name in PROVIDER_LIST else "1",
        choices=[str(i) for i in range(1, len(PROVIDER_LIST) + 1)]
    )
    provider_name = PROVIDER_LIST[int(choice) - 1]

    # Get API key
    if provider_name == "ollama":
        console.print("[#6c7086]  Ollama 不需要 API Key[/#6c7086]")
        api_key = None
    else:
        console.print(f"\n[#6c7086]  输入 {provider_name} 的 API Key (支持粘贴):[/#6c7086]")
        api_key = input("  API Key: ").strip()
        if not api_key:
            console.print("[#f38ba8]   API Key 不能为空[/#f38ba8]")
            return None

    # Get base URL
    default_url = DEFAULT_URLS.get(provider_name, "")
    base_url = Prompt.ask("输入 Base URL", default=default_url)

    # Fetch available models from API
    available_models = []
    if api_key and provider_name != "ollama":
        console.print("\n[#6c7086]  正在获取可用模型列表...[/#6c7086]")
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            url = f"{base_url}/v1/models"
            response = requests.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                available_models = sorted([m["id"] for m in data.get("data", [])])
        except Exception as e:
            console.print(f"[#f9e2af]   获取模型列表失败: {e}[/#f9e2af]")

    # Select default model
    default_model = DEFAULT_MODELS.get(provider_name, "")
    if available_models:
        console.print("\n[#89b4fa]  可用模型:[/#89b4fa]")
        for i, m in enumerate(available_models, 1):
            console.print(f"  [#585b70]{i:2d}.[/#585b70] [#cdd6f4]{m}[/#cdd6f4]")

        console.print("\n[#6c7086]  输入数字选择默认模型，或直接输入模型名称[/#6c7086]")
        model_choice = input("  选择模型 (直接回车使用默认): ").strip()

        if model_choice:
            if model_choice.isdigit() and 1 <= int(model_choice) <= len(available_models):
                default_model = available_models[int(model_choice) - 1]
            else:
                default_model = model_choice
        elif not default_model and available_models:
            default_model = available_models[0]
    else:
        if provider_name != "ollama":
            model_input = input(f"  输入默认模型名称 (直接回车使用 '{default_model}'): ").strip()
            if model_input:
                default_model = model_input

    # Save config
    config.default_provider = provider_name
    config.default_model = default_model
    config.providers[provider_name] = ProviderConfig(
        api_key=api_key,
        base_url=base_url if base_url else None,
    )
    save_config(config)

    console.print()
    console.print(f"[bold #a6e3a1]   {provider_name} 配置已保存[/bold #a6e3a1]")
    console.print(f"[#a6e3a1]   默认模型: [#cdd6f4]{default_model}[/#cdd6f4][/#a6e3a1]")
    console.print()
    return config


def quick_switch_provider(config: AppConfig) -> tuple[str, str]:
    """Quick switch provider and model."""
    from rich.prompt import Prompt, Confirm

    console.print()
    console.print("[#89b4fa]  切换提供商:[/#89b4fa]")
    for i, p in enumerate(PROVIDER_LIST, 1):
        current = " [#a6e3a1] 当前[/#a6e3a1]" if p == config.default_provider else ""
        console.print(f"  [#585b70]{i}.[/#585b70] [#cdd6f4]{p}[/#cdd6f4]{current}")

    choice = Prompt.ask(
        "选择提供商",
        default="",
        choices=[str(i) for i in range(1, len(PROVIDER_LIST) + 1)] + [""],
    )

    if not choice:
        return config.default_provider, config.default_model

    new_provider = PROVIDER_LIST[int(choice) - 1]
    new_model = DEFAULT_MODELS.get(new_provider, config.default_model)

    # Check if API key exists
    if not check_api_key(config, new_provider):
        console.print(f"[#f9e2af]   {new_provider} 未配置 API Key[/#f9e2af]")
        if Confirm.ask("  现在配置?"):
            updated = interactive_setup(config, new_provider)
            if updated:
                return new_provider, updated.default_model
        return config.default_provider, config.default_model

    return new_provider, new_model


def read_file_content(filepath: str) -> Optional[str]:
    """Read file content if file exists."""
    try:
        path = Path(filepath)
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8")
            if len(content) > 10000:
                content = content[:10000] + "\n... (truncated)"
            return content
    except Exception:
        pass
    return None


async def chat_completion(
    config: AppConfig,
    messages: list[Message],
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    stream: Optional[bool] = None,
) -> str:
    """Get chat completion from AI model."""
    provider_name = provider_name or config.default_provider
    model = model or config.default_model
    stream = stream if stream is not None else config.stream

    provider_config = get_provider_config(config, provider_name)
    provider = create_provider(
        provider_name=provider_name,
        api_key=provider_config.api_key,
        base_url=provider_config.base_url,
    )

    if stream:
        return await _stream_response(provider, messages, model)
    else:
        with ui.thinking("思考中..."):
            response = await provider.chat(messages=messages, model=model, stream=False)
        return response.content


async def _stream_response(provider, messages: list[Message], model: str) -> str:
    """Handle streaming response with better formatting."""
    full_response = []

    try:
        # Start response
        ui.start_response(model)

        # Show thinking animation while waiting for initial response
        with ui.thinking("请求中..."):
            stream = await provider.chat(messages=messages, model=model, stream=True)

        # Start streaming
        ui.start_streaming()

        # Stream response
        async for chunk in stream:
            if chunk is not None:
                full_response.append(chunk)
                ui.update_stream(chunk)

        # End streaming
        ui.end_streaming()

        return "".join(full_response)
    except Exception as e:
        ui.show_error(str(e))
        return "".join(full_response)


def process_input(user_input: str) -> tuple[str, Optional[str]]:
    """Process user input, handling special commands and file references.

    Returns:
        Tuple of (processed_input, file_content)
    """
    file_content = None

    # Check for /file command
    if user_input.startswith("/file "):
        filepath = user_input[6:].strip()
        content = read_file_content(filepath)
        if content:
            file_content = content
            user_input = f"请分析此文件 ({filepath}):\n\n```\n{content}\n```"
        else:
            console.print(f"[#f38ba8]   无法读取文件: {filepath}[/#f38ba8]")
            return "", None

    # Check for @file references
    if "@" in user_input:
        parts = user_input.split()
        for part in parts:
            if part.startswith("@"):
                filepath = part[1:]
                content = read_file_content(filepath)
                if content:
                    file_content = content
                    user_input = user_input.replace(
                        part, f"({filepath}):\n```\n{content}\n```"
                    )

    return user_input, file_content


def _display_tool_args(tool_args: dict):
    """Display tool call arguments in a clean format."""
    if not tool_args:
        return
    for k, v in tool_args.items():
        val_str = str(v)
        if len(val_str) > 80:
            val_str = val_str[:77] + "..."
        console.print(f"  [#585b70]{k}:[/#585b70] [#6c7086]{val_str}[/#6c7086]")


def _display_read_file(tool_args: dict):
    """Display read_file tool call compactly with filename only."""
    filepath = str(tool_args.get("filepath", "?"))
    filename = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    console.print(f"[#a6e3a1]  ● read_file[/#a6e3a1] [#585b70]·[/#585b70] [#6c7086]{filename}[/#6c7086]")


def _display_tool_result(tool_result: str):
    """Display tool execution result with truncation."""
    lines = tool_result.split("\n")
    if len(lines) > 5:
        preview = "\n".join(lines[:5])
        console.print(f"  [#45475a]{preview}[/#45475a]")
        console.print(f"  [#585b70]... ({len(lines)} 行, {len(tool_result)} 字符)[/#585b70]")
    else:
        for line in lines:
            if len(line) > 120:
                line = line[:117] + "..."
            console.print(f"  [#45475a]{line}[/#45475a]")


async def _run_tool_loop(
    config: AppConfig,
    history: ChatHistory,
    provider_name: str,
    model: str,
    max_iterations: int = 20,
) -> None:
    """执行工具调用循环：AI 可自主使用工具完成任务。"""
    provider_config = get_provider_config(config, provider_name)
    provider = create_provider(
        provider_name=provider_name,
        api_key=provider_config.api_key,
        base_url=provider_config.base_url,
    )

    for iteration in range(max_iterations):
        messages = history.get_messages()
        try:
            # Show thinking animation while waiting for API
            with ui.thinking("思考中..."):
                response = await provider.chat(
                    messages=messages,
                    model=model,
                    tools=TOOL_DEFINITIONS,
                    stream=False,
                )
        except Exception as e:
            ui.show_error(str(e))
            return

        if response.tool_calls:
            # Show reasoning content if present
            if response.reasoning_content:
                console.print()
                console.print(f"[#585b70]  ── 思考过程 ──[/#585b70]")
                console.print(f"[#6c7086]  {response.reasoning_content[:500]}[/#6c7086]")
                if len(response.reasoning_content or "") > 500:
                    console.print(f"[#6c7086]  ... (截断)[/#6c7086]")

            # 先添加 assistant 消息（含 tool_calls），消息顺序很重要
            response_content = (response.content or "").strip()
            assistant_msg = Message(
                role="assistant",
                content=response_content if response_content else None,
                tool_calls=[
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in response.tool_calls
                ] if response.tool_calls else None,
                reasoning_content=response.reasoning_content,
            )
            history.add_message(assistant_msg)

            # 分离需要审批和不需审批的工具（保留原始 arguments 字符串）
            no_approval_calls = []
            approval_calls = []
            for tc in response.tool_calls:
                tc_copy = dict(tc)
                args = tc_copy.get("arguments", {})
                if isinstance(args, str):
                    try:
                        tc_copy["arguments"] = json.loads(args)
                    except json.JSONDecodeError:
                        tc_copy["arguments"] = {}
                if tc_copy.get("name") in REQUIRES_APPROVAL and not config.auto_approve:
                    approval_calls.append(tc_copy)
                else:
                    no_approval_calls.append(tc_copy)

            # 显示工具调用分隔线
            tool_count = len(response.tool_calls)
            label = "工具调用" if tool_count > 1 else "工具调用"
            console.print()
            console.print(f"[#45475a]  ── {label} ({tool_count}) ──[/#45475a]")

            # 并行执行不需要审批的工具
            import concurrent.futures

            async def _exec_tool(tc):
                tool_name = tc["name"]
                tool_args = tc.get("arguments", {})
                handler = TOOL_HANDLERS.get(tool_name)
                if handler:
                    import functools
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(
                        None, functools.partial(handler, **tool_args)
                    )
                return f"未知工具: {tool_name}"

            # 并行执行
            if no_approval_calls:
                ui.update_status(Status.TOOL_CALL)
                tasks = [_exec_tool(tc) for tc in no_approval_calls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for tc, result in zip(no_approval_calls, results):
                    tool_name = tc["name"]
                    tool_args = tc.get("arguments", {})
                    tool_id = tc.get("id", "")
                    if isinstance(result, Exception):
                        tool_result = f"错误: {result}"
                        console.print(f"[#f38ba8]  ✗ {tool_name}[/#f38ba8]")
                    else:
                        tool_result = str(result)
                        if tool_name == "read_file":
                            _display_read_file(tool_args)
                        else:
                            console.print(f"[#a6e3a1]  ● {tool_name}[/#a6e3a1]")
                            _display_tool_args(tool_args)
                            _display_tool_result(tool_result)

                    history.add_message(Message(
                        role="tool",
                        content=tool_result,
                        tool_call_id=tool_id,
                        name=tool_name,
                    ))

            # 逐个处理需要审批的工具
            for tc in approval_calls:
                tool_name = tc["name"]
                tool_args = tc.get("arguments", {})
                tool_id = tc.get("id", "")

                console.print(f"[#f9e2af]  ⚠ {tool_name}[/#f9e2af]")
                _display_tool_args(tool_args)
                console.print(f"[#f9e2af]  需要批准此操作[/#f9e2af]")
                approved = input("  执行? [y/N] ").strip().lower()
                if approved != "y":
                    tool_result = "用户拒绝了此操作"
                    console.print(f"[#f38ba8]  ✗ 已拒绝[/#f38ba8]")
                else:
                    handler = TOOL_HANDLERS.get(tool_name)
                    tool_result = handler(**tool_args) if handler else f"未知工具: {tool_name}"
                    if tool_name == "read_file":
                        _display_read_file(tool_args)
                    else:
                        _display_tool_result(tool_result)

                history.add_message(Message(
                    role="tool",
                    content=str(tool_result),
                    tool_call_id=tool_id,
                    name=tool_name,
                ))

            ui.update_status(Status.TOOL_CALL)
            console.print(f"[#45475a]  ── 完成 ──[/#45475a]")

            # 继续循环，让 AI 处理工具结果
            continue
        else:
            # AI 给出最终回复
            if response.content:
                # 流式显示
                ui.start_response(model)
                ui.start_streaming()
                content = response.content
                ui.update_stream(content)
                ui.end_streaming()
                history.add_message("assistant", content)
            return

    console.print("[#f9e2af]   已达到最大工具调用次数[/#f9e2af]")


async def interactive_chat(
    config: AppConfig,
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> None:
    """Start an interactive chat session with Claude Code style."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML

    try:
        from pygments.lexers import PythonLexer
        lexer = PygmentsLexer(PythonLexer)
    except ImportError:
        lexer = None

    # Check API key on first launch
    current_provider = provider_name or config.default_provider
    if not check_api_key(config, current_provider):
        config = interactive_setup(config, current_provider)
        if config is None:
            return
        current_provider = config.default_provider
        model = config.default_model

    history = ChatHistory(max_size=config.history_size)

    # Use custom or default system prompt
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT
    history.add_message("system", system_prompt)

    provider_display = current_provider
    model_display = model or config.default_model

    # Show welcome
    ui.show_welcome(provider_display, model_display, check_api_key(config, provider_display))

    # Setup key bindings
    bindings = KeyBindings()

    @bindings.add("escape", "enter")
    def _(event):
        event.current_buffer.newline()

    @bindings.add("enter")
    def _(event):
        event.current_buffer.validate_and_handle()

    @bindings.add("c-c")
    def _(event):
        """Handle Ctrl+C - copy selection or exit."""
        buffer = event.app.current_buffer
        if buffer.selection_state:
            buffer.copy_selection()
        else:
            event.app.exit(exception=KeyboardInterrupt)

    @bindings.add("c-p")
    def _(event):
        """Handle Ctrl+P - command palette."""
        event.app.exit(exception=KeyboardInterrupt("palette"))

    @bindings.add("c-v")
    def _(event):
        """Handle Ctrl+V - paste from clipboard."""
        from prompt_toolkit.clipboard import get_clipboard
        clipboard_data = get_clipboard().get_data()
        if clipboard_data.text:
            event.current_buffer.insert_text(clipboard_data.text)

    # Command completer
    commands = [
        "/setup", "/provider", "/model", "/clear", "/file",
        "/config", "/help", "/exit", "/save", "/load",
        "/export", "/undo", "/retry", "/resume"
    ]
    command_completer = WordCompleter(commands, ignore_case=True)

    # Setup prompt session
    prompt_history_file = ChatHistory.get_history_dir() / ".prompt_history"
    prompt_history = FileHistory(str(prompt_history_file))

    msg_count = 0
    interrupt_count = 0

    session_start = time.time()

    def get_toolbar_text():
        """Get toolbar formatted text."""
        from prompt_toolkit.formatted_text import HTML

        elapsed = ""
        if ui.state.status in (Status.STREAMING, Status.COMPLETED, Status.TOOL_CALL, Status.THINKING):
            if ui.state.stats and ui.state.stats.start_time > 0:
                elapsed = ui.state.stats.duration_str
        else:
            d = time.time() - session_start
            m = int(d // 60)
            s = int(d % 60)
            elapsed = f"{m}m {s}s" if m > 0 else f"{s}s"

        if ui.state.status in (Status.THINKING, Status.STREAMING):
            anim = ui.get_animation_frame()
            status_text = "thinking" if ui.state.status == Status.THINKING else "streaming"
            return HTML(
                f'<style bg="#11111b" fg="#f9e2af">  {anim} {status_text}</style>'
                f'<style bg="#11111b" fg="#585b70">  ·  {elapsed}</style>'
                f'<style bg="#11111b" fg="#585b70">  ·  {model_display}</style>'
            )
        elif ui.state.status == Status.TOOL_CALL:
            return HTML(
                f'<style bg="#11111b" fg="#a6e3a1">  ◇ tool_call</style>'
                f'<style bg="#11111b" fg="#585b70">  ·  {elapsed}</style>'
                f'<style bg="#11111b" fg="#585b70">  ·  {model_display}</style>'
            )
        elif ui.state.status == Status.ERROR:
            err = ui.state.error_message[:40]
            return HTML(
                f'<style bg="#11111b" fg="#f38ba8">  ✗ {err}</style>'
            )
        else:
            return HTML(
                f'<style bg="#11111b" fg="#cba6f7">{model_display}</style>'
                f'<style bg="#11111b" fg="#45475a">  /  </style>'
                f'<style bg="#11111b" fg="#89b4fa">{provider_display}</style>'
                f'<style bg="#11111b" fg="#585b70">  ·  {msg_count} msgs</style>'
                f'<style bg="#11111b" fg="#585b70">  ·  {elapsed}</style>'
            )

    def get_prompt_html():
        """Get styled prompt message."""
        from prompt_toolkit.formatted_text import HTML
        return HTML(
            f'<prompt-symbol>▸</prompt-symbol> '
        )

    def get_rprompt_html():
        """Get right-aligned prompt info."""
        from prompt_toolkit.formatted_text import HTML
        return HTML(
            f'<prompt-model>{model_display}</prompt-model>'
            f'<prompt-sep>  ·  </prompt-sep>'
            f'<prompt-provider>{provider_display}</prompt-provider>'
            f'<prompt-meta>  {msg_count}</prompt-meta>'
        )

    # Input style - Catppuccin Mocha inspired
    input_style = Style.from_dict({
        # Prompt
        'prompt-symbol': '#cba6f7 bold',
        'prompt-model': '#a6e3a1',
        'prompt-sep': '#45475a',
        'prompt-provider': '#89b4fa',
        'prompt-meta': '#585b70',

        # Input text
        '': '#cdd6f4',

        # Cursor
        'cursor': '#cba6f7',

        # Toolbar
        'bottom-toolbar': 'noreverse bg:#11111b',
        'bottom-toolbar.text': '#6c7086',

        # Auto-completion menu
        'completion-menu': 'bg:#1e1e2e #cdd6f4',
        'completion-menu.completion': 'bg:#313244 #cdd6f4',
        'completion-menu.completion.current': 'bg:#45475a #cba6f7 bold',
        'completion-menu.meta.completion': 'bg:#313244 #6c7086',
        'completion-menu.meta.completion.current': 'bg:#45475a #cba6f7',
        'completion-menu.multi-column-meta': 'bg:#313244 #6c7086',

        # Scrollbar
        'scrollbar': 'bg:#313244',
        'scrollbar.button': 'bg:#45475a',
        'scrollbar.arrow': 'bg:#313244 #89b4fa',

        # Selection
        'selection': 'bg:#45475a #cdd6f4',

        # Search
        'search': 'bg:#f9e2af #1e1e2e',
        'search.current': 'bg:#f38ba8 #1e1e2e',
    })

    def get_bottom_toolbar():
        """Get bottom toolbar."""
        return get_toolbar_text()

    session = PromptSession(
        history=prompt_history,
        key_bindings=bindings,
        lexer=lexer,
        multiline=False,
        completer=command_completer,
        style=input_style,
        bottom_toolbar=get_bottom_toolbar,
        complete_while_typing=True,
        mouse_support=False,
    )

    while True:
        try:
            # Update message count
            msg_count += 1
            ui.state.message_count = msg_count

            # Clear any residual input from previous command interactions
            if session.app:
                session.app.current_buffer.reset()

            user_input = await session.prompt_async(
                message=get_prompt_html(),
                rprompt=get_rprompt_html(),
            )

            # Reset status after input
            ui.update_status(Status.READY)

            # Invalidate to refresh toolbar
            session.app.invalidate()

        except KeyboardInterrupt as e:
            if str(e) == "palette":
                # Show command palette
                console.print("\n[bold]命令面板:[/bold]")
                for i, cmd in enumerate(commands, 1):
                    console.print(f"  [cyan]{i}[/cyan]. {cmd}")
                continue

            interrupt_count += 1
            if interrupt_count >= 2:
                console.print("\n[#6c7086]  再见！[/#6c7086]")
                break
            console.print("\n[#f9e2af]  再次按 Ctrl+C 退出[/#f9e2af]")
            continue

        except EOFError:
            console.print("\n[#6c7086]  再见！[/#6c7086]")
            break

        interrupt_count = 0
        user_input = user_input.strip()

        if not user_input:
            continue

        # Handle special commands
        cmd = user_input.lower()

        if cmd in ("quit", "exit", "/exit"):
            console.print("[#6c7086]  再见！[/#6c7086]")
            break

        if cmd == "/clear":
            ui.pulse_action("正在清除历史记录...", 0.3)
            history.clear()
            history.add_message("system", system_prompt)
            msg_count = 0
            console.print("[bold #a6e3a1]   历史记录已清除[/bold #a6e3a1]")
            session.app.invalidate()
            continue

        if cmd == "/help":
            ui.show_help()
            session.app.invalidate()
            continue

        if cmd == "/setup":
            result = interactive_setup(config, provider_display)
            if result:
                config = result
                provider_display = config.default_provider
                model_display = config.default_model
            session.app.invalidate()
            continue

        if cmd == "/provider":
            new_provider, new_model = quick_switch_provider(config)
            if new_provider != provider_display:
                provider_display = new_provider
                model_display = new_model
                config.default_provider = new_provider
                config.default_model = new_model
                save_config(config)
                ui.pulse_action("正在切换提供商...", 0.5)
                console.print(f"[bold #a6e3a1]   已切换到: [#cdd6f4]{provider_display}[/#cdd6f4] ([#89b4fa]{model_display}[/#89b4fa])[/bold #a6e3a1]")
            session.app.invalidate()
            continue

        if cmd == "/config":
            ui.show_config(
                provider_display,
                model_display,
                check_api_key(config, provider_display),
                config.stream,
                config.history_size
            )
            continue

        if cmd == "/model":
            # Get available models
            try:
                provider_config = get_provider_config(config, provider_display)
                provider = create_provider(
                    provider_name=provider_display,
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url,
                )
                available_models = provider.get_available_models()
            except Exception:
                available_models = []

            ui.show_model_list(available_models, model_display)

            console.print("\n[dim]输入数字选择模型，或直接输入模型名称[/dim]")
            choice = input("选择模型: ").strip()

            if choice:
                if choice.isdigit() and 1 <= int(choice) <= len(available_models):
                    new_model = available_models[int(choice) - 1]
                else:
                    new_model = choice
                model_display = new_model
                config.default_model = new_model
                save_config(config)
                ui.pulse_action("正在切换模型...", 0.5)
                console.print(f"[bold #a6e3a1]   已切换到模型: [#cdd6f4]{model_display}[/#cdd6f4][/bold #a6e3a1]")
            continue

        if cmd.startswith("/model "):
            new_model = user_input[7:].strip()
            model_display = new_model
            config.default_model = new_model
            save_config(config)
            ui.pulse_action("正在切换模型...", 0.5)
            console.print(f"[bold #a6e3a1]   已切换到模型: [#cdd6f4]{model_display}[/#cdd6f4][/bold #a6e3a1]")
            continue

        if cmd.startswith("/save "):
            name = user_input[6:].strip()
            if not name:
                name = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = ChatHistory.get_history_dir() / f"{name}.json"
            history.save(filepath)
            console.print(f"[bold #a6e3a1]   会话已保存: [#cdd6f4]{name}[/#cdd6f4][/bold #a6e3a1]")
            console.print(f"[#6c7086]  {filepath}[/#6c7086]")
            session.app.invalidate()
            continue

        if cmd == "/save":
            name = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = ChatHistory.get_history_dir() / f"{name}.json"
            history.save(filepath)
            console.print(f"[bold #a6e3a1]   会话已保存: [#cdd6f4]{name}[/#cdd6f4][/bold #a6e3a1]")
            console.print(f"[#6c7086]  {filepath}[/#6c7086]")
            session.app.invalidate()
            continue

        if cmd.startswith("/load "):
            name = user_input[6:].strip()
            filepath = ChatHistory.get_history_dir() / f"{name}.json"
            if filepath.exists():
                history.load(filepath)
                msg_count = len(history.messages)
                console.print(f"[bold #a6e3a1]   已加载会话: [#cdd6f4]{name}[/#cdd6f4] ({msg_count} 条消息)[/bold #a6e3a1]")
                session.app.invalidate()
            else:
                console.print(f"[#f38ba8]   未找到会话: {name}[/#f38ba8]")
            continue

        if cmd == "/load":
            sessions = ChatHistory.list_sessions()
            if not sessions:
                console.print("[#6c7086]   没有已保存的会话[/#6c7086]")
                continue
            ui.show_saved_sessions(sessions)
            choice = input("  选择会话序号: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(sessions):
                session_name = sessions[int(choice) - 1]["name"]
                filepath = ChatHistory.get_history_dir() / f"{session_name}.json"
                history.load(filepath)
                msg_count = len(history.messages)
                console.print(f"[bold #a6e3a1]   已加载会话: [#cdd6f4]{session_name}[/#cdd6f4] ({msg_count} 条消息)[/bold #a6e3a1]")
            session.app.invalidate()
            continue

        if cmd.startswith("/export "):
            name = user_input[8:].strip()
            json_filepath = ChatHistory.get_history_dir() / f"{name}.json"
            md_filepath = ChatHistory.get_history_dir() / f"{name}.md"
            history.save(json_filepath)
            history.export_markdown(md_filepath)
            console.print(f"[bold #a6e3a1]   会话已导出[/bold #a6e3a1]")
            console.print(f"[#6c7086]  JSON: {json_filepath}[/#6c7086]")
            console.print(f"[#6c7086]  MD:   {md_filepath}[/#6c7086]")
            session.app.invalidate()
            continue

        if cmd == "/undo":
            user_indices = [i for i, m in enumerate(history.messages) if m.role == "user"]
            if len(user_indices) < 2:
                console.print("[#6c7086]   没有可撤销的消息[/#6c7086]")
                continue
            last_user_idx = user_indices[-1]
            removed = history.messages[last_user_idx:]
            history.messages = history.messages[:last_user_idx]
            msg_count = len(history.messages)
            console.print(f"[bold #a6e3a1]   已撤销最后一轮对话 ({len(removed)} 条消息)[/bold #a6e3a1]")
            session.app.invalidate()
            continue

        if cmd == "/retry":
            user_indices = [i for i, m in enumerate(history.messages) if m.role == "user"]
            if not user_indices:
                console.print("[#6c7086]   没有可重试的消息[/#6c7086]")
                continue
            last_user_idx = user_indices[-1]
            if last_user_idx < len(history.messages) - 1:
                history.messages = history.messages[:last_user_idx + 1]
                console.print("[bold #89b4fa]   正在重试...[/bold #89b4fa]")
                try:
                    await _run_tool_loop(
                        config=config,
                        history=history,
                        provider_name=provider_display,
                        model=model_display,
                    )
                except Exception as e:
                    ui.show_error(str(e))
            session.app.invalidate()
            continue

        # Process input (handle @file references)
        processed_input, file_content = process_input(user_input)
        if not processed_input:
            continue

        # Add user message to history
        history.add_message("user", processed_input)

        # Get AI response with tool calling
        try:
            await _run_tool_loop(
                config=config,
                history=history,
                provider_name=provider_display,
                model=model_display,
            )
        except Exception as e:
            ui.show_error(str(e))


async def single_question(
    config: AppConfig,
    question: str,
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    file_content: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> str:
    """Ask a single question and get response."""
    messages = []

    if system_prompt:
        messages.append(Message(role="system", content=system_prompt))
    else:
        messages.append(Message(role="system", content=SYSTEM_PROMPT))

    if file_content:
        question = f"{question}\n\n```\n{file_content}\n```"

    messages.append(Message(role="user", content=question))

    return await chat_completion(
        config=config,
        messages=messages,
        provider_name=provider_name,
        model=model,
    )
