"""Chat history management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .providers import Message


class ChatHistory:
    """Manage chat history."""

    def __init__(self, max_size: int = 100):
        self.messages: list[Message] = []
        self.max_size = max_size

    def add_message(self, role_or_msg, content: str = None) -> None:
        """Add a message to history. Accepts Message object or (role, content)."""
        if isinstance(role_or_msg, Message):
            self.messages.append(role_or_msg)
        else:
            self.messages.append(Message(role=role_or_msg, content=content))
        if len(self.messages) > self.max_size:
            self.messages = self.messages[-self.max_size :]

    def get_messages(self) -> list[Message]:
        """Get all messages in history."""
        return self.messages.copy()

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def save(self, filepath: Path) -> None:
        """Save full history to file including tool calls and metadata."""
        data = []
        for msg in self.messages:
            entry = {"role": msg.role, "content": msg.content}
            if msg.tool_calls is not None:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id is not None:
                entry["tool_call_id"] = msg.tool_call_id
            if msg.name is not None:
                entry["name"] = msg.name
            if msg.reasoning_content is not None:
                entry["reasoning_content"] = msg.reasoning_content
            data.append(entry)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, filepath: Path) -> None:
        """Load full history from file including tool calls and metadata."""
        if not filepath.exists():
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.messages = [
            Message(
                role=m["role"],
                content=m.get("content") or "",
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id"),
                name=m.get("name"),
                reasoning_content=m.get("reasoning_content"),
            )
            for m in data
        ]

    def export_markdown(self, filepath: Path) -> None:
        """Export conversation to a Markdown file with structured format."""
        lines = ["# aicli Conversation\n"]
        for msg in self.messages:
            role_label = {
                "system": "## System",
                "user": "## User",
                "assistant": "## Assistant",
                "tool": "## Tool",
            }.get(msg.role, f"## {msg.role}")

            lines.append(f"{role_label}")
            if msg.name:
                lines.append(f"**Tool**: `{msg.name}`")
            if msg.tool_call_id:
                lines.append(f"**Call ID**: `{msg.tool_call_id}`")
            if msg.reasoning_content:
                lines.append("\n<reasoning>\n")
                lines.append(msg.reasoning_content)
                lines.append("\n</reasononing>\n")
            if msg.tool_calls:
                lines.append("\n<tool_calls>\n")
                lines.append("```json")
                lines.append(json.dumps(msg.tool_calls, ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")
            if msg.content:
                if msg.role == "tool":
                    lines.append(f"\n```\n{msg.content}\n```\n")
                else:
                    lines.append(f"\n{msg.content}\n")
            elif msg.tool_calls:
                lines.append("")  # tool_calls only, no content
            lines.append("---\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def get_history_dir() -> Path:
        """Get the history directory."""
        from .config import get_config_dir

        history_dir = get_config_dir() / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir

    @staticmethod
    def list_sessions() -> list[dict]:
        """List all saved chat sessions."""
        history_dir = ChatHistory.get_history_dir()
        sessions = []
        for file in history_dir.glob("*.json"):
            stat = file.stat()
            sessions.append(
                {
                    "file": file.name,
                    "name": file.stem,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        return sorted(sessions, key=lambda x: x["modified"], reverse=True)
