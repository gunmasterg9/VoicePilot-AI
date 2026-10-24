# NEO AI — 100% Offline Windows AI PC Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)
[![UI PySide6](https://img.shields.io/badge/UI-PySide6%20Qt6-41CD52.svg)](https://pypi.org/project/PySide6/)
[![Voice Faster--Whisper](https://img.shields.io/badge/ASR-Faster--Whisper%20(Offline)-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![TTS SAPI5 Offline](https://img.shields.io/badge/TTS-SAPI5%20(100%25%20Offline)-purple.svg)](https://pypi.org/project/pyttsx3/)
[![Ollama Local](https://img.shields.io/badge/LLM-Local%20Ollama-black.svg)](https://ollama.com)

**NEO AI** is a polished, fast, reliable, and **100% offline Windows desktop AI assistant**. Built with Python 3.12 and PySide6 Qt6, NEO unifies local quantized speech recognition (Faster-Whisper), zero-latency deterministic command routing, offline SAPI5 text-to-speech, safe Windows PC automation, and local Ollama conversational AI.

Supported PC commands execute through deterministic local handlers **without contacting Ollama**, guaranteeing zero network latency and uninterrupted PC control even if Ollama is stopped.

> **Original Creator & Attribution**: Created by **Gautam Vandar**. Upgraded to the complete offline NEO AI architecture while preserving historical attribution and module backward compatibility.

---

## 🏛 Core Architectural Systems

```
Microphone  ──>  Faster-Whisper (int8 CPU)  ──>  Command Router
                                                       │
                      ┌────────────────────────────────┴───────────────────────────────┐
                      ▼                                                                ▼
             [Known PC Command]                                            [Conversational / Chat]
                      │                                                                │
             Safe Action Registry                                                 Local Ollama
                      │                                                        (127.0.0.1:11434)
         ┌────────────┴─────────────┐                                                  │
         ▼                          ▼                                                  ▼
Local OS Handlers           Windows Security                                       UI Response
(Subprocess, PyAutoGUI)    (Confirmations/Roots)                                       │
         │                          │                                                  │
         └──────────────────────────┴─────────────────┬────────────────────────────────┘
                                                      ▼
                                       PySide6 Modern UI & CoreOrb
                                                      │
                                                      ▼
                                      Offline SAPI5 TTS (pyttsx3)
```

---

## 🚀 Key Features

### 1. Modern Desktop UI/UX (`ui/window.py`)
- **Clean Dark Theme**: High-contrast, accessibility-tested cyberpunk/slate aesthetic (`#0c0f17`, `#54e7a6`, `#38bdf8`, `#ef4444`).
- **Real-Time 6-State Visual Orb**: Real-time lifecycle tracking with specialized animation speeds and colors:
  `IDLE` (Ready) → `LISTENING` → `TRANSCRIBING` → `ROUTING` → `EXECUTING` / `THINKING` → `SPEAKING` → `IDLE`.
- **Top Header Bar**: Application branding, online-independent `● 100% OFFLINE` indicator, and live system state.
- **Compact 5-View Navigation**:
  - `🏠 HOME`: Animated orb, 9-button Quick Actions, real-time hardware telemetry, chat transcript, text/voice controls.
  - `🎙 VOICE`: Microphone selection & calibration, Whisper model choice (`tiny.en`, `base`), language configuration (`en`, `hi`), and SAPI5 TTS controls.
  - `📋 ACTIVITY`: Live auditable table logging timestamp, type, request, status, and execution details.
  - `⚙ SETTINGS`: Ollama host & model configuration, safety confirmation toggles, and live subsystem diagnostic runner.
  - `ℹ ABOUT`: System specifications, offline architectural breakdown, and creator attribution.
- **Instant Quick Actions Panel**: 1-click execution for Notepad, Calculator, Screenshots, Volume Up/Down/Mute, Recycle Bin, Windows Search, and Hardware Telemetry.
- **Non-Blocking Background Workers**: `AgentWorker`, `VoiceWorker`, and `TtsWorker` execute on background `QThread` instances to eliminate UI freezing.

### 2. Smart Voice Command Engine (`core/router.py`)
- **Deterministic 0ms Local Routing**: Known PC actions bypass the LLM completely, executing via local Python handlers without invoking Ollama.
- **Intent Classifier (`CommandRouter`)**: Categorizes requests into `PC_COMMAND`, `SYSTEM_CONTROL`, `DESTRUCTIVE_ACTION`, `CONVERSATIONAL`, `AMBIGUOUS`, or `EMPTY`.
- **Bilingual English & Hindi Phrasing**:
  - **Volume**: "Increase volume", "Volume down", "Mute volume", "आवाज़ बढ़ाओ", "वॉल्यूम कम करो", "आवाज बंद करो".
  - **Applications**: "Open Notepad", "Open Calculator", "नोटपैड खोलो", "कैलकुलेटर खोलो".
  - **Screenshots**: "Take a screenshot", "Capture screen", "स्क्रीनशॉट लो".
  - **System Control**: "Stop", "Cancel", "Halt", "Silence", "रुक जाओ", "बंद करो", "शांत रहो".
  - **Time & Date**: "What time is it", "Today's date", "समय क्या हुआ है", "आज क्या तारीख है".

### 3. Fast Offline Voice Pipeline (`interfaces/voice.py` & `interfaces/tts.py`)
- **Faster-Whisper Local ASR**: Quantized CPU int8 Whisper models with reusable instance caching and zero cloud calls.
- **Windows SAPI5 Offline TTS**: High-speed, natural offline speech via `pyttsx3` with master voice enable/disable toggle (`tts_enabled`), speech rate, and volume controls.
- **Instant Speech Interruption**: `⏹ STOP` halts speech playback and cancels in-flight workers immediately.

### 4. Safe PC Automation (`tools/registry.py` & `core/safety.py`)
- **System Root Guard**: Strict allowlists block destructive file actions against `C:\`, `C:\Windows`, `C:\Program Files`, and system roots.
- **Confirmation Prompts**: Destructive operations (`delete_path`, `shutdown_pc`, `restart_pc`) require user confirmation.
- **Auditable Tool Registry**: Structured `ToolSpec` registry with validated JSON parameter schemas and strict risk classifications (`READ_ONLY`, `REVERSIBLE`, `DESTRUCTIVE`).

### 5. Local Ollama Chat (`core/llm.py`)
- **Conversational Only**: General knowledge, coding questions, and open-ended conversation route strictly to local Ollama.
- **Resilient Fallback**: If Ollama is offline or uninstalled, local PC commands, volume controls, app launchers, file searches, and telemetry remain 100% operational.

---

## 💻 Installation & Setup

### Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Python 3.10, 3.11, or 3.12 (Python 3.12 recommended)
- **Ollama**: (Optional, for conversational AI chat) [Download Ollama for Windows](https://ollama.com/download)

### 1. Clone & Set Up Virtual Environment
```powershell
cd "VoicePilot AI"

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Optional: Pull Local Ollama Model
```powershell
ollama pull qwen3:1.7b
```

---

## 🚀 Launching NEO AI

### Option A: Desktop Double-Click
Double-click `launch_neo.bat`.

### Option B: Terminal Command
```powershell
# Launch PySide6 Desktop GUI (Recommended)
python main.py --mode ui

# Launch Terminal CLI Mode
python main.py --mode terminal

# Launch REST/HTTP API Server
python main.py --mode api
```

---

## 🧪 Automated Testing & Verification

Run the complete test suite (113 tests) anytime to verify 100% system stability:

```powershell
# Run the entire test suite across all 10 modules (113 tests)
pytest

# Run the Phase 9 Comprehensive Offline Assistant Test Suite (16 tests)
pytest tests/test_phase6_offline_assistant.py

# Run Command Routing & Direct Execution Tests (19 tests)
pytest tests/test_command_routing.py

# Run Core AI Brain & Automation Tests (11 tests, 33 command variations)
pytest tests/test_phase3_brain.py
```

### Test Coverage Highlights (113 / 113 Passed)
1. UI startup and navigation when Ollama is unavailable.
2. Direct local command execution with 0ms Ollama latency.
3. Allowlisted app launching (Notepad, Calculator) via mocked handlers.
4. Volume (up/down/mute) and screenshot controls.
5. Conversational questions routed to local Ollama.
6. Local commands working while Ollama is completely stopped.
7. Safe handling of unknown and ambiguous commands.
8. Confirmation requirements for destructive operations.
9. Stop/cancel behavior and instant speech interruption.
10. Duplicate-execution prevention within 2-second windows.
11. Recognition error handling and empty audio protection.
12. Offline SAPI5 TTS error handling and `tts_enabled` toggling.
13. Settings validation, schema constraints, and persistence.
14. Non-blocking UI execution on background worker threads.
15. Safe cleanup of audio streams and worker threads during window closing.

---

## 🔒 Privacy & Offline Guarantee

- **No Remote Telemetry**: Zero external tracking, analytics, or metrics servers.
- **No Cloud Voice Services**: Zero cloud speech recognition or cloud TTS APIs.
- **Local Loopback Only**: The only network interface used is `http://127.0.0.1:11434` for local Ollama.
- **Data Protection**: API keys and credential strings are automatically masked and scrubbed.

---

## 🔄 Backward Compatibility Notice

For automated pipelines or existing user scripts configured for ORION:
- `from core.agent import OrionAgent` aliases `NeoAgent`.
- `from ui.window import OrionWindow` aliases `NeoWindow`.
- `from interfaces.terminal import run_terminal` aliases `run_neo_terminal`.
- `from interfaces.api import OrionHandler, run_server` continue to function without modification.
- Existing settings files with `ORION_...` prefixes are automatically migrated without data loss.
