"""
app_launcher.py
---------------
Detects the host operating system and opens installed applications by name.
Supports Windows, macOS, and Linux.
"""

import logging
import platform
import subprocess
import shutil
import re
from typing import Optional

logger = logging.getLogger(__name__)

OS = platform.system().lower()

WINDOWS_APPS = {
    "chrome":             ["start chrome"],
    "google chrome":      ["start chrome"],
    "edge":               ["start msedge"],
    "microsoft edge":     ["start msedge"],
    "firefox":            ["start firefox"],
    "notepad":            ["start notepad"],
    "calculator":         ["start calc"],
    "calc":               ["start calc"],
    "vscode":             ["code"],
    "vs code":            ["code"],
    "visual studio code": ["code"],
    "spotify":            ["start spotify"],
    "discord":            ["start discord"],
    "steam":              ["start steam"],
    "file explorer":      ["start explorer"],
    "explorer":           ["start explorer"],
    "files":              ["start explorer"],
    "paint":              ["start mspaint"],
    "word":               ["start winword"],
    "excel":              ["start excel"],
    "powershell":         ["start powershell"],
    "cmd":                ["start cmd"],
    "terminal":           ["start cmd"],
    "task manager":       ["taskmgr"],
    "control panel":      ["control"],
}

MACOS_APPS = {
    "chrome":               ["open -a 'Google Chrome'"],
    "google chrome":        ["open -a 'Google Chrome'"],
    "edge":                 ["open -a 'Microsoft Edge'"],
    "microsoft edge":       ["open -a 'Microsoft Edge'"],
    "firefox":              ["open -a Firefox"],
    "safari":               ["open -a Safari"],
    "notepad":              ["open -a TextEdit"],
    "textedit":             ["open -a TextEdit"],
    "calculator":           ["open -a Calculator"],
    "vscode":               ["open -a 'Visual Studio Code'", "code"],
    "vs code":              ["open -a 'Visual Studio Code'", "code"],
    "visual studio code":   ["open -a 'Visual Studio Code'", "code"],
    "spotify":              ["open -a Spotify"],
    "discord":              ["open -a Discord"],
    "steam":                ["open -a Steam"],
    "file explorer":        ["open ~"],
    "finder":               ["open ~"],
    "files":                ["open ~"],
    "terminal":             ["open -a Terminal"],
    "activity monitor":     ["open -a 'Activity Monitor'"],
}

LINUX_APPS = {
    "chrome":               ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
    "google chrome":        ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
    "edge":                 ["microsoft-edge", "microsoft-edge-stable"],
    "firefox":              ["firefox"],
    "notepad":              ["gedit", "kate", "mousepad", "xed"],
    "calculator":           ["gnome-calculator", "kcalc", "xcalc"],
    "vscode":               ["code"],
    "vs code":              ["code"],
    "visual studio code":   ["code"],
    "spotify":              ["spotify"],
    "discord":              ["discord"],
    "steam":                ["steam"],
    "file explorer":        ["nautilus", "dolphin", "thunar", "nemo", "pcmanfm"],
    "files":                ["nautilus", "dolphin", "thunar", "nemo", "pcmanfm"],
    "terminal":             ["gnome-terminal", "konsole", "xterm", "xfce4-terminal"],
    "text editor":          ["gedit", "kate", "mousepad"],
    "vlc":                  ["vlc"],
    "gimp":                 ["gimp"],
}


class AppLauncher:
    """Opens named applications on Windows, macOS, and Linux."""

    def open(self, app_name: str) -> dict:
        """
        Attempt to open *app_name*.
        Returns: {"success": bool, "message": str}
        """
        key = app_name.strip().lower()
        logger.info("Attempting to open app: %r (OS=%s)", key, OS)

        try:
            if OS == "windows":
                return self._launch_windows(key)
            elif OS == "darwin":
                return self._launch_macos(key)
            else:
                return self._launch_linux(key)
        except Exception as exc:
            msg = f"Unexpected error launching '{app_name}': {exc}"
            logger.exception(msg)
            return {"success": False, "message": msg}

    def detect_open_intent(self, user_text: str) -> Optional[str]:
        """
        Scan *user_text* for open/launch/start + <app name> patterns.
        Returns the app name string if found, else None.
        """
        text = user_text.lower().strip()
        for trigger in ["open ", "launch ", "start ", "run "]:
            if text.startswith(trigger):
                return text[len(trigger):].strip()

        match = re.search(r"\b(?:open|launch|start|run)\s+([a-z0-9 _\-\.]+)", text)
        if match:
            return match.group(1).strip()
        return None

    def _launch_windows(self, key: str) -> dict:
        candidates = WINDOWS_APPS.get(key)
        if not candidates:
            return self._not_found(key)

        for cmd in candidates:
            try:
                subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Launched (Windows): %r", cmd)
                return {"success": True, "message": f"Opening {key.title()}..."}
            except Exception as exc:
                logger.debug("Command %r failed: %s", cmd, exc)

        return {"success": False, "message": f"Could not open '{key}'."}

    def _launch_macos(self, key: str) -> dict:
        candidates = MACOS_APPS.get(key)
        if not candidates:
            return self._not_found(key)

        for cmd in candidates:
            try:
                subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Launched (macOS): %r", cmd)
                return {"success": True, "message": f"Opening {key.title()}..."}
            except Exception as exc:
                logger.debug("Command %r failed: %s", cmd, exc)

        return {"success": False, "message": f"Could not open '{key}'."}

    def _launch_linux(self, key: str) -> dict:
        candidates = LINUX_APPS.get(key)
        if not candidates:
            return self._not_found(key)

        for cmd in candidates:
            binary = cmd.split()[0]
            if shutil.which(binary):
                try:
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    logger.info("Launched (Linux): %r", cmd)
                    return {"success": True, "message": f"Opening {key.title()}..."}
                except Exception as exc:
                    logger.debug("Command %r failed: %s", cmd, exc)

        return {"success": False, "message": f"Could not find '{key}' on this system."}

    def _not_found(self, key: str) -> dict:
        msg = f"'{key}' is not in the supported application list."
        logger.warning(msg)
        return {"success": False, "message": msg}