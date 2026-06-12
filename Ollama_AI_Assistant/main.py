"""
main.py
-------
Application entry point for the Ollama Desktop AI Assistant.

Responsibilities:
  - Initialise logging.
  - Load configuration.
  - Run Ollama availability checks.
  - Instantiate all subsystems (AI engine, speech, launcher).
  - Launch the Tkinter GUI and enter the main loop.
  - Support wake word detection ("Hey Bro") for hands-free operation.
"""

import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox
import threading
import time

# ---------------------------------------------------------------------------
# Bootstrap: ensure logs/ directory exists before logging init
# ---------------------------------------------------------------------------
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR  = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE  = os.path.join(LOGS_DIR, "assistant.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Local modules
# ---------------------------------------------------------------------------
from config_manager import ConfigManager
from ai_engine      import AIEngine
from speech_input   import SpeechInput
from speech_output  import SpeechOutput
from app_launcher   import AppLauncher
from gui            import MainWindow


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------

def check_ollama(ai: AIEngine, cfg: ConfigManager) -> list[str]:
    """
    Run pre-flight checks.  Returns a list of warning strings
    (empty if everything is fine).
    """
    warnings: list[str] = []

    if not ai.is_ollama_running():
        warnings.append(
            "⚠  Ollama service is not running.\n"
            "   Start it with:  ollama serve\n"
            "   Then restart this application."
        )
        return warnings   # no point checking model if service is down

    models = ai.list_models()
    configured_model = cfg.get("model")
    if not any(configured_model in m for m in models):
        warnings.append(
            f"⚠  Model '{configured_model}' not found locally.\n"
            f"   Pull it with:  ollama pull {configured_model}\n"
            f"   Available: {', '.join(models) or 'none'}"
        )

    return warnings


def show_startup_warnings(warnings: list[str]) -> None:
    """Display each warning as a non-fatal messagebox."""
    for w in warnings:
        logger.warning(w)
    if warnings:
        messagebox.showwarning(
            "Ollama AI Assistant — Startup Warning",
            "\n\n".join(warnings),
        )


# ---------------------------------------------------------------------------
# Jarvis-style Assistant Class
# ---------------------------------------------------------------------------

class OllamaAssistant:
    """
    Manages the assistant with wake word detection and voice/text modes.
    """
    
    def __init__(self, cfg, ai, speech_i, speech_o, launcher, gui_app):
        self.cfg = cfg
        self.ai = ai
        self.speech_input = speech_i
        self.speech_output = speech_o
        self.launcher = launcher
        self.gui = gui_app
        
        self.wake_word_enabled = self.cfg.get("wake_word_enabled", True)
        self.wake_word = self.cfg.get("wake_word", "hey bro")
        self.idle_timeout = self.cfg.get("idle_timeout", 30)  # seconds before resetting
        
        self.last_activity_time = time.time()
        self.is_in_conversation = False
        self.conversation_timeout = 60  # seconds before ending conversation mode
        
        # Start wake word listener if enabled
        if self.wake_word_enabled and self.speech_input.available:
            self._start_wake_word_listener()
    
    def _start_wake_word_listener(self):
        """Start the background wake word detection thread."""
        def on_wake_word_command(command_text):
            """Called when wake word is detected and command is captured."""
            logger.info(f"🎯 Wake word command received: {command_text}")
            
            # Update activity timestamp
            self.update_activity()
            
            # Set conversation mode in GUI
            self.gui.set_conversation_mode(True, self.wake_word)
            
            # Use the GUI's wake word handler (which will process the command)
            self.gui.on_wake_word_command(command_text)
        
        def on_wake_word_error(error_msg):
            """Handle wake word errors."""
            logger.warning(f"Wake word error: {error_msg}")
            self.gui.on_wake_word_error(error_msg)
        
        # Start listening for wake word
        self.speech_input.start_wake_word_listening(
            command_callback=on_wake_word_command,
            wake_word=self.wake_word,
            error_callback=on_wake_word_error
        )
        
        # Update GUI status
        self.gui.set_conversation_mode(False, self.wake_word)
        
        # Start idle monitor
        self._start_idle_monitor()
    
    def _start_idle_monitor(self):
        """Monitor for idle time and reset conversation state."""
        def monitor():
            while True:
                time.sleep(5)
                current_time = time.time()
                
                # If in conversation mode but idle for too long, exit
                if self.is_in_conversation:
                    if current_time - self.last_activity_time > self.conversation_timeout:
                        self.is_in_conversation = False
                        logger.info("Conversation mode ended due to inactivity")
                        self.gui.set_conversation_mode(False, self.wake_word)
                        # Optional: play a subtle chime or just update status
                        if self.speech_output.enabled:
                            self.speech_output.speak("I'm still here. Say my name when you need me.")
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def update_activity(self):
        """Update last activity timestamp (called when user interacts)."""
        self.last_activity_time = time.time()
        self.is_in_conversation = True
        
        # Update GUI status to show we're in conversation mode
        self.gui.set_conversation_mode(True, self.wake_word)
    
    def stop(self):
        """Stop wake word listener and clean up."""
        if self.wake_word_enabled and hasattr(self.speech_input, 'stop_wake_word_listening'):
            self.speech_input.stop_wake_word_listening()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("Ollama AI Assistant starting up…")
    logger.info("=" * 60)

    # --- Configuration ---
    cfg = ConfigManager()
    logger.info("Config loaded: model=%s  theme=%s", cfg.get("model"), cfg.get("theme"))

    # --- Subsystems ---
    ai       = AIEngine(cfg)
    speech_i = SpeechInput()
    speech_o = SpeechOutput(cfg)
    launcher = AppLauncher()

    # --- Apply female voice and flirty mode from config ---
    voice_gender = cfg.get("voice_gender", "female")
    flirty_mode = cfg.get("flirty_mode", False)
    
    if speech_o.available:
        # Set voice gender after a short delay to ensure engine is ready
        def apply_voice_settings():
            try:
                speech_o.set_voice_gender(voice_gender)
                if flirty_mode:
                    speech_o.set_flirty_mode(True)
                    logger.info("💋 Flirty mode enabled - Assistant is ready to flirt!")
            except Exception as e:
                logger.warning(f"Could not apply voice settings: {e}")
        
        threading.Timer(1.0, apply_voice_settings).start()

    # --- Tkinter root (needed before messagebox calls) ---
    root = tk.Tk()
    root.withdraw()   # hide until fully built

    # --- Ollama checks ---
    warnings = check_ollama(ai, cfg)
    show_startup_warnings(warnings)

    # --- Build GUI ---
    app = MainWindow(
        root       = root,
        config_manager = cfg,
        ai_engine  = ai,
        speech_input  = speech_i,
        speech_output = speech_o,
        app_launcher  = launcher,
    )

    if warnings:
        app.set_status("⚠ Ollama issue detected — see warning dialog.")
    else:
        app.set_status(f"Connected to Ollama  ·  Model: {cfg.get('model')}")

    # --- Initialize Jarvis-style assistant ---
    assistant = OllamaAssistant(cfg, ai, speech_i, speech_o, launcher, app)
    
    # Store assistant reference in GUI for activity updates
    app.assistant = assistant

    root.deiconify()   # show the window
    logger.info("GUI launched.  Entering mainloop.")
    
    # Play startup greeting if voice is enabled
    if speech_o.enabled and cfg.get("voice_gender", "female") == "female":
        greeting = "Hello there! I'm your AI assistant. Just say Hey Bro to get my attention."
        threading.Timer(1.5, lambda: speech_o.speak(greeting)).start()

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down.")
    finally:
        assistant.stop()
        speech_o.stop()
        speech_i.stop()
        logger.info("Application exited cleanly.")


if __name__ == "__main__":
    main()