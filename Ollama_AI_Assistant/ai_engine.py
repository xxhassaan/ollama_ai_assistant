"""
ai_engine.py
------------
Connects to a locally running Ollama service, sends prompts, and returns
AI responses.  Maintains per-session conversation history for multi-turn
dialogue.
"""

import json
import logging
import requests
from typing import Callable, Generator, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class Message:
    """Represents a single chat message."""

    def __init__(self, role: str, content: str):
        if role not in ("user", "assistant", "system"):
            raise ValueError(f"Invalid role: {role}")
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

    def __repr__(self):
        preview = self.content[:60].replace("\n", " ")
        return f"<Message role={self.role!r} content={preview!r}>"


# ---------------------------------------------------------------------------
# AI Engine
# ---------------------------------------------------------------------------

class AIEngine:
    """
    Wraps all Ollama API communication.

    - Uses /api/chat for multi-turn conversations (preferred).
    - Falls back to /api/generate for simple single-shot prompts.
    - Never raises exceptions to callers; always returns a structured dict.
    """

    def __init__(self, config_manager):
        self.cfg = config_manager
        self.history: List[Message] = []
        self._system_prompt = (
            "You are a helpful AI desktop assistant. "
            "Answer concisely but completely. "
            "When asked to open an application, say you will attempt to open it."
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def host(self) -> str:
        return self.cfg.get("ollama_host", "http://localhost:11434")

    @property
    def model(self) -> str:
        return self.cfg.get("model", "qwen3:8b")

    @property
    def chat_url(self) -> str:
        return f"{self.host}/api/chat"

    @property
    def generate_url(self) -> str:
        return f"{self.host}/api/generate"

    @property
    def tags_url(self) -> str:
        return f"{self.host}/api/tags"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(
        self,
        user_text: str,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """
        Send a user message and return a response dict:
            {
                "success": bool,
                "text": str,          # full response or error message
                "error": str | None
            }

        If stream_callback is provided, partial tokens are passed to it
        as they arrive (streaming mode).
        """
        if not user_text.strip():
            return {"success": False, "text": "", "error": "Empty input"}

        # Record the user turn
        self.history.append(Message("user", user_text))

        try:
            if stream_callback:
                full_text = self._chat_streaming(stream_callback)
            else:
                full_text = self._chat_blocking()

            # Record the assistant turn
            self.history.append(Message("assistant", full_text))
            logger.info("AI response received (%d chars).", len(full_text))
            return {"success": True, "text": full_text, "error": None}

        except requests.exceptions.ConnectionError:
            err = "Cannot connect to Ollama. Is the service running?"
            logger.error(err)
            self.history.pop()  # remove the failed user message
            return {"success": False, "text": err, "error": err}

        except requests.exceptions.Timeout:
            err = "Ollama request timed out. Try again."
            logger.error(err)
            self.history.pop()
            return {"success": False, "text": err, "error": err}

        except Exception as exc:  # pylint: disable=broad-except
            err = f"Unexpected error: {exc}"
            logger.exception(err)
            self.history.pop()
            return {"success": False, "text": err, "error": err}

    def clear_history(self) -> None:
        """Wipe conversation memory."""
        self.history.clear()
        logger.info("Conversation history cleared.")

    def set_model(self, model_name: str) -> None:
        """Dynamically switch the active model."""
        self.cfg.set("model", model_name)
        logger.info("Model switched to %s", model_name)

    # ------------------------------------------------------------------
    # Ollama availability checks
    # ------------------------------------------------------------------

    def is_ollama_running(self) -> bool:
        """Return True if the Ollama HTTP service is reachable."""
        try:
            resp = requests.get(self.tags_url, timeout=3)
            return resp.status_code == 200
        except Exception:  # pylint: disable=broad-except
            return False

    def list_models(self) -> List[str]:
        """Return list of locally available model names."""
        try:
            resp = requests.get(self.tags_url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Could not list models: %s", exc)
            return []

    def model_exists(self, model_name: Optional[str] = None) -> bool:
        """Return True if *model_name* (or the configured model) is available."""
        target = model_name or self.model
        return any(target in m for m in self.list_models())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(self) -> List[dict]:
        """Assemble the full message list (system + history) for /api/chat."""
        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(msg.to_dict() for msg in self.history)
        return messages

    def _chat_blocking(self) -> str:
        """POST to /api/chat without streaming; return the full response text."""
        payload = {
            "model": self.model,
            "messages": self._build_messages(),
            "stream": False,
        }
        resp = requests.post(self.chat_url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()

    def _chat_streaming(self, callback: Callable[[str], None]) -> str:
        """
        POST to /api/chat with streaming=True.
        Calls *callback* for each token fragment as it arrives.
        Returns the accumulated full text.
        """
        payload = {
            "model": self.model,
            "messages": self._build_messages(),
            "stream": True,
        }
        full_text = []
        with requests.post(
            self.chat_url, json=payload, stream=True, timeout=120
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_text.append(token)
                    callback(token)
                if chunk.get("done"):
                    break
        return "".join(full_text).strip()
