"""
gui.py
------
Main Tkinter desktop window for the Ollama AI Assistant.
Voice ONLY works in CALL MODE - text messages are silent.
"""

import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ai_engine import AIEngine
from speech_input import SpeechInput
from speech_output import SpeechOutput
from app_launcher import AppLauncher
from settings import SettingsWindow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Colour palettes
# ---------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg":           "#0d0d1a",
        "sidebar":      "#12122b",
        "chat_bg":      "#0d0d1a",
        "user_bubble":  "#1a3a5c",
        "user_fg":      "#e0f0ff",
        "ai_bubble":    "#1e1e3a",
        "ai_fg":        "#e8e8f0",
        "input_bg":     "#1a1a2e",
        "input_fg":     "#eaeaea",
        "accent":       "#7c6af7",
        "accent2":      "#e94560",
        "status_bg":    "#12122b",
        "status_fg":    "#8888aa",
        "btn_bg":       "#7c6af7",
        "btn_fg":       "#ffffff",
        "send_bg":      "#e94560",
        "muted":        "#444466",
        "border":       "#2a2a4a",
        "typing_fg":    "#9090bb",
        "call_active":  "#00ff88",
        "call_inactive": "#e94560",
    },
    "light": {
        "bg":           "#f5f6fa",
        "sidebar":      "#ffffff",
        "chat_bg":      "#f5f6fa",
        "user_bubble":  "#2563eb",
        "user_fg":      "#ffffff",
        "ai_bubble":    "#ffffff",
        "ai_fg":        "#1e293b",
        "input_bg":     "#ffffff",
        "input_fg":     "#1e293b",
        "accent":       "#2563eb",
        "accent2":      "#ef4444",
        "status_bg":    "#e2e8f0",
        "status_fg":    "#64748b",
        "btn_bg":       "#2563eb",
        "btn_fg":       "#ffffff",
        "send_bg":      "#ef4444",
        "muted":        "#94a3b8",
        "border":       "#e2e8f0",
        "typing_fg":    "#94a3b8",
        "call_active":  "#10b981",
        "call_inactive": "#ef4444",
    }
}


# ---------------------------------------------------------------------------
# ChatBubble widget
# ---------------------------------------------------------------------------
class ChatBubble(tk.Frame):
    def __init__(self, parent, text: str, role: str, colors: dict, **kwargs):
        super().__init__(parent, bg=colors["chat_bg"], **kwargs)

        is_user = (role == "user")
        bubble_bg  = colors["user_bubble"] if is_user else colors["ai_bubble"]
        bubble_fg  = colors["user_fg"]     if is_user else colors["ai_fg"]
        anchor_side = "e" if is_user else "w"
        label_text  = "You" if is_user else "Assistant"
        label_fg    = colors["accent"] if is_user else colors["muted"]

        wrapper = tk.Frame(self, bg=colors["chat_bg"])
        wrapper.pack(fill="x", padx=12, pady=(4, 2))

        tk.Label(
            wrapper, text=label_text,
            font=("Segoe UI", 8, "bold"),
            bg=colors["chat_bg"], fg=label_fg
        ).pack(anchor=anchor_side)

        bubble = tk.Frame(wrapper, bg=bubble_bg, padx=12, pady=8)
        bubble.pack(anchor=anchor_side, fill="none")

        tk.Label(
            bubble, text=text, wraplength=520, justify="left",
            bg=bubble_bg, fg=bubble_fg, font=("Segoe UI", 11)
        ).pack(anchor="w")


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------
class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        config_manager,
        ai_engine: AIEngine,
        speech_input: SpeechInput,
        speech_output: SpeechOutput,
        app_launcher: AppLauncher,
    ):
        self.root = root
        self.cfg = config_manager
        self.ai = ai_engine
        self.si = speech_input
        self.so = speech_output
        self.launcher = app_launcher

        self.theme_name: str = self.cfg.get("theme", "dark")
        self.c = THEMES[self.theme_name]

        self._ui_queue: queue.Queue = queue.Queue()
        self._typing_dots = 0
        self._typing_job: Optional[str] = None

        # Call mode variables
        self._call_mode_active = False
        self._call_thread: Optional[threading.Thread] = None
        self._stop_call_flag = threading.Event()

        self._build_window()
        self._build_layout()
        self._welcome_message()
        self._process_ui_queue()

        self._in_conversation_mode = False

    def _build_window(self) -> None:
        self.root.title("Ollama AI Assistant")
        self.root.geometry("860x640")
        self.root.minsize(620, 480)
        self.root.configure(bg=self.c["bg"])

    def _build_layout(self) -> None:
        c = self.c

        # Top bar
        topbar = tk.Frame(self.root, bg=c["sidebar"], height=54)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(
            topbar, text="🤖  Ollama AI Assistant",
            font=("Segoe UI", 14, "bold"),
            bg=c["sidebar"], fg=c["accent"]
        ).pack(side="left", padx=16, pady=8)

        self._btn_voice = self._toolbar_btn(topbar, "🔊", self._toggle_voice, side="right")
        self._btn_clear = self._toolbar_btn(topbar, "🗑", self._clear_chat, side="right")
        self._btn_settings = self._toolbar_btn(topbar, "⚙", self._open_settings, side="right")

        self._lbl_voice_state = tk.Label(
            topbar, text="Voice ON" if self.so.enabled else "Voice OFF",
            font=("Segoe UI", 8), bg=c["sidebar"],
            fg=c["accent"] if self.so.enabled else c["muted"]
        )
        self._lbl_voice_state.pack(side="right", padx=(0, 4))

        self._lbl_conversation_mode = tk.Label(
            topbar, text="🎤 Listening for 'Hey Bro'...",
            font=("Segoe UI", 8, "italic"),
            bg=c["sidebar"], fg=c["accent2"]
        )
        self._lbl_conversation_mode.pack(side="right", padx=(0, 16))

        # Chat area
        chat_frame = tk.Frame(self.root, bg=c["bg"])
        chat_frame.pack(fill="both", expand=True, side="top")

        self._canvas = tk.Canvas(chat_frame, bg=c["chat_bg"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(chat_frame, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._chat_inner = tk.Frame(self._canvas, bg=c["chat_bg"])
        self._canvas_window = self._canvas.create_window((0, 0), window=self._chat_inner, anchor="nw")
        self._chat_inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

        self._lbl_typing = tk.Label(
            self._chat_inner, text="", font=("Segoe UI", 10, "italic"),
            bg=c["chat_bg"], fg=c["typing_fg"]
        )

        # Bottom input bar
        input_bar = tk.Frame(self.root, bg=c["sidebar"], pady=10)
        input_bar.pack(fill="x", side="bottom")

        self._btn_call = tk.Button(
            input_bar, text="📞", font=("Segoe UI", 14),
            bg=c["input_bg"], fg=c["call_inactive"],
            relief="flat", cursor="hand2", command=self._toggle_call_mode
        )
        self._btn_call.pack(side="left", padx=(12, 6))

        self._btn_mic = tk.Button(
            input_bar, text="🎙", font=("Segoe UI", 16),
            bg=c["input_bg"], fg=c["accent"],
            relief="flat", cursor="hand2", command=self._on_mic_click
        )
        self._btn_mic.pack(side="left", padx=(0, 6))

        self._entry = tk.Text(
            input_bar, height=2, font=("Segoe UI", 11),
            bg=c["input_bg"], fg=c["input_fg"], insertbackground=c["input_fg"],
            relief="flat", wrap="word", padx=10, pady=6
        )
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", self._on_enter_key)
        self._entry.bind("<Shift-Return>", self._on_shift_enter)

        self._btn_send = tk.Button(
            input_bar, text="Send ➤", font=("Segoe UI", 11, "bold"),
            bg=c["send_bg"], fg=c["btn_fg"], relief="flat", cursor="hand2",
            padx=16, pady=8, command=self._on_send
        )
        self._btn_send.pack(side="right", padx=(6, 12))

        # Status bar
        self._status_var = tk.StringVar(value="Ready.")
        status_bar = tk.Frame(self.root, bg=c["status_bg"], height=22)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        tk.Label(
            status_bar, textvariable=self._status_var,
            font=("Segoe UI", 8), bg=c["status_bg"], fg=c["status_fg"], anchor="w"
        ).pack(side="left", padx=8)

    def _toolbar_btn(self, parent, text: str, cmd, side="right") -> tk.Button:
        btn = tk.Button(
            parent, text=text, font=("Segoe UI", 13),
            bg=self.c["sidebar"], fg=self.c["muted"],
            relief="flat", cursor="hand2", activebackground=self.c["border"],
            command=cmd
        )
        btn.pack(side=side, padx=4, pady=6)
        return btn

    def _append_bubble(self, text: str, role: str) -> None:
        bubble = ChatBubble(self._chat_inner, text=text, role=role, colors=self.c)
        bubble.pack(fill="x", pady=2)
        self._scroll_to_bottom()

    def _welcome_message(self) -> None:
        model = self.cfg.get("model", "qwen3:8b")
        wake_word = self.cfg.get("wake_word", "Hey Bro")
        msg = (
            f"Hello! I'm your AI assistant powered by {model}.\n"
            f"💬 Say '{wake_word}' to activate voice mode!\n"
            f"📞 Click the CALL button for voice conversation (text mode is silent)!\n"
            "Ask me anything, or say 'open Chrome' to launch an app.\n"
            "Use the microphone button 🎙 for one-time voice input."
        )
        self._append_bubble(msg, "assistant")

    def _scroll_to_bottom(self) -> None:
        self.root.update_idletasks()
        self._canvas.yview_moveto(1.0)

    def _show_typing(self) -> None:
        self._lbl_typing.pack(anchor="w", padx=24, pady=(2, 4))
        self._typing_dots = 0
        self._animate_typing()

    def _hide_typing(self) -> None:
        if self._typing_job:
            self.root.after_cancel(self._typing_job)
            self._typing_job = None
        self._lbl_typing.pack_forget()

    def _animate_typing(self) -> None:
        self._typing_dots = (self._typing_dots + 1) % 4
        self._lbl_typing.config(text="Assistant is typing" + "." * self._typing_dots)
        self._scroll_to_bottom()
        self._typing_job = self.root.after(400, self._animate_typing)

    def _process_ui_queue(self) -> None:
        try:
            while True:
                fn, args = self._ui_queue.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.root.after(30, self._process_ui_queue)

    def _schedule(self, fn, *args) -> None:
        self._ui_queue.put((fn, args))

    def set_conversation_mode(self, active: bool, wake_word: str = "Hey Bro") -> None:
        self._in_conversation_mode = active
        if active:
            self._lbl_conversation_mode.config(
                text="💬 Conversation mode active - Speak naturally!",
                fg=self.c["accent"]
            )
            self._set_status("🎯 Conversation mode active! Just speak naturally.")
        else:
            self._lbl_conversation_mode.config(
                text=f"🎤 Listening for '{wake_word}'...",
                fg=self.c["accent2"]
            )
            self._set_status(f"🎤 Idle - Say '{wake_word}' to activate.")

    # ------------------------------------------------------------------
    # CALL MODE - Voice ONLY works here!
    # ------------------------------------------------------------------

    def _toggle_call_mode(self) -> None:
        if not self.si.available:
            self._set_status("Speech recognition unavailable for call mode.")
            return

        if self._call_mode_active:
            self._stop_call_mode()
        else:
            self._start_call_mode()

    def _start_call_mode(self) -> None:
        self._call_mode_active = True
        self._stop_call_flag.clear()
        self._btn_call.config(fg=self.c["call_active"], text="📞🔴")
        self._set_status("📞 CALL ACTIVE - Voice responses enabled! Speak naturally.")
        self._append_bubble("📞 Call started. Voice responses are now ACTIVE. Say 'hang up' to end.", "assistant")
        
        # Voice greeting (only in call mode)
        if self.so.enabled:
            self.so.speak("Call started. How can I help you?")
        
        self._call_thread = threading.Thread(target=self._call_loop, daemon=True)
        self._call_thread.start()

    def _stop_call_mode(self) -> None:
        self._call_mode_active = False
        self._stop_call_flag.set()
        self._btn_call.config(fg=self.c["call_inactive"], text="📞")
        self._set_status("Call ended. Voice responses disabled.")
        self._append_bubble("📞 Call ended. Voice responses are now OFF.", "assistant")
        
        # Voice goodbye (only in call mode)
        if self.so.enabled:
            self.so.speak("Call ended. Talk to you later!")

    def _call_loop(self) -> None:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                logger.info("Call mode: Microphone calibrated")
        except Exception as e:
            logger.error(f"Call mode mic error: {e}")
            self._schedule(self._set_status, f"Microphone error: {e}")
            self._schedule(self._stop_call_mode)
            return
        
        while self._call_mode_active and not self._stop_call_flag.is_set():
            try:
                with sr.Microphone() as source:
                    self._schedule(self._set_status, "📞 Listening...")
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                    self._schedule(self._set_status, "📞 Processing...")
                    text = recognizer.recognize_google(audio)
                    logger.info(f"Call mode recognized: {text}")
                    
                    if "hang up" in text.lower() or "end call" in text.lower():
                        self._schedule(self._stop_call_mode)
                        break
                    
                    self._schedule(self._append_bubble, text, "user")
                    
                    app_name = self.launcher.detect_open_intent(text)
                    if app_name:
                        result = self.launcher.open(app_name)
                        reply = result["message"]
                        self._schedule(self._append_bubble, reply, "assistant")
                        # Voice response ONLY in call mode
                        if self.so.enabled and self._call_mode_active:
                            self.so.speak(reply)
                        continue
                    
                    self._schedule(self._show_typing)
                    ai_response = self.ai.send_message(text)
                    self._schedule(self._hide_typing)
                    
                    if ai_response.get("success"):
                        response_text = ai_response.get("text", "")
                        self._schedule(self._append_bubble, response_text, "assistant")
                        # Voice response ONLY in call mode
                        if self.so.enabled and self._call_mode_active:
                            self.so.speak(response_text)
                    else:
                        error_msg = ai_response.get("text", "Unknown error")
                        self._schedule(self._append_bubble, f"⚠ {error_msg}", "assistant")
                        if self.so.enabled and self._call_mode_active:
                            self.so.speak("Sorry, I encountered an error.")
                    
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                self._schedule(self._set_status, "📞 Could not understand, please repeat...")
                if self.so.enabled and self._call_mode_active:
                    self.so.speak("Sorry, I didn't catch that. Can you repeat?")
                continue
            except sr.RequestError as e:
                logger.error(f"Call mode recognition error: {e}")
                self._schedule(self._set_status, f"Recognition error: {e}")
                continue
            except Exception as e:
                logger.error(f"Call mode error: {e}")
                continue

    # ------------------------------------------------------------------
    # Event handlers - NO VOICE for text messages!
    # ------------------------------------------------------------------

    def _on_enter_key(self, event) -> str:
        self._on_send()
        return "break"

    def _on_shift_enter(self, event) -> None:
        pass

    def _on_send(self) -> None:
        text = self._entry.get("1.0", "end").strip()
        if not text:
            return
        self._entry.delete("1.0", "end")
        self._process_user_input(text)

    def _on_mic_click(self) -> None:
        if self.si.is_listening:
            self._set_status("Already listening…")
            return
        if not self.si.available:
            self._set_status("Speech recognition unavailable.")
            return

        self._btn_mic.config(fg=self.c["accent2"], text="⏸")
        self._set_status("🎙 Listening…")
        self.si.listen_once(callback=self._on_speech_result, error_callback=self._on_speech_error)

    def _on_speech_result(self, text: str) -> None:
        self._schedule(self._insert_recognised_text, text)

    def _insert_recognised_text(self, text: str) -> None:
        self._btn_mic.config(fg=self.c["accent"], text="🎙")
        self._entry.delete("1.0", "end")
        self._entry.insert("end", text)
        self._set_status(f"Recognised: \"{text[:50]}\"")

    def _on_speech_error(self, msg: str) -> None:
        self._schedule(self._show_speech_error, msg)

    def _show_speech_error(self, msg: str) -> None:
        self._btn_mic.config(fg=self.c["accent"], text="🎙")
        self._set_status(f"Speech error: {msg}")

    def _toggle_voice(self) -> None:
        new_state = not self.so.enabled
        self.so.set_enabled(new_state)
        label = "Voice ON" if new_state else "Voice OFF"
        fg = self.c["accent"] if new_state else self.c["muted"]
        self._lbl_voice_state.config(text=label, fg=fg)
        self._set_status(f"Voice output {'enabled' if new_state else 'disabled'} (only works in Call Mode).")

    def _clear_chat(self) -> None:
        for widget in self._chat_inner.winfo_children():
            widget.destroy()
        self.ai.clear_history()
        self._lbl_typing = tk.Label(
            self._chat_inner, text="", font=("Segoe UI", 10, "italic"),
            bg=self.c["chat_bg"], fg=self.c["typing_fg"]
        )
        self._welcome_message()
        self._set_status("Chat cleared.")

    def _open_settings(self) -> None:
        SettingsWindow(
            parent=self.root, config_manager=self.cfg, ai_engine=self.ai,
            on_save=self._on_settings_saved, theme=self.theme_name,
        )

    def _on_settings_saved(self) -> None:
        self.ai.set_model(self.cfg.get("model"))
        self._set_status(f"Settings applied. Model: {self.cfg.get('model')}")
        wake_word = self.cfg.get("wake_word", "Hey Bro")
        if not self._in_conversation_mode:
            self._lbl_conversation_mode.config(text=f"🎤 Listening for '{wake_word}'...")

    # ------------------------------------------------------------------
    # Core logic - NO VOICE for text/button input!
    # ------------------------------------------------------------------

    def _process_user_input(self, text: str, from_wake_word: bool = False) -> None:
        self._append_bubble(text, "user")
        
        if from_wake_word:
            self._set_status("🎯 Command received! Processing...")

        app_name = self.launcher.detect_open_intent(text)
        if app_name:
            result = self.launcher.open(app_name)
            reply = result["message"]
            self._append_bubble(reply, "assistant")
            # NO VOICE for app launch responses in text mode
            self._set_status(reply)
            return

        self._set_status("Thinking…")
        self._set_input_enabled(False)
        self._show_typing()
        thread = threading.Thread(target=self._ai_worker, args=(text,), daemon=True)
        thread.start()

    def _ai_worker(self, user_text: str) -> None:
        result = self.ai.send_message(user_text)
        self._schedule(self._on_ai_response, result)

    def _on_ai_response(self, result: dict) -> None:
        self._hide_typing()
        self._set_input_enabled(True)

        if result["success"]:
            text = result["text"]
            self._append_bubble(text, "assistant")
            self._set_status("Ready.")
            # NO VOICE for text responses - ONLY in call mode!
        else:
            error_msg = result.get("text", "Unknown error")
            self._append_bubble(f"⚠ {error_msg}", "assistant")
            self._set_status(f"Error: {error_msg}")

    def on_wake_word_command(self, command_text: str) -> None:
        logger.info(f"🎯 Wake word command received in GUI: {command_text}")
        self._schedule(self._process_user_input, command_text, True)

    def on_wake_word_error(self, error_msg: str) -> None:
        self._schedule(self._set_status, f"Wake word error: {error_msg}")

    def _set_status(self, msg: str) -> None:
        self._schedule(self._status_var.set, msg)

    def set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    def _set_input_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._entry.config(state=state)
        self._btn_send.config(state=state)

    def _on_inner_configure(self, event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")