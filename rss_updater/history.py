from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from filelock import FileLock

from rss_updater.models import CheckResult

logger = logging.getLogger("rss_updater.history")


class HistoryManager:
    def __init__(self, history_dir: Path) -> None:
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.history_dir / "history.json"
        self.lock_file = self.history_dir / "history.lock"
        self.lock = FileLock(str(self.lock_file), timeout=10)

    def load_history(self) -> dict[str, Any]:
        with self.lock:
            return self._load_history_unlocked()

    def _load_history_unlocked(self) -> dict[str, Any]:
        if not self.history_file.exists():
            return {}
        try:
            content = self.history_file.read_text(encoding="utf-8")
            return json.loads(content) if content else {}
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load history, returning empty")
            return {}

    def save_history(self, history: dict[str, Any]) -> None:
        with self.lock:
            self._save_history_unlocked(history)

    def _save_history_unlocked(self, history: dict[str, Any]) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.history_dir),
            suffix=".tmp",
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.history_file)
        except Exception:
            logger.exception("Failed to save history")
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def get_last_content_hash(self, feed_name: str) -> str | None:
        with self.lock:
            history = self._load_history_unlocked()
            feed_data: dict[str, Any] = history.get(feed_name, {})
            return feed_data.get("last_content_hash")

    def set_last_content_hash(self, feed_name: str, content_hash: str) -> None:
        with self.lock:
            history = self._load_history_unlocked()
            if feed_name not in history:
                history[feed_name] = {}
            history[feed_name]["last_content_hash"] = content_hash
            self._save_history_unlocked(history)

    def get_known_guids(self, feed_name: str) -> set[str]:
        with self.lock:
            history = self._load_history_unlocked()
            feed_data: dict[str, Any] = history.get(feed_name, {})
            return set(feed_data.get("known_guids", []))

    def add_known_guids(self, feed_name: str, guids: set[str]) -> None:
        with self.lock:
            history = self._load_history_unlocked()
            if feed_name not in history:
                history[feed_name] = {}
            existing: set[str] = set(history[feed_name].get("known_guids", []))
            existing.update(guids)
            history[feed_name]["known_guids"] = list(existing)
            self._save_history_unlocked(history)

    def add_check_result(self, result: CheckResult) -> None:
        with self.lock:
            history = self._load_history_unlocked()
            if result.feed_name not in history:
                history[result.feed_name] = {}
            checks: list[dict[str, Any]] = history[result.feed_name].get("checks", [])
            checks.append(
                {
                    "status": result.status,
                    "timestamp": result.timestamp,
                    "articles_count": result.articles_count,
                    "new_articles_count": len(result.new_articles),
                    "error_message": result.error_message,
                    "content_hash": result.content_hash,
                }
            )
            history[result.feed_name]["checks"] = checks
            self._cleanup_old_checks(history)
            self._save_history_unlocked(history)

    def get_recent_checks(self, feed_name: str, limit: int = 10) -> list[dict[str, Any]]:
        history = self.load_history()
        checks: list[dict[str, Any]] = history.get(feed_name, {}).get("checks", [])
        sorted_checks = sorted(
            checks,
            key=lambda c: c.get("timestamp", ""),
            reverse=True,
        )
        return sorted_checks[:limit]

    def _cleanup_old_checks(self, history: dict[str, Any]) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        for feed_name in list(history.keys()):
            feed_data = history.get(feed_name, {})
            checks: list[dict[str, Any]] = feed_data.get("checks", [])
            cleaned = [c for c in checks if self._parse_timestamp(c.get("timestamp", "")) > cutoff]
            if cleaned:
                history[feed_name]["checks"] = cleaned
            else:
                history[feed_name].pop("checks", None)
                if not history[feed_name]:
                    history.pop(feed_name, None)

    @staticmethod
    def _parse_timestamp(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)
