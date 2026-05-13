"""CLI entry point for aicli."""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import load_config, save_config, get_config_file, get_provider_config
from .chat import interactive_chat, single_question
from .history import ChatHistory
from .providers import create_provider
from .utils import read_file, read_stdin

console = Console(force_terminal=True)


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.run(coro)


@click.group()
@click.version_option(version=__version__, prog_name="aicli")
def main():
    """aicli - 一个与 AI 模型交互的命令行工具。"""
    pass


@main.command()
@click.option("-p", "--provider", help="要使用的 AI 提供商")
@click.option("-m", "--model", help="要使用的模型")
@click.option("--stream/--no-stream", default=None, help="启用/禁用流式输出")
@click.option("--system", "system_prompt", help="系统提示词")
@click.option("--approve/--no-approve", default=None, help="自动批准工具操作")
def chat(
    provider: Optional[str],
    model: Optional[str],
    stream: Optional[bool],
    system_prompt: Optional[str],
    approve: Optional[bool],
):
    """启动交互式对话会话。"""
    config = load_config(provider=provider, model=model, stream=stream)
    if approve is not None:
        config.auto_approve = approve
    run_async(
        interactive_chat(
            config=config,
            provider_name=provider,
            model=model,
            system_prompt=system_prompt,
        )
    )


@main.command()
@click.option("-p", "--provider", help="要使用的 AI 提供商")
@click.option("-m", "--model", help="要使用的模型")
@click.option("--stream/--no-stream", default=None, help="启用/禁用流式输出")
@click.option("--system", "system_prompt", help="系统提示词")
def code(
    provider: Optional[str],
    model: Optional[str],
    stream: Optional[bool],
    system_prompt: Optional[str],
):
    """启动 Claude Code 风格的交互式会话。

    功能特性:
    - 语法高亮
    - 多行输入 (Alt+Enter)
    - 通过 @文件名 或 /file 分析文件
    - 特殊命令 (/clear, /help, /model)
    """
    config = load_config(provider=provider, model=model, stream=stream)
    run_async(
        interactive_chat(
            config=config,
            provider_name=provider,
            model=model,
            system_prompt=system_prompt,
        )
    )


@main.command()
@click.argument("question", required=False)
@click.option("-p", "--provider", help="要使用的 AI 提供商")
@click.option("-m", "--model", help="要使用的模型")
@click.option("-f", "--file", "filepath", help="包含文件内容")
@click.option("--stream/--no-stream", default=None, help="启用/禁用流式输出")
@click.option("--system", "system_prompt", help="系统提示词")
def ask(
    question: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    filepath: Optional[str],
    stream: Optional[bool],
    system_prompt: Optional[str],
):
    """提出单个问题。

    如果未提供 QUESTION，则从标准输入或文件读取。
    """
    config = load_config(provider=provider, model=model, stream=stream)

    # Get question from argument, file, or stdin
    if question is None:
        if filepath:
            question = read_file(filepath)
            if question is None:
                return
        else:
            question = read_stdin()
            if question is None:
                console.print("[#f38ba8]   未提供问题[/#f38ba8]")
                return
    elif filepath:
        file_content = read_file(filepath)
        if file_content is None:
            return
        question = f"{question}\n\n文件内容:\n```\n{file_content}\n```"

    response = run_async(
        single_question(
            config=config,
            question=question,
            provider_name=provider,
            model=model,
            system_prompt=system_prompt,
        )
    )

    if not config.stream:
        console.print(response)


@main.command()
@click.option("-p", "--provider", help="要使用的 AI 提供商")
@click.option("-m", "--model", help="要使用的模型")
def models(provider: Optional[str], model: Optional[str]):
    """列出可用模型。"""
    config = load_config(provider=provider, model=model)
    provider_name = provider or config.default_provider

    provider_config = get_provider_config(config, provider_name)
    provider = create_provider(
        provider_name=provider_name,
        api_key=provider_config.api_key,
        base_url=provider_config.base_url,
    )

    available_models = provider.get_available_models()

    console.print()
    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )
    console.print(f"[#89b4fa]   {provider_name} 可用模型[/#89b4fa]")
    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )

    for i, m in enumerate(available_models, 1):
        status = " [#a6e3a1] 当前[/#a6e3a1]" if m == (model or config.default_model) else ""
        console.print(f"  [#585b70]{i:2d}.[/#585b70] [#cdd6f4]{m}[/#cdd6f4]{status}")

    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )
    console.print()


@main.command()
def config():
    """显示配置文件路径和当前配置。"""
    config_file = get_config_file()
    
    console.print()
    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )
    console.print(f"[#89b4fa]   配置[/#89b4fa]")
    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )
    console.print(f"[#89b4fa]  配置文件[/#89b4fa]  [#cdd6f4]{config_file}[/#cdd6f4]")

    if config_file.exists():
        loaded = load_config()
        console.print(
            f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
        )
        console.print(f"[#89b4fa]  提供商[/#89b4fa]      [#cdd6f4]{loaded.default_provider}[/#cdd6f4]")
        console.print(f"[#89b4fa]  模型[/#89b4fa]        [#cdd6f4]{loaded.default_model}[/#cdd6f4]")
        console.print(f"[#89b4fa]  流式输出[/#89b4fa]    [#cdd6f4]{loaded.stream}[/#cdd6f4]")
        console.print(f"[#89b4fa]  历史大小[/#89b4fa]    [#cdd6f4]{loaded.history_size}[/#cdd6f4]")
    else:
        console.print("[#6c7086]  未找到配置文件，使用默认值[/#6c7086]")

    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )
    console.print()


@main.command()
@click.option("-p", "--provider", help="要配置的 AI 提供商")
@click.option("-k", "--api-key", help="要设置的 API Key")
@click.option("--base-url", help="要设置的 Base URL")
def setup(provider: Optional[str], api_key: Optional[str], base_url: Optional[str]):
    """为提供商设置配置。"""
    config = load_config()

    if provider is None:
        provider = click.prompt(
            "提供商",
            type=click.Choice(["deepseek", "openai", "claude", "moonshot", "ollama"]),
            default="deepseek",
        )

    if api_key is None and provider != "ollama":
        api_key = click.prompt("API Key", hide_input=True)

    if base_url is None:
        default_urls = {
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com",
            "claude": "https://api.anthropic.com",
            "moonshot": "https://api.moonshot.cn",
            "ollama": "http://localhost:11434",
        }
        base_url = click.prompt("Base URL", default=default_urls.get(provider, ""))

    if provider not in config.providers:
        config.providers[provider] = {}

    from .config import ProviderConfig

    config.providers[provider] = ProviderConfig(
        api_key=api_key,
        base_url=base_url,
    )

    save_config(config)
    console.print()
    console.print(f"[bold #a6e3a1]   配置已保存: [#cdd6f4]{provider}[/#cdd6f4][/bold #a6e3a1]")
    console.print()


@main.group()
def history():
    """管理对话历史记录。"""
    pass


@history.command("list")
def history_list():
    """列出已保存的对话会话。"""
    sessions = ChatHistory.list_sessions()

    if not sessions:
        console.print()
        console.print("[#6c7086]   未找到已保存的会话[/#6c7086]")
        console.print()
        return

    console.print()
    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )
    console.print(f"[#89b4fa]   对话会话[/#89b4fa]")
    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )

    for session in sessions:
        console.print(
            f"  [#cdd6f4]{session['name']}[/#cdd6f4]"
            f"  [#6c7086]{session['modified']}[/#6c7086]"
            f"  [#585b70]{session['size']} 字节[/#585b70]"
        )

    console.print(
        f"[#6c7086]  ─────────────────────────────────────[/#6c7086]"
    )
    console.print()


@history.command("save")
@click.argument("name")
def history_save(name: str):
    """保存当前对话历史记录。"""
    # This would need to be connected to an active session
    console.print()
    console.print("[#f9e2af]   保存命令需要活跃的对话会话[/#f9e2af]")
    console.print()


@history.command("load")
@click.argument("name")
def history_load(name: str):
    """加载已保存的对话会话。"""
    # This would start a chat with loaded history
    console.print()
    console.print(f"[#89b4fa]   正在加载会话: [#cdd6f4]{name}[/#cdd6f4][/#89b4fa]")
    console.print()


if __name__ == "__main__":
    main()
