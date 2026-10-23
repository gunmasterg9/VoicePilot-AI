# NEO AI — Your Local AI PC Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)
[![UI PySide6](https://img.shields.io/badge/UI-PySide6%20Qt6-41CD52.svg)](https://pypi.org/project/PySide6/)
[![Voice Faster--Whisper](https://img.shields.io/badge/ASR-Faster--Whisper-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![TTS Neural%20+%20SAPI](https://img.shields.io/badge/TTS-Neural%20%7C%20SAPI5-purple.svg)](https://github.com/rany2/edge-tts)

**NEO AI** (formerly ORION) is an advanced, offline-first, local AI PC assistant engineered specifically for Windows desktops. Built with Python 3.12 and PySide6, NEO combines local speech recognition (Faster-Whisper), dynamic local LLMs (Ollama), natural neural and offline SAPI5 text-to-speech, and secure desktop automation.

> **Original Creator & Attribution**: Created by **Gautam Vandar**. Upgraded to NEO AI architecture while preserving historical attribution and module compatibility.

---

## Key Features & Architecture

### 1. Animated CoreOrb Desktop UI
- **5-State Visual Pulse Engine**: Dynamic visual feedback for `READY`, `LISTENING`, `THINKING`, `SPEAKING`, and `ERROR` states.
- **Dedicated Controls**:
  - `◉ VOICE`: One-click speech recording and transcription.
  - `EXECUTE`: Instant keyboard command submission.
  - `🔊 TEST TTS`: Live audio playback verification.
  - `⏹ STOP`: Instant halt of speech synthesis and cancellation of active operations.
  - `⚙ SETTINGS`: Full diagnostic and configuration modal.
- **Scrollable Transcript Console**: Rich, styled conversation log with user inputs and assistant responses.
- **Live Hardware Telemetry**: Active LLM model, active TTS provider, voice state, and memory status.

### 2. Dual-Engine Speech Synthesis (TTS)
- **Online Neural TTS**: High-fidelity natural speech powered by Microsoft Edge Neural voices (supports English, Hindi, and Gujarati) with zero API keys required.
- **Offline SAPI5 Fallback**: Guaranteed audio output via native Windows SAPI voices even when disconnected from the internet.
- **Thread-Safe & Overlap Prevention**: Queues and playback locks prevent stuttering or overlapping voices.
- **Instant Interruption**: User can click `⏹ STOP` to immediately cut off speech playback.

### 3. Speech Recognition (ASR)
- **Local Faster-Whisper**: Runs quantized CPU int8 Whisper models (`tiny.en`, `base`, etc.) offline.
- **Audio Pipeline**: Real-time microphone capture via `sounddevice` and `SpeechRecognition` with direct float32 streaming.
- **Multi-language Ready**: Pre-configured voice and recognition support for English (`en`), Hindi (`hi`), and Gujarati (`gu`).

### 4. Dynamic LLM Brain & Provider Architecture
- **Local Ollama Integration**: Automatically polls `http://127.0.0.1:11434/api/tags` to discover installed models. Auto-selects lightweight models (e.g., `qwen3:1.7b`) optimized for 8 GB RAM machines.
- **Optional Cloud Provider**: OpenAI-compatible adapter available for cloud LLM endpoints.
- **Offline Fallback Engine**: Core system operations, time/date, application launching, hardware diagnostics, and navigation work even if the LLM is temporarily unreachable.

### 5. Secure PC Automation
- **System Root Guard**: Strict allowlists block destructive file actions against `C:\`, `C:\Windows`, `C:\Program Files`, and user accounts roots.
- **Confirmation Prompts**: Sensitive operations (`delete_path`, `shutdown_pc`, `restart_pc`) prompt the user with modal dialogs before execution.
- **Auditable Tool Registry**: Validated execution of applications, window management, and web navigation.

---

## Installation & Setup

### Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Python 3.10, 3.11, or 3.12 (Python 3.12 recommended)
- **Ollama**: (Optional for local LLM brain) [Download Ollama for Windows](https://ollama.com/download)

### 1. Clone & Setup Virtual Environment
```powershell
git clone <repo-url> "VoicePilot AI"
cd "VoicePilot AI"

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Setup Ollama (Recommended)
```powershell
# Pull a fast, lightweight model for 8 GB RAM systems
ollama pull qwen3:1.7b
```

---

## Launching NEO AI

### Option A: Desktop Double-Click Launcher
Double-click `launch_neo.bat`.

### Option B: Terminal Command
```powershell
# Launch PySide6 GUI (Default)
python main.py --mode ui

# Launch Terminal CLI Mode
python main.py --mode terminal

# Launch REST/HTTP API Server
python main.py --mode api
```

---

## Voice Commands Tested & Supported

NEO AI has been verified against 20 core PC automation and conversational commands:

| # | Command | Category | Expected Response |
|---|---------|----------|-------------------|
| 01 | `who are you` | Identity | "My name is NEO. I am your local AI PC assistant..." |
| 02 | `who created you` | Attribution | "I was created by Gautam Vandar." |
| 03 | `what can you do` | Capabilities | Capabilities overview and available modules |
| 04 | `what is your name` | Identity | "My name is NEO..." |
| 05 | `what time is it` | System API | Real-time system clock (e.g., "05:15 PM") |
| 06 | `what is today's date` | System API | Real-time calendar date |
| 07 | `check cpu usage` | Telemetry | Current CPU % load |
| 08 | `how much memory is used` | Telemetry | RAM usage percentage and GB breakdown |
| 09 | `check battery and system status` | Telemetry | Battery % and hardware health check |
| 10 | `open notepad` | App Launcher | Launches Windows Notepad (`notepad.exe`) |
| 11 | `open calculator` | App Launcher | Launches Windows Calculator (`calc.exe`) |
| 12 | `open file explorer` | App Launcher | Opens Windows File Explorer |
| 13 | `open command prompt` | App Launcher | Launches Command Prompt (`cmd.exe`) |
| 14 | `open google` | Web Navigation | Opens Google in default web browser |
| 15 | `open youtube` | Web Navigation | Opens YouTube in default web browser |
| 16 | `open github` | Web Navigation | Opens GitHub in default web browser |
| 17 | `open wikipedia` | Web Navigation | Opens Wikipedia in default web browser |
| 18 | `search for python documentation` | Web Search | Searches Google for specified query |
| 19 | `test your audio playback` | Diagnostics | Speaks: "NEO audio playback is operational..." |
| 20 | `tell me a joke` | Conversational | Delivers developer humor |

---

## Running Automated Tests

Run the complete test suite anytime to verify system stability:

```powershell
# Phase 1 Voice Commands & Pipeline Test (7 tests)
python -m unittest tests.test_phase1_voice_commands

# Comprehensive NEO AI Architecture & Security Test (17 tests)
python -m unittest tests.test_neo_ai
```

---

## Settings & Diagnostics Modal

Clicking `⚙ SETTINGS` opens the central configuration manager:
- **AI Brain Tab**: Switch between Ollama and Cloud providers, pick active Ollama models with live refresh, configure model timeouts.
- **Voice & Audio Tab**: Select audio input devices, choose Speech Recognition models (`tiny.en`, `base`, `small`), configure online neural voices (`Aria`, `Guy`, `Swara`, `Dhwani`), and run live mic & speaker tests.
- **Diagnostics Tab**: Inspect memory, CPU load, Ollama connection status, and installed dependencies in real time.

---

## Backward Compatibility Notice

For automated pipelines or existing user scripts configured for ORION:
- `from core.agent import OrionAgent` continues to work (aliases `NeoAgent`).
- `from ui.window import OrionWindow` continues to work (aliases `NeoWindow`).
- `from interfaces.terminal import run_terminal` continues to work (aliases `run_neo_terminal`).
- `from interfaces.api import OrionHandler, run_server` continue to work.
- Existing settings files with `ORION_...` prefixes are automatically migrated without data loss.
