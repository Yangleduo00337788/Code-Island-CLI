"""Anthropic Claude provider."""

import json
from typing import AsyncIterator, Optional

import httpx

from .base import BaseProvider, ChatResponse, Message


class ClaudeProvider(BaseProvider):
    """Provider for Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        base_url = base_url or "https://api.anthropic.com"
        super().__init__(api_key, base_url)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        stream: bool = False,
        tools: Optional[list] = None,
    ) -> ChatResponse | AsyncIterator[str]:
        """Send chat messages using Claude API."""
        if not self.validate_api_key():
            raise ValueError("Claude 的 API Key 未配置")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # Convert messages format
        system_message = None
        claude_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            elif msg.role == "tool":
                claude_messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": msg.tool_call_id or "", "content": msg.content}],
                })
            else:
                content = [{"type": "text", "text": msg.content}] if msg.content else []
                claude_messages.append({"role": msg.role, "content": content})

        data = {
            "model": model,
            "max_tokens": 4096,
            "messages": claude_messages,
        }

        if system_message:
            data["system"] = system_message

        if tools:
            data["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools
            ]

        if stream:
            return self._stream_chat(headers, data)
        else:
            return await self._normal_chat(headers, data)

    async def _normal_chat(self, headers: dict, data: dict) -> ChatResponse:
        """Non-streaming chat request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=data,
                timeout=120.0,
            )
            response.raise_for_status()
            result = response.json()

            content = ""
            tool_calls = None
            for block in result.get("content", []):
                if block["type"] == "text":
                    content += block["text"]
                elif block["type"] == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block["id"],
                        "name": block["name"],
                        "arguments": json.dumps(block["input"]),
                    })

            return ChatResponse(
                content=content,
                model=result["model"],
                usage=result.get("usage"),
                tool_calls=tool_calls,
            )

    async def _stream_chat(self, headers: dict, data: dict) -> AsyncIterator[str]:
        """Streaming chat request."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=data,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line = line[6:]
                        try:
                            import json

                            chunk = json.loads(line)
                            if chunk["type"] == "content_block_delta":
                                yield chunk["delta"]["text"]
                        except (json.JSONDecodeError, KeyError):
                            continue

    def get_available_models(self) -> list[str]:
        """Get list of available Claude models."""
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
