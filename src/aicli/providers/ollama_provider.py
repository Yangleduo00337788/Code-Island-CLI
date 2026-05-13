"""Ollama provider for local models."""

from typing import AsyncIterator, Optional

import httpx

from .base import BaseProvider, ChatResponse, Message


class OllamaProvider(BaseProvider):
    """Provider for Ollama local models."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        base_url = base_url or "http://localhost:11434"
        # Ollama doesn't require API key
        super().__init__(api_key="", base_url=base_url)

    async def chat(
        self,
        messages: list[Message],
        model: str,
        stream: bool = False,
        tools: Optional[list] = None,
    ) -> ChatResponse | AsyncIterator[str]:
        """Send chat messages using Ollama API."""
        headers = {"Content-Type": "application/json"}

        data = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
        }

        if stream:
            return self._stream_chat(headers, data)
        else:
            return await self._normal_chat(headers, data)

    async def _normal_chat(self, headers: dict, data: dict) -> ChatResponse:
        """Non-streaming chat request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                headers=headers,
                json=data,
                timeout=120.0,
            )
            response.raise_for_status()
            result = response.json()

            return ChatResponse(
                content=result["message"]["content"],
                model=result["model"],
                usage={
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0)
                    + result.get("eval_count", 0),
                },
            )

    async def _stream_chat(self, headers: dict, data: dict) -> AsyncIterator[str]:
        """Streaming chat request."""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                headers=headers,
                json=data,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            import json

                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                yield chunk["message"]["content"]
                        except json.JSONDecodeError:
                            continue

    def get_available_models(self) -> list[str]:
        """Get list of available Ollama models."""
        # Try to get models from Ollama API
        try:
            import httpx

            response = httpx.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                result = response.json()
                return [model["name"] for model in result.get("models", [])]
        except Exception:
            pass

        # Return common models as fallback
        return [
            "llama3.1",
            "llama3",
            "mistral",
            "codellama",
            "qwen2",
            "gemma2",
        ]

    def validate_api_key(self) -> bool:
        """Ollama doesn't require API key."""
        return True
