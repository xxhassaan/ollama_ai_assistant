"""
settings.py
-----------
Provides a Tkinter Toplevel settings dialog that lets the user change:
  - Ollama model name
  - Voice enabled toggle
  - UI theme
  - Speech rate and volume
Settings are persisted via ConfigManager.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SettingsWindow:
    """Modal settings dialog."""

    def __init__(
        self,
        parent: tk.Tk,
        config_manager,
        ai_engine=None,
        on_save: Optional[Callable] = None,
        theme: str = "dark",
    ):
        self.cfg = config_manager
        self.ai_engine = ai_engine
        self.on_save = on_save
        self.theme = theme

        # Colours
        if theme == "dark":
            self.BG = "#1a1a2e"
            self.PANEL = "#16213e"
            self.ACCENT = "#e94560"
            self.FG = "#eaeaea"
            self.ENTRY_BG = "#0f3460"
            self.BTN_BG = "#e94560"
            self.BTN_FG = "#ffffff"
        else:
            self.BG = "#f0f2f5"
            self.PANEL = "#ffffff"
            self.ACCENT = "#2563eb"
            self.FG = "#1e293b"
            self.ENTRY_BG = "#e2e8f0"
            self.BTN_BG = "#2563eb"
            self.BTN_FG = "#ffffff"

        self.win = tk.Toplevel(parent)
        self.win.title("Settings")
        self.win.geometry("460x480")
        self.win.resizable(False, False)
        self.win.configure(bg=self.BG)
        self.win.transient(parent)
        self.win.grab_set()

        self._vars: dict = {}
        self._build_ui()
        self._load_values()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build all widgets."""
        pad = {"padx": 20, "pady": 8}

        # Title
        tk.Label(
            self.win, text="⚙  Settings",
            font=("Segoe UI", 16, "bold"),
            bg=self.BG, fg=self.ACCENT
        ).pack(pady=(20, 10))

        frame = tk.Frame(self.win, bg=self.PANEL, bd=0)
        frame.pack(fill="both", expand=True, padx=20, pady=5)

        # --- Model ---
        self._section(frame, "AI Model")
        self._vars["model"] = tk.StringVar()
        model_row = tk.Frame(frame, bg=self.PANEL)
        model_row.pack(fill="x", **pad)
        tk.Label(model_row, text="Ollama Model:", bg=self.PANEL, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Entry(model_row, textvariable=self._vars["model"],
                 bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
                 font=("Segoe UI", 10), relief="flat", width=22
                 ).pack(side="right")

        # Model list button
        if self.ai_engine:
            tk.Button(
                frame, text="🔄 Refresh available models",
                command=self._refresh_models,
                bg=self.ENTRY_BG, fg=self.FG,
                font=("Segoe UI", 9), relief="flat", cursor="hand2"
            ).pack(pady=(0, 4))

        # --- Voice ---
        self._section(frame, "Voice Output")
        self._vars["voice_enabled"] = tk.BooleanVar()
        voice_row = tk.Frame(frame, bg=self.PANEL)
        voice_row.pack(fill="x", **pad)
        tk.Label(voice_row, text="Enable voice output:", bg=self.PANEL, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side="left")
        ttk.Checkbutton(voice_row, variable=self._vars["voice_enabled"]
                        ).pack(side="right")

        # Speech rate
        self._vars["speech_rate"] = tk.IntVar()
        rate_row = tk.Frame(frame, bg=self.PANEL)
        rate_row.pack(fill="x", **pad)
        tk.Label(rate_row, text="Speech rate (wpm):", bg=self.PANEL, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Scale(rate_row, variable=self._vars["speech_rate"],
                 from_=80, to=300, orient="horizontal",
                 bg=self.PANEL, fg=self.FG, troughcolor=self.ENTRY_BG,
                 highlightthickness=0, length=140
                 ).pack(side="right")

        # --- Theme ---
        self._section(frame, "Appearance")
        self._vars["theme"] = tk.StringVar()
        theme_row = tk.Frame(frame, bg=self.PANEL)
        theme_row.pack(fill="x", **pad)
        tk.Label(theme_row, text="Theme:", bg=self.PANEL, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side="left")
        ttk.Combobox(
            theme_row, textvariable=self._vars["theme"],
            values=["dark", "light"], state="readonly", width=10
        ).pack(side="right")

        # --- Buttons ---
        btn_frame = tk.Frame(self.win, bg=self.BG)
        btn_frame.pack(fill="x", padx=20, pady=15)

        tk.Button(
            btn_frame, text="Save", command=self._save,
            bg=self.BTN_BG, fg=self.BTN_FG,
            font=("Segoe UI", 11, "bold"), relief="flat",
            cursor="hand2", width=10
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            btn_frame, text="Cancel", command=self.win.destroy,
            bg=self.ENTRY_BG, fg=self.FG,
            font=("Segoe UI", 11), relief="flat",
            cursor="hand2", width=10
        ).pack(side="right")

        tk.Button(
            btn_frame, text="Reset Defaults", command=self._reset,
            bg=self.ENTRY_BG, fg=self.FG,
            font=("Segoe UI", 10), relief="flat",
            cursor="hand2"
        ).pack(side="left")

    def _section(self, parent, label: str) -> None:
        """Render a section header."""
        tk.Label(parent, text=label,
                 bg=self.PANEL, fg=self.ACCENT,
                 font=("Segoe UI", 10, "bold")
                 ).pack(anchor="w", padx=20, pady=(12, 0))
        tk.Frame(parent, bg=self.ACCENT, height=1).pack(fill="x", padx=20, pady=(2, 0))

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        """Populate form fields from config."""
        self._vars["model"].set(self.cfg.get("model", "qwen3:8b"))
        self._vars["voice_enabled"].set(self.cfg.get("voice_enabled", True))
        self._vars["speech_rate"].set(self.cfg.get("speech_rate", 175))
        self._vars["theme"].set(self.cfg.get("theme", "dark"))

    def _save(self) -> None:
        """Validate and persist settings."""
        model = self._vars["model"].get().strip()
        if not model:
            messagebox.showerror("Validation", "Model name cannot be empty.", parent=self.win)
            return

        self.cfg.update({
            "model": model,
            "voice_enabled": self._vars["voice_enabled"].get(),
            "speech_rate": self._vars["speech_rate"].get(),
            "theme": self._vars["theme"].get(),
        })
        logger.info("Settings saved.")

        if self.on_save:
            self.on_save()

        messagebox.showinfo(
            "Settings", "Settings saved.\nSome changes take effect on restart.",
            parent=self.win
        )
        self.win.destroy()

    def _reset(self) -> None:
        """Reset config to defaults and reload form."""
        if messagebox.askyesno("Reset", "Reset all settings to defaults?", parent=self.win):
            self.cfg.reset_to_defaults()
            self._load_values()

    def _refresh_models(self) -> None:
        """Fetch available models from Ollama and update the combobox hint."""
        models = self.ai_engine.list_models() if self.ai_engine else []
        if models:
            messagebox.showinfo(
                "Available Models",
                "Models found on Ollama:\n\n" + "\n".join(models),
                parent=self.win
            )
        else:
            messagebox.showwarning(
                "No Models",
                "Could not retrieve model list.\nIs Ollama running?",
                parent=self.win
            )
