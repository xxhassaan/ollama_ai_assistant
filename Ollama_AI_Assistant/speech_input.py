"""
speech_input.py
---------------
Handles microphone input and speech-to-text conversion using the
SpeechRecognition library.  Provides both one-shot and background-listening
modes. Now includes wake word detection ("Hey Bro") for hands-free operation.
"""

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# SpeechRecognition is optional – handle gracefully if missing.
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("SpeechRecognition not installed. Voice input disabled.")


class SpeechInput:
    """
    Wraps SpeechRecognition for clean GUI integration.

    Usage:
        si = SpeechInput()
        si.listen_once(callback=lambda text: print(text))
        si.start_wake_word_listening(wake_word="hey bro", command_callback=my_function)
    """

    def __init__(self):
        self._recognizer: Optional[object] = None
        self._bg_stop = None          # handle for background listener
        self._listening = False
        self._wake_word_listening = False
        self._wake_word_thread: Optional[threading.Thread] = None
        self._wake_word_callback: Optional[Callable] = None
        self._wake_word = "hey bro"
        self._lock = threading.Lock()

        if SR_AVAILABLE:
            self._recognizer = sr.Recognizer()
            # Tune for typical desktop environments
            self._recognizer.pause_threshold = 0.8
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return SR_AVAILABLE and self._recognizer is not None

    @property
    def is_listening(self) -> bool:
        return self._listening

    @property
    def is_wake_word_listening(self) -> bool:
        return self._wake_word_listening

    def listen_once(
        self,
        callback: Callable[[str], None],
        error_callback: Optional[Callable[[str], None]] = None,
        timeout: int = 5,
        phrase_limit: int = 15,
    ) -> None:
        """
        Listen for a single utterance in a background thread.

        :param callback:       Called with the recognised text on success.
        :param error_callback: Called with an error string on failure.
        :param timeout:        Seconds to wait for speech to start.
        :param phrase_limit:   Max seconds for a single phrase.
        """
        if not self.available:
            msg = "Speech recognition is not available (library missing)."
            logger.error(msg)
            if error_callback:
                error_callback(msg)
            return

        if self._listening:
            logger.debug("Already listening – ignoring duplicate request.")
            return

        thread = threading.Thread(
            target=self._listen_worker,
            args=(callback, error_callback, timeout, phrase_limit),
            daemon=True,
            name="SpeechInput-once",
        )
        thread.start()

    def start_wake_word_listening(
        self,
        command_callback: Callable[[str], None],
        wake_word: str = "hey bro",
        error_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Start continuous listening for a wake word, then capture the command.
        
        :param command_callback: Called with the command text after wake word detected
        :param wake_word: The wake word/phrase to listen for (default: "hey bro")
        :param error_callback: Called with error message if something fails
        """
        if not self.available:
            msg = "Speech recognition is not available (library missing)."
            logger.error(msg)
            if error_callback:
                error_callback(msg)
            return

        if self._wake_word_listening:
            logger.warning("Wake word listening already active")
            return

        self._wake_word = wake_word.lower()
        self._wake_word_callback = command_callback
        self._wake_word_listening = True
        
        self._wake_word_thread = threading.Thread(
            target=self._wake_word_worker,
            args=(error_callback,),
            daemon=True,
            name="SpeechInput-wakeword",
        )
        self._wake_word_thread.start()
        logger.info("🎤 Wake word listening started. Say '%s' to activate.", wake_word)

    def stop_wake_word_listening(self) -> None:
        """Stop continuous wake word listening."""
        self._wake_word_listening = False
        if self._wake_word_thread:
            self._wake_word_thread.join(timeout=1.0)
            self._wake_word_thread = None
        logger.info("Wake word listening stopped.")

    def stop(self) -> None:
        """Stop any active background listening session."""
        if self._bg_stop:
            try:
                self._bg_stop(wait_for_stop=False)
            except Exception:  # pylint: disable=broad-except
                pass
            self._bg_stop = None
        with self._lock:
            self._listening = False
        
        # Also stop wake word listening
        self.stop_wake_word_listening()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _listen_worker(
        self,
        callback: Callable[[str], None],
        error_callback: Optional[Callable[[str], None]],
        timeout: int,
        phrase_limit: int,
    ) -> None:
        """Blocking worker that runs in a dedicated thread."""
        with self._lock:
            self._listening = True

        try:
            with sr.Microphone() as source:
                logger.info("Adjusting for ambient noise…")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Listening for speech…")
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )

            logger.info("Recognising speech with Google API…")
            text = self._recognizer.recognize_google(audio)
            logger.info("Recognised: %r", text)
            callback(text)

        except sr.WaitTimeoutError:
            msg = "No speech detected within the timeout period."
            logger.warning(msg)
            if error_callback:
                error_callback(msg)

        except sr.UnknownValueError:
            msg = "Could not understand the audio. Please try again."
            logger.warning(msg)
            if error_callback:
                error_callback(msg)

        except sr.RequestError as exc:
            msg = f"Speech recognition service error: {exc}"
            logger.error(msg)
            if error_callback:
                error_callback(msg)

        except OSError as exc:
            msg = f"Microphone error: {exc}"
            logger.error(msg)
            if error_callback:
                error_callback(msg)

        except Exception as exc:  # pylint: disable=broad-except
            msg = f"Unexpected speech input error: {exc}"
            logger.exception(msg)
            if error_callback:
                error_callback(msg)

        finally:
            with self._lock:
                self._listening = False

    def _wake_word_worker(
        self,
        error_callback: Optional[Callable[[str], None]],
    ) -> None:
        """
        Continuous worker that listens for wake word, then captures command.
        """
        with sr.Microphone() as source:
            logger.info("Calibrating microphone for wake word detection...")
            self._recognizer.adjust_for_ambient_noise(source, duration=1.0)
            logger.info("✅ Wake word detection active. Say '%s'", self._wake_word)
            
            while self._wake_word_listening:
                try:
                    # Listen for potential wake word (short timeout for responsiveness)
                    audio = self._recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                    # Transcribe what was said
                    text = self._recognizer.recognize_google(audio).lower()
                    
                    if text and self._wake_word in text:
                        logger.info("🎯 Wake word '%s' detected!", self._wake_word)
                        
                        # Now listen for the actual command
                        try:
                            logger.info("🎤 Listening for command...")
                            command_audio = self._recognizer.listen(
                                source, timeout=5, phrase_time_limit=10
                            )
                            command_text = self._recognizer.recognize_google(command_audio)
                            logger.info("📝 Command received: %r", command_text)
                            
                            if self._wake_word_callback:
                                self._wake_word_callback(command_text)
                                
                        except sr.WaitTimeoutError:
                            logger.warning("No command detected after wake word")
                            if error_callback:
                                error_callback("No command heard after wake word")
                        except sr.UnknownValueError:
                            logger.warning("Could not understand command")
                            if error_callback:
                                error_callback("Could not understand the command")
                                
                except sr.WaitTimeoutError:
                    # No speech detected, continue listening
                    continue
                except sr.UnknownValueError:
                    # Speech detected but not recognized, continue
                    continue
                except sr.RequestError as exc:
                    logger.error("Recognition service error: %s", exc)
                    if error_callback:
                        error_callback(f"Service error: {exc}")
                    # Brief pause before retrying
                    threading.Event().wait(1.0)
                except Exception as exc:
                    logger.error("Unexpected error in wake word worker: %s", exc)
                    if error_callback:
                        error_callback(f"Error: {exc}")
                    threading.Event().wait(1.0)