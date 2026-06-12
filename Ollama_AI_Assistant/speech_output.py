"""
speech_output.py
----------------
Fixed version - creates a fresh engine for each utterance to avoid
runAndWait() hanging after the first call.
"""

import logging
import queue
import threading
import random
import subprocess

logger = logging.getLogger(__name__)

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logger.warning("pyttsx3 not installed. Voice output disabled.")


class SpeechOutput:

    def __init__(self, config_manager):
        self.cfg = config_manager
        self._enabled: bool = self.cfg.get("voice_enabled", True)
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._flirty_mode: bool = self.cfg.get("flirty_mode", False)
        self._voice_gender: str = self.cfg.get("voice_gender", "female")
        self._female_voice_id = None
        self._male_voice_id = None

        if PYTTSX3_AVAILABLE:
            self._discover_voices()
            self._start_worker()

    @property
    def available(self) -> bool:
        return PYTTSX3_AVAILABLE

    @property
    def enabled(self) -> bool:
        return self._enabled and self.available

    def set_enabled(self, value: bool) -> None:
        self._enabled = value
        self.cfg.set("voice_enabled", value)
        if not value:
            self.stop()

    def set_voice_gender(self, gender: str) -> None:
        self._voice_gender = gender
        self.cfg.set("voice_gender", gender)

    def set_flirty_mode(self, enabled: bool) -> None:
        self._flirty_mode = enabled
        self.cfg.set("flirty_mode", enabled)

    def speak(self, text: str) -> None:
        if not self.enabled:
            return
        if not text.strip():
            return
        logger.info("Queued for speech: %s", text[:80])
        self._stop_event.clear()
        self._queue.put(text)

    def speak_flirty(self, text: str) -> None:
        self.speak(text)

    def stop(self) -> None:
        self._stop_event.set()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def flirt_response(self, compliment_type: str = "generic") -> str:
        responses = {
            "generic": [
                "Oh, you're making me blush!",
                "Stop it, you're too sweet!",
                "You know how to make a girl smile.",
            ],
            "smart": ["I love how your mind works.", "That's why I enjoy talking to you."],
            "beautiful": ["You're not so bad yourself!", "Oh stop, you're going to give me an ego!"],
            "funny": ["You always know how to make me laugh.", "I like your style!"],
        }
        return random.choice(responses.get(compliment_type, responses["generic"]))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _discover_voices(self) -> None:
        """Run once at startup to find and cache voice IDs."""
        try:
            engine = pyttsx3.init(driverName='sapi5')
            voices = engine.getProperty('voices')

            logger.info("Available voices:")
            for i, v in enumerate(voices):
                logger.info("  [%d] %s | %s", i, v.name, v.id)

            # Find female voice - priority: Zira > 'female' keyword > index 1
            for v in voices:
                if 'zira' in v.name.lower():
                    self._female_voice_id = v.id
                    logger.info("Female voice selected (Zira): %s", v.name)
                    break
            if not self._female_voice_id:
                for v in voices:
                    if 'female' in v.name.lower():
                        self._female_voice_id = v.id
                        logger.info("Female voice selected: %s", v.name)
                        break
            if not self._female_voice_id and len(voices) > 1:
                self._female_voice_id = voices[1].id
                logger.info("Female fallback (index 1): %s", voices[1].name)

            # Find male voice - priority: David > index 0
            for v in voices:
                if 'david' in v.name.lower():
                    self._male_voice_id = v.id
                    break
            if not self._male_voice_id and voices:
                self._male_voice_id = voices[0].id

            engine.stop()
            del engine

        except Exception as exc:
            logger.error("Voice discovery failed: %s", exc)

    def _get_voice_id(self):
        if self._voice_gender.lower() == "female" and self._female_voice_id:
            return self._female_voice_id
        return self._male_voice_id

    def _start_worker(self) -> None:
        t = threading.Thread(
            target=self._run_worker, daemon=True, name="SpeechOutput-worker"
        )
        t.start()

    def _run_worker(self) -> None:
        while True:
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                continue

            self._speak_now(text)

    def _speak_now(self, text: str) -> None:
        """
        Create a FRESH engine per utterance.
        This is the only reliable fix for pyttsx3 going silent after first call.
        """
        try:
            engine = pyttsx3.init(driverName='sapi5')

            voice_id = self._get_voice_id()
            if voice_id:
                engine.setProperty('voice', voice_id)

            if self._flirty_mode:
                engine.setProperty('rate', 145)
                engine.setProperty('volume', 0.95)
            else:
                engine.setProperty('rate', self.cfg.get("speech_rate", 150))
                engine.setProperty('volume', self.cfg.get("speech_volume", 0.95))

            engine.say(text)
            engine.runAndWait()
            engine.stop()
            del engine
            logger.debug("Speech done.")

        except Exception as exc:
            logger.error("pyttsx3 error: %s — trying PowerShell fallback.", exc)
            # Fallback: use Windows PowerShell speech synthesis directly
            try:
                voice_name = (
                    "Microsoft Zira Desktop"
                    if self._voice_gender == "female"
                    else "Microsoft David Desktop"
                )
                safe_text = text.replace("'", "").replace('"', "")
                ps_cmd = (
                    f"Add-Type -AssemblyName System.Speech; "
                    f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    f"$s.SelectVoice('{voice_name}'); "
                    f"$s.Rate = -1; "
                    f"$s.Speak('{safe_text}');"
                )
                subprocess.Popen(
                    ["powershell", "-Command", ps_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("PowerShell TTS fallback used.")
            except Exception as exc2:
                logger.error("PowerShell fallback failed: %s", exc2)