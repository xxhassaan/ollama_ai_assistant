"""
config_manager.py
-----------------
Handles loading, saving, and validating application configuration.
Automatically creates config.json with defaults if missing.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "model": "qwen3:8b",
    "voice_enabled": True,
    "theme": "dark",
    "ollama_host": "http://localhost:11434",
    "max_history": 50,
    "speech_rate": 175,
    "speech_volume": 1.0
}


class ConfigManager:
    """Manages persistent application configuration via JSON."""

    def __init__(self, path: str = CONFIG_PATH):
        self.path = path
        self.config: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, fallback=None):
        """Return a config value, falling back to the default or provided fallback."""
        return self.config.get(key, DEFAULT_CONFIG.get(key, fallback))

    def set(self, key: str, value) -> None:
        """Set a single config value and persist to disk."""
        self.config[key] = value
        self._save()

    def update(self, updates: dict) -> None:
        """Apply multiple updates at once and persist."""
        self.config.update(updates)
        self._save()

    def all(self) -> dict:
        """Return a shallow copy of the full config."""
        return dict(self.config)

    def reset_to_defaults(self) -> None:
        """Overwrite config with defaults and persist."""
        self.config = dict(DEFAULT_CONFIG)
        self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load config from disk, merging with defaults for missing keys."""
        if not os.path.exists(self.path):
            logger.info("config.json not found – creating with defaults.")
            self.config = dict(DEFAULT_CONFIG)
            self._save()
            return

        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            # Merge: start from defaults so new keys are always present
            merged = dict(DEFAULT_CONFIG)
            merged.update(loaded)
            self.config = merged
            logger.info("Configuration loaded from %s", self.path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load config (%s) – using defaults.", exc)
            self.config = dict(DEFAULT_CONFIG)

    def _save(self) -> None:
        """Persist current config to disk."""
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.config, fh, indent=4)
            logger.debug("Configuration saved to %s", self.path)
        except OSError as exc:
            logger.error("Failed to save config: %s", exc)

    def _validate(self) -> None:
        """Ensure required keys exist; fill missing ones from defaults."""
        changed = False
        for key, default_val in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = default_val
                changed = True
        if changed:
            self._save()
