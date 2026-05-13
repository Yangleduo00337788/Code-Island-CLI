"""工具调用代理循环 - 已弃用。

此模块已整合到 chat.py 的 _run_tool_loop() 中。
保留此文件仅用于向后兼容。
"""

import json
from typing import Optional

from rich.console import Console

from .config import AppConfig
from .providers import Message, create_provider
from .providers.base import ChatResponse
from .tools import TOOL_DEFINITIONS, TOOL_HANDLERS, REQUIRES_APPROVAL

console = Console()


async def tool_loop(
    config: AppConfig,
    messages: list[Message],
    provider_name: str,
    model: str,
    stream: bool = False,
    auto_approve: bool = False,
    on_tool_call: Optional[callable] = None,
) -> str:
    """代理循环：发送消息，处理工具调用，直到 AI 给出最终回复。"""
    from .providers import get_provider_config

    provider_config = get_provider_config(config, provider_name)
    provider = create_provider(
        provider_name=provider_name,
        api_key=provider_config.api_key,
        base_url=provider_config.base_url,
    )

    max_iterations = 15

    for iteration in range(max_iterations):
        response = await provider.chat(
            messages=messages,
            model=model,
            tools=TOOL_DEFINITIONS,
            stream=False,
        )

        if response.tool_calls:
            for tc in response.tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("arguments", {})
                tool_id = tc.get("id", "")

                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        tool_args = {}

                if on_tool_call:
                    on_tool_call(tool_name, tool_args)

                handler = TOOL_HANDLERS.get(tool_name)
                if handler:
                    needs_approval = tool_name in REQUIRES_APPROVAL and not auto_approve
                    if needs_approval:
                        console.print(
                            f"\n[#f9e2af]  ⚡ 工具调用批准[/#f9e2af]"
                        )
                        console.print(
                            f"[#6c7086]  {tool_name}[/#6c7086] "
                            f"[#585b70]{_format_args(tool_args)}[/#585b70]"
                        )
                        approved = input("  执行? [y/N] ").strip().lower()
                        if approved != "y":
                            tool_result = "用户拒绝了此操作"
                        else:
                            tool_result = handler(**tool_args)
                    else:
                        tool_result = handler(**tool_args)
                else:
                    tool_result = f"未知工具: {tool_name}"

                result_content = str(tool_result)
                if on_tool_call and hasattr(on_tool_call, 'result') or True:
                    pass

                messages.append(
                    Message(
                        role="tool",
                        content=result_content,
                        tool_call_id=tool_id,
                        name=tool_name,
                    )
                )
                messages.append(
                    _make_assistant_tool_response(tool_name, tool_id, result_content)
                )

            # Remove the assistant message that contained tool calls
            # (we need to keep it in the conversation with the tool_call info)
            if response.content:
                pass
        else:
            return response.content or ""

    return "已达到最大工具调用次数，但任务未完成。"


def _format_args(args: dict) -> str:
    """格式化工具参数用于显示。"""
    items = []
    for k, v in args.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + "..."
        items.append(f"{k}={s}")
    return ", ".join(items)


def _make_assistant_tool_response(tool_name: str, tool_id: str, result: str) -> Message:
    """创建包含工具调用信息的 assistant 消息。"""
    # 将工具结果作为 assistant 消息的一部分
    # 实际在 OpenAI 格式中，tool 消息跟在 assistant (with tool_calls) 之后
    return Message(
        role="assistant",
        content=f"[工具调用: {tool_name}]",
    )


def format_tool_result_for_chat(tool_name: str, tool_args: dict, result: str) -> str:
    """格式化工具执行结果用于聊天显示。"""
    args_str = _format_args(tool_args)
    return f"[{#6c7086}  {tool_name}({args_str})[/#6c7086]]"
