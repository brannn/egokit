"""Log parsers for Claude Code and Augment session formats.

Pure Python stdlib implementation - no external dependencies.
Parses JSONL (Claude Code) and JSON (Augment) formats into normalized Session objects.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .models import Message, MessageRole, Session

if TYPE_CHECKING:
    from collections.abc import Iterator

# Threshold for detecting millisecond timestamps (timestamps after year ~2001 in ms)
MILLISECOND_TIMESTAMP_THRESHOLD = 1e12


class LogParser(ABC):
    """Abstract base class for session log parsers."""

    @abstractmethod
    def parse(self, path: Path) -> Iterator[Session]:
        """Parse log files from the given path.

        Args:
            path: Path to log file or directory

        Yields:
            Session objects parsed from the logs
        """

    @abstractmethod
    def discover(self, root: Path) -> list[Path]:
        """Discover parseable log files under the given root.

        Args:
            root: Root directory to search

        Returns:
            List of paths to parseable log files
        """


class ClaudeCodeParser(LogParser):
    """Parser for Claude Code JSONL session logs.

    Claude Code stores logs at ~/.claude/projects/{project-path}/{uuid}.jsonl
    Each line is a JSON object representing a message or event.
    """

    DEFAULT_PATH = Path.home() / ".claude" / "projects"

    def discover(self, root: Path | None = None) -> list[Path]:
        """Discover Claude Code JSONL log files.

        Args:
            root: Root path to search (defaults to ~/.claude/projects)

        Returns:
            List of paths to .jsonl files
        """
        search_root = root or self.DEFAULT_PATH
        if not search_root.exists():
            return []

        return list(search_root.rglob("*.jsonl"))

    def parse(self, path: Path) -> Iterator[Session]:
        """Parse a Claude Code JSONL log file.

        Args:
            path: Path to .jsonl file

        Yields:
            Session objects (one per file)
        """
        if not path.exists() or path.suffix != ".jsonl":
            return

        messages: list[Message] = []
        start_time: datetime | None = None
        end_time: datetime | None = None

        with path.open(encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = self._parse_entry(entry)
                if msg:
                    messages.append(msg)
                    if msg.timestamp:
                        if start_time is None or msg.timestamp < start_time:
                            start_time = msg.timestamp
                        if end_time is None or msg.timestamp > end_time:
                            end_time = msg.timestamp

        if messages:
            # Extract project path from file location
            project_path = self._extract_project_path(path)

            yield Session(
                session_id=path.stem,
                messages=messages,
                source="claude_code",
                project_path=project_path,
                start_time=start_time,
                end_time=end_time,
            )

    def _parse_entry(self, entry: dict[str, object]) -> Message | None:
        """Parse a single JSONL entry into a Message.

        Args:
            entry: Parsed JSON object from log line

        Returns:
            Message object or None if not a valid message
        """
        # Claude Code uses 'type' field to distinguish message types
        entry_type = entry.get("type", "")

        # Helper to extract timestamp safely
        def get_timestamp() -> datetime | None:
            ts_val = entry.get("timestamp")
            if isinstance(ts_val, str | float | int):
                return self._parse_timestamp(ts_val)
            return None

        # Handle different message formats
        if entry_type == "human" or entry.get("role") == "user":
            content = entry.get("message", {})
            if isinstance(content, dict):
                text = content.get("content", "")
            else:
                text = str(content)
            return Message(role=MessageRole.USER, content=str(text), timestamp=get_timestamp())

        if entry_type == "assistant" or entry.get("role") == "assistant":
            content = entry.get("message", {})
            if isinstance(content, dict):
                text = content.get("content", "")
            else:
                text = str(content)
            return Message(role=MessageRole.ASSISTANT, content=str(text), timestamp=get_timestamp())

        return None

    def _parse_timestamp(self, ts: str | float | None) -> datetime | None:
        """Parse timestamp from various formats."""
        if ts is None:
            return None
        if isinstance(ts, float | int):
            return datetime.fromtimestamp(ts, tz=UTC)
        # ts is str at this point
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _extract_project_path(self, log_path: Path) -> str | None:
        """Extract project path from Claude Code log file location."""
        # Path structure: ~/.claude/projects/{encoded-project-path}/{uuid}.jsonl
        parts = log_path.parts
        try:
            projects_idx = parts.index("projects")
            if projects_idx + 1 < len(parts) - 1:
                # The encoded path is between 'projects' and the uuid file
                encoded = parts[projects_idx + 1]
                # Decode: -Users-foo-myproject -> /Users/foo/myproject
                return "/" + encoded.replace("-", "/").lstrip("/")
        except (ValueError, IndexError):
            pass
        return None


class AugmentParser(LogParser):
    """Parser for Augment JSON conversation exports.

    Augment exports conversations as JSON files with a chatHistory array.
    Each entry contains request_message, response_text, and structured_output_nodes.
    """

    def discover(self, root: Path) -> list[Path]:
        """Discover Augment JSON export files.

        Args:
            root: Root directory to search

        Returns:
            List of paths to Augment JSON files
        """
        if not root.exists():
            return []

        # If root is a file, check if it's a valid export
        if root.is_file():
            if self._is_augment_export(root):
                return [root]
            return []

        # Look for files that match Augment export patterns
        candidates: list[Path] = []

        # Common patterns for Augment exports (including timestamp exports)
        patterns = [
            "*Augment*.json",
            "*augment*.json",
            "conversation*.json",
            "*_2025-*.json",  # Timestamp pattern: _2025-12-01T...
            "*_2024-*.json",
        ]
        for pattern in patterns:
            candidates.extend(root.glob(pattern))

        # Also check all .json files for valid Augment format
        for json_file in root.glob("*.json"):
            if json_file not in candidates:
                candidates.append(json_file)

        # Filter to only valid Augment exports
        valid_files: list[Path] = []
        for path in candidates:
            if self._is_augment_export(path):
                valid_files.append(path)

        return valid_files

    def _is_augment_export(self, path: Path) -> bool:
        """Check if a JSON file is a valid Augment export."""
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            # Augment exports have chatHistory - either at root or nested in conversation
            if not isinstance(data, dict):
                return False
            if "chatHistory" in data:
                return True
            # Check for nested structure: {conversation: {chatHistory: [...]}}
            conv = data.get("conversation", {})
            return isinstance(conv, dict) and "chatHistory" in conv
        except (json.JSONDecodeError, OSError):
            return False

    def _extract_chat_history(self, data: dict[str, object]) -> list[object]:
        """Extract chatHistory from Augment export (handles both formats)."""
        # Try root-level chatHistory first
        if "chatHistory" in data:
            history = data.get("chatHistory")
            if isinstance(history, list):
                return history

        # Try nested conversation.chatHistory
        conv = data.get("conversation")
        if isinstance(conv, dict) and "chatHistory" in conv:
            history = conv.get("chatHistory")
            if isinstance(history, list):
                return history

        return []

    def parse(self, path: Path) -> Iterator[Session]:
        """Parse an Augment JSON export file.

        Args:
            path: Path to JSON file

        Yields:
            Session objects parsed from the export
        """
        if not path.exists() or path.suffix != ".json":
            return

        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        if not isinstance(data, dict):
            return

        chat_history = self._extract_chat_history(data)
        if not chat_history:
            return

        messages: list[Message] = []
        start_time: datetime | None = None
        end_time: datetime | None = None

        for entry in chat_history:
            if not isinstance(entry, dict):
                continue

            msg_pair = self._parse_entry(entry)
            for msg in msg_pair:
                messages.append(msg)
                if msg.timestamp:
                    if start_time is None or msg.timestamp < start_time:
                        start_time = msg.timestamp
                    if end_time is None or msg.timestamp > end_time:
                        end_time = msg.timestamp

        if messages:
            yield Session(
                session_id=path.stem,
                messages=messages,
                source="augment",
                project_path=str(path.parent),
                start_time=start_time,
                end_time=end_time,
            )

    def _parse_entry(self, entry: dict[str, object]) -> list[Message]:
        """Parse a single chat history entry into Messages.

        Augment entries typically contain both user request and assistant response.

        Args:
            entry: Chat history entry object

        Returns:
            List of Message objects (usually user + assistant pair)
        """
        messages: list[Message] = []
        ts_value = entry.get("timestamp")
        timestamp = self._parse_timestamp(
            ts_value if isinstance(ts_value, str | float | int) else None,
        )

        # Parse user message
        request = entry.get("request_message", "")
        if request:
            messages.append(Message(
                role=MessageRole.USER,
                content=str(request),
                timestamp=timestamp,
            ))

        # Parse assistant response
        response = entry.get("response_text", "")
        if not response:
            # Try structured_output_nodes for code-heavy responses
            nodes = entry.get("structured_output_nodes", [])
            if isinstance(nodes, list):
                response = self._extract_text_from_nodes(nodes)

        if response:
            messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=str(response),
                timestamp=timestamp,
            ))

        return messages

    def _extract_text_from_nodes(self, nodes: list[object]) -> str:
        """Extract text content from structured output nodes."""
        texts: list[str] = []
        for node in nodes:
            if isinstance(node, dict):
                text = node.get("text", "") or node.get("content", "")
                if text:
                    texts.append(str(text))
        return "\n".join(texts)

    def _parse_timestamp(self, ts: str | float | None) -> datetime | None:
        """Parse timestamp from various formats."""
        if ts is None:
            return None
        if isinstance(ts, float | int):
            # Handle milliseconds (Augment may use ms timestamps)
            if ts > MILLISECOND_TIMESTAMP_THRESHOLD:
                ts = ts / 1000
            return datetime.fromtimestamp(ts, tz=UTC)
        # ts is str at this point
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None

