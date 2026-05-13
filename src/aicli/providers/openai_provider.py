"""OpenAI-compatible provider for DeepSeek, OpenAI, Moonshot, etc."""

from typing import AsyncIterator, Optional

import httpx

from .base import BaseProvider, ChatResponse, Message


DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com",
    "moonshot": "https://api.moonshot.cn",
}


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider_name: str = "openai",
    ):
        if base_url is None:
            base_url = DEFAULT_BASE_URLS.get(provider_name, "https://api.openai.com")
        super().__init__(api_key, base_url)
        self.provider_name = provider_name

    async def chat(
        self,
        messages: list[Message],
        model: str,
        stream: bool = False,
        tools: Optional[list] = None,
    ) -> ChatResponse | AsyncIterator[str]:
        """Send chat messages using OpenAI-compatible API."""
        if not self.validate_api_key():
            raise ValueError(f"{self.provider_name} 的 API Key 未配置")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        msg_list = []
        for m in messages:
            msg = {"role": m.role, "content": m.content}
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.name:
                msg["name"] = m.name
            if m.reasoning_content:
                msg["reasoning_content"] = m.reasoning_content
            msg_list.append(msg)

        data = {
            "model": model,
            "messages": msg_list,
            "stream": stream,
        }

        if tools:
            data["tools"] = tools
            data["tool_choice"] = "auto"

        if stream:
            return self._stream_chat(headers, data)
        else:
            return await self._normal_chat(headers, data)

    async def _normal_chat(self, headers: dict, data: dict) -> ChatResponse:
        """Non-streaming chat request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=120.0,
            )
            if response.status_code != 200:
                error_detail = response.text[:500]
                raise ValueError(
                    f"API 错误 ({response.status_code}): {error_detail}"
                )
            result = response.json()

            message = result["choices"][0]["message"]
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls")
            reasoning_content = message.get("reasoning_content")

            return ChatResponse(
                content=content,
                model=result["model"],
                usage=result.get("usage"),
                tool_calls=[
                    {
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    }
                    for tc in tool_calls
                ] if tool_calls else None,
                reasoning_content=reasoning_content,
            )

    async def _stream_chat(self, headers: dict, data: dict) -> AsyncIterator[str]:
        """Streaming chat request."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line = line[6:]
                        if line.strip() == "[DONE]":
                            break
                        try:
                            import json

                            chunk = json.loads(line)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content is not None:
                                yield content
                        except json.JSONDecodeError:
                            continue

    def get_available_models(self) -> list[str]:
        """Get list of available models based on provider."""
        # Default fallback models
        fallback_models = {
            "deepseek": [
                "deepseek-chat",
                "deepseek-coder",
                "deepseek-reasoner",
            ],
            "openai": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
            ],
            "moonshot": [
                "moonshot-v1-8k",
                "moonshot-v1-32k",
                "moonshot-v1-128k",
            ],
        }

        # Try to fetch from API
        if self.api_key:
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }
                response = requests.get(
                    f"{self.base_url}/v1/models",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    if models:
                        return sorted(models)
            except Exception:
                pass

        return fallback_models.get(self.provider_name, [])
