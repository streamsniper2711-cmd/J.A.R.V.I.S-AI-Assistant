# J.A.R.V.I.S. AI Assistant

> **Just A Rather Very Intelligent System**

A modular, futuristic desktop AI assistant inspired by the J.A.R.V.I.S. concept from Iron Man.

J.A.R.V.I.S. combines conversational AI, voice interaction, long-term memory, computer automation, web tools, system monitoring, computer vision, and a customizable futuristic HUD interface into one desktop assistant.

---

## ✨ Features

### 🧠 AI Assistant

* Conversational AI architecture
* Multiple AI provider support
* Context-aware interactions
* Extensible agent and plugin system
* Developer/code assistance
* Proactive assistant capabilities

### 🧠 Long-Term Memory

* Persistent assistant memory
* Conversation persistence
* User preference storage
* Configurable memory management
* SQLite-backed application data
* JSON-based long-term memory

J.A.R.V.I.S. is designed to retain useful information between sessions rather than behaving like a completely stateless chatbot.

### 🎙️ Voice System

* Speech-to-text
* Text-to-speech
* Wake-word architecture
* Voice activity detection
* Interruptible speech
* Voice profiles
* Pronunciation management
* Multiple speech engines/providers

Supported voice architecture includes Fish Audio and Edge TTS, with a provider abstraction that allows additional engines to be added.

### 👁️ Computer Vision

The vision subsystem includes:

* Webcam/camera support
* Object detection
* Face recognition
* Hand tracking
* Gesture recognition
* Frame processing
* Multimodal vision processing
* Vision diagnostics
* Face registration

Vision functionality is designed as a modular subsystem so additional perception capabilities can be added later.

### 🖥️ Desktop Automation

J.A.R.V.I.S. can interact with the Windows desktop through modular actions such as:

* Application launching
* Browser control
* Computer control
* File management
* File processing
* Desktop interaction
* Computer settings
* Screen processing
* System monitoring
* Messaging
* Reminders
* YouTube tools
* Weather information
* Flight searching
* Game-related utilities

### 🌐 Web & Information Tools

* Web searching
* Browser interaction
* Online information retrieval
* YouTube transcript processing
* Web-based utilities

### 🎛️ Futuristic HUD Interface

The interface is designed around a futuristic J.A.R.V.I.S.-style HUD.

Features include:

* Animated Arc Reactor interface
* Transparent compact mode
* Quick Actions interface
* Integrated chat log
* Command input
* Enter-to-send interaction
* Customizable UI elements
* Adjustable size and position
* Opacity controls
* Color customization
* Visibility controls
* Custom buttons, panels, text and separators
* Persistent layout configuration
* Dedicated Settings interface

The UI is built to be highly customizable rather than being locked to a single layout.

### 🔌 Modular Architecture

The project is organized into separate modules for easier development and expansion.

```text
actions/      → Assistant actions and automation
app/          → API/service layer
core/         → AI, voice, audio, plugins and core services
memory/       → Long-term memory and configuration
vision/       → Computer vision subsystem
plugins/      → Extensible plugin system
dashboard/    → Dashboard/service functionality
config/       → Configuration and UI settings
data/         → Persistent application data
assets/       → Fonts, sounds and visual assets
ui.py         → Main desktop interface
main.py       → Main application launcher
```

---

## 🚀 Getting Started

### Requirements

* Windows
* Python 3.10+
* Microphone for voice features
* Webcam for vision features
* Internet connection for online AI/voice services

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/JARVIS-AI-Assistant.git
cd JARVIS-AI-Assistant
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or on Windows:

```bash
install_dependencies.bat
```

### 3. Configure J.A.R.V.I.S.

Configure your API keys and service settings through the project's configuration system.

Keep private credentials out of Git.

**Do not commit real API keys, tokens, passwords, or private certificates to a public repository.**

### 4. Start J.A.R.V.I.S.

```bash
python main.py
```

Alternative Windows launchers are also included:

```text
run_jarvis.bat
run_jarvis.vbs
start_jarvis.py
```

---

## 🎙️ Voice Configuration

Voice configuration can be managed through the Settings interface.

The current architecture supports:

### Fish Audio

Configure:

* API key
* Model ID
* Reference voice ID
* Endpoint
* Output format
* Latency preference

### Edge TTS

Configure:

* Voice name
* Speech rate
* Pitch

The voice architecture is separated from the assistant logic so speech providers can be replaced without rewriting the entire assistant.

---

## 🎨 UI Customization

J.A.R.V.I.S. includes dedicated configuration and layout tools.

### Settings

```bash
python ui_settings.py
```

### Layout Editor

```bash
python ui_layout.py
```

The layout editor is intended to allow customization of:

* Position
* Size
* Opacity
* Color
* Visibility
* Text
* Buttons
* Panels
* Separators
* Custom UI elements

Layout information is saved in:

```text
config/ui_layout.json
```

---

## 🌐 Optional Service Layer

J.A.R.V.I.S. includes an optional FastAPI service layer.

Start it with:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

The service architecture is designed for future expansion including provider integrations, agents, external interfaces and WebSocket communication.

---

## 🧩 Plugin System

Plugins can be added through the `plugins/` directory.

A template is included:

```text
plugins/_template.py
```

The goal is to allow new assistant capabilities to be developed independently without modifying the entire core system.

---

## 📁 Project Structure

```text
JARVIS-AI-Assistant/
│
├── actions/
│   ├── browser_control.py
│   ├── computer_control.py
│   ├── desktop.py
│   ├── file_controller.py
│   ├── web_search.py
│   ├── system_monitor.py
│   ├── screen_processor.py
│   └── ...
│
├── app/
│   ├── api.py
│   ├── main.py
│   └── core/
│
├── assets/
│   ├── fonts/
│   ├── audio/
│   └── UI assets
│
├── config/
│   ├── api_keys.json
│   ├── ui_layout.json
│   └── jarvis.ico
│
├── core/
│   ├── ai_providers.py
│   ├── llm_client.py
│   ├── plugin_loader.py
│   ├── stt.py
│   ├── tts.py
│   ├── voice.py
│   └── ...
│
├── dashboard/
│
├── memory/
│   ├── memory_manager.py
│   ├── config_manager.py
│   └── long_term.json
│
├── plugins/
│
├── vision/
│   ├── camera.py
│   ├── face_recognition.py
│   ├── object_detection.py
│   ├── hand_tracking.py
│   ├── gesture.py
│   ├── multimodal.py
│   └── ...
│
├── data/
│
├── main.py
├── ui.py
├── ui_settings.py
├── ui_layout.py
├── ui_theme.py
├── requirements.txt
└── README.md
```

---

## 🔐 Security

Before publishing this repository publicly, make sure sensitive files are removed or replaced with example configuration.

Never publish:

```text
API keys
Access tokens
Passwords
Private certificates
Private voice credentials
Personal database contents
Private user data
```

Use environment variables or an example configuration file such as:

```text
.env.example
config/api_keys.example.json
```

---

## 🛠️ Development

The project is designed as an evolving experimental AI assistant.

Development priorities include:

* Better long-term memory
* Smarter contextual reasoning
* More reliable wake-word detection
* Improved vision capabilities
* More autonomous actions
* Expanded plugin support
* Better UI customization
* Improved voice interactions
* More intelligent proactive behavior
* Additional AI provider support
* Advanced multimodal capabilities

---

## 🧠 Vision

The long-term goal of this project is to create a highly capable personal desktop AI assistant that combines:

**Memory + Voice + Vision + Automation + AI + Personalization**

into one unified system.

The project is inspired by the fictional J.A.R.V.I.S. concept, while remaining an independent software project.

---

## ⚠️ Disclaimer

This project is a personal/experimental AI assistant inspired by the fictional J.A.R.V.I.S. system from Marvel's Iron Man.

It is **not affiliated with, endorsed by, or officially connected to Marvel, Disney, or any related organization.**

Use automation, computer-control and external API features responsibly.

---

## 📜 License

See the [`LICENSE`](LICENSE) file for the project's license.

---

## ⭐ Support

If this project is useful or interesting to you, consider giving the repository a ⭐ on GitHub.

Contributions, ideas, bug reports and feature requests are welcome.

---

### J.A.R.V.I.S.

**Your desktop. Your AI. Your system.**
