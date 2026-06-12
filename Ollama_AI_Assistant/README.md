# 🤖 Ollama Desktop AI Assistant

A fully offline, privacy-first desktop AI assistant built with Python and Tkinter,
powered by [Ollama](https://ollama.com) local language models.

---

## ✨ Features

- **Multi-turn AI chat** with full session memory
- **Voice input** via microphone (SpeechRecognition)
- **Voice output** via offline TTS (pyttsx3)
- **App launcher** — say "Open Chrome" or "Open Calculator"
- **Dark & light themes**
- **Configurable model** — switch models from Settings
- **Streaming responses** from Ollama
- **Never freezes** — all AI/speech work runs in background threads

---

## 📋 Requirements

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Ollama | Latest |
| Tkinter | Included with Python |

---

## 🚀 Quick Start

### 1 — Install Python

Download Python 3.11 or later from https://www.python.org/downloads/

Verify installation:
```bash
python --version
```

### 2 — Create a virtual environment (recommended)

```bash
# Create
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Linux users** — install PortAudio first:
> ```bash
> sudo apt install portaudio19-dev python3-pyaudio
> ```

> **macOS users** — install PortAudio via Homebrew:
> ```bash
> brew install portaudio
> pip install pyaudio
> ```

### 4 — Install Ollama

Download and install from https://ollama.com

Verify:
```bash
ollama --version
```

Start the Ollama service:
```bash
ollama serve
```

### 5 — Download the AI model

```bash
ollama pull qwen3:8b
```

This downloads the default model (~5 GB).  Feel free to use any model you prefer —
you can change it later in Settings.

To verify the model works:
```bash
ollama run qwen3:8b
# Type a message, then /bye to exit
```

### 6 — Run the application

```bash
python main.py
```

---

## 🗂 Project Structure

```
Ollama_AI_Assistant/
│
├── main.py            # Entry point — startup checks, launches GUI
├── gui.py             # Tkinter main window, chat bubbles, toolbar
├── ai_engine.py       # Ollama API client, conversation history
├── speech_input.py    # Microphone → speech-to-text
├── speech_output.py   # Text-to-speech (pyttsx3, background thread)
├── app_launcher.py    # Cross-platform application launcher
├── settings.py        # Settings Toplevel dialog
├── config_manager.py  # JSON config load/save/validate
│
├── config.json        # Persistent user preferences
├── requirements.txt   # Python dependencies
├── README.md          # This file
│
├── assets/
│   ├── app_icon.ico   # (optional) Window icon
│   └── ...
│
└── logs/
    └── assistant.log  # Runtime log (errors, info)
```

---

## ⚙ Configuration

`config.json` is created automatically on first run. You can edit it directly
or use the in-app Settings dialog (⚙ button).

| Key | Default | Description |
|---|---|---|
| `model` | `qwen3:8b` | Ollama model name |
| `voice_enabled` | `true` | Enable TTS voice output |
| `theme` | `dark` | `dark` or `light` |
| `ollama_host` | `http://localhost:11434` | Ollama API base URL |
| `speech_rate` | `175` | Words per minute for TTS |
| `speech_volume` | `1.0` | TTS volume (0.0 – 1.0) |

---

## 🗣 App Launcher Commands

Say or type any of these to open applications:

```
Open Chrome
Open Firefox
Open Edge
Open Notepad
Open Calculator
Open VS Code
Open Visual Studio Code
Open Spotify
Open Discord
Open Steam
Open File Explorer
Open Terminal
```

---

## 🐞 Troubleshooting

### "Cannot connect to Ollama"
Make sure the Ollama service is running:
```bash
ollama serve
```

### "Model not found"
Pull the model:
```bash
ollama pull qwen3:8b
```
Or change the model in Settings to one you have installed.

### Voice input not working
Install PyAudio:
```bash
# Windows
pip install pyaudio

# macOS
brew install portaudio && pip install pyaudio

# Linux
sudo apt install portaudio19-dev && pip install pyaudio
```

### Voice output not working
```bash
pip install pyttsx3
```
On Linux you may also need:
```bash
sudo apt install espeak ffmpeg libespeak1
```

### Application starts but chat fails
Check `logs/assistant.log` for detailed error messages.

---

## 🔄 Changing the AI Model

1. Pull any model from Ollama:
   ```bash
   ollama pull llama3.2
   ollama pull mistral
   ollama pull gemma2:9b
   ```
2. Open Settings (⚙ button) and type the model name, then click Save.

---

## 🏗 Extending the Project

The codebase uses clean separation of concerns:

- **New AI providers** → subclass or replace `AIEngine`
- **New voice engines** → replace `SpeechOutput`
- **New app commands** → add entries to the dicts in `app_launcher.py`
- **New settings** → add to `DEFAULT_CONFIG` in `config_manager.py` and add a widget in `settings.py`

---

## 📄 License

MIT — free for personal and commercial use.
