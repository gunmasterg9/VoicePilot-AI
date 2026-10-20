# VoicePilot AI - Native Windows Desktop Voice Assistant

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%20Windows%2011-0078D6?logo=windows)](https://microsoft.com/windows)
[![Framework](https://img.shields.io/badge/Framework-.NET%209%20LTS-512BD4?logo=dotnet)](https://dotnet.microsoft.com/)
[![UI](https://img.shields.io/badge/UI-WPF%20Fluent%20Design-00D2FF)](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/)
[![Installer](https://img.shields.io/badge/Installer-WiX%207%20MSI-10B981)](https://wixtoolset.org/)
[![License](https://img.shields.io/badge/License-MIT-purple)](#)

**VoicePilot AI** is a genuine, high-performance native Windows PC desktop voice assistant engineered in C# on .NET 9 using Windows Presentation Foundation (WPF) with modern Fluent-inspired dark ergonomics.

It is **NOT** a website, browser wrapper, Electron app, Tauri app, or WebView shell. It runs as a true compiled Windows executable (`VoicePilot.exe`), integrates directly with Win32 APIs, P/Invoke, and Windows Multimedia, and operates with local privacy-first architecture.

---

## 🌟 Key Features

- **Microphone & Push-to-Talk**: One-click microphone toggle, push-to-talk, and configurable global hotkeys (default: `Ctrl+Win+Space`).
- **Real-Time Voice Waveform Visualizer**: Smooth native WPF audio visualizer rendering dynamic sound bars matching real microphone audio input levels.
- **Live Speech Transcription**: Displays instantaneous partial speech hypotheses as you speak and commits finalized transcripts.
- **Controlled PC Automation (Zero Shell Injection)**:
  - **Launch Approved Applications**: Safely launches apps like Notepad, Calculator, Edge, Chrome, Task Manager, Windows Terminal, and custom allowlisted executables.
  - **Open Authorized Paths**: Opens approved directories (Documents, Downloads, Desktop, Pictures, Music) in File Explorer with path traversal protection.
  - **Search Local Files**: Fast, non-blocking file search within approved user folders.
  - **Date & Time Readout**: Speaks and formats current local time, date, and day of week.
  - **System Controls**: Workstation lock (`LockWorkStation` Win32 API), audio mute toggle, and battery status.
  - **Web Search**: Safe URL-encoded web queries via default browser.
  - **Clipboard Support**: Read and copy text to the Windows clipboard safely.
- **Confirmation Gate for Sensitive Actions**: Destructive actions (such as file deletion or sensitive file operations) are gated behind an interactive confirmation card requiring explicit user approval before execution.
- **Local AI & Multi-Engine Intent Processing**:
  - **Tier 1 (Instant Offline Rule Engine)**: Deterministic, zero-latency keyword and regex matcher working 100% offline with no model dependencies.
  - **Tier 2 (Local Ollama LLM Engine)**: Connects to local Ollama (`http://localhost:11434`, e.g., `llama3.2`) using structured JSON function calling with strict schema validation. Automatically falls back to Tier 1 if Ollama is offline.
- **Privacy First**:
  - Microphone audio and conversation transcripts remain strictly local to your machine.
  - Sensitive tokens, API keys, passwords, and personal identity data are automatically redacted from logs.
  - Easy button to view, manage, and clear locally stored conversation history.
- **Background Tray Operation**:
  - Minimizes smoothly to the Windows System Notification Area (System Tray).
  - Context menu with quick actions ("Open VoicePilot", "Start Listening", "Stop Listening", "Settings", "Exit").
- **Managed Extension Plugin Architecture**:
  - Discover and load managed .NET assemblies (`IPlugin`) inside isolated `AssemblyLoadContext` sandboxes.
  - Includes a working sample plugin (`VoicePilot.Plugins.Sample`) providing weather simulation, quick voice note-taking, and system diagnostics.
- **Professional Windows Installer**:
  - Generates a versioned Windows Installer (`VoicePilot-Setup-1.0.0.msi`) built with WiX 7, creating Desktop and Start Menu shortcuts and registering uninstallation in Windows Settings.

---

## 🏛 Architecture Overview

```
VoicePilot.sln
│
├── src/
│   ├── VoicePilot.Sdk/             # Public plugin contracts & data models (IPlugin, IActionDefinition, ActionResult)
│   ├── VoicePilot.Core/            # Core engine, audio abstractions, security allowlists, intent parsing, storage
│   │   ├── Audio/                  # ISpeechRecognitionService, SapiSpeechRecognitionService, WhisperSpeechRecognitionService
│   │   ├── Synthesis/              # ISpeechSynthesisService, SapiSpeechSynthesisService
│   │   ├── Automation/             # IAction, ActionRegistry, ActionExecutor, typed actions
│   │   │   └── Actions/            # DateTimeAction, LaunchAppAction, OpenPathAction, SearchFilesAction,
│   │   │                           # SystemControlAction, WebSearchAction, ClipboardAction, DeleteFileAction
│   │   ├── Security/               # PathSecurityValidator, AppAllowlistValidator, SensitiveDataMasker
│   │   ├── Intent/                 # IIntentParser, RuleBasedIntentParser, IntentResult
│   │   ├── Llm/                    # ILanguageModelService, OllamaLanguageModelService
│   │   ├── Configuration/          # AppSettings, SettingsManager
│   │   ├── Storage/                # IConversationHistoryStore, JsonConversationHistoryStore
│   │   ├── Plugins/                # PluginLoader, PluginContext, PluginActionWrapper
│   │   └── Interop/                # NativeMethods (RegisterHotKey, LockWorkStation, WM_APPCOMMAND)
│   │
│   ├── VoicePilot.App/             # Native WPF Application executable (Fluent UI, MVVM)
│   │   ├── Controls/               # WaveformVisualizer (dynamic audio bars)
│   │   ├── Styles/                 # FluentTheme.xaml (modern dark Fluent design tokens)
│   │   ├── ViewModels/             # MainViewModel, SettingsViewModel, ConversationBubbleViewModel
│   │   ├── Views/                  # MainWindow.xaml, SettingsWindow.xaml
│   │   ├── Services/               # GlobalHotkeyService, TrayIconService
│   │   └── App.xaml                # DI container setup & application bootstrapper
│   │
│   ├── VoicePilot.Plugins.Sample/  # Demonstrator plugin (sample.weather, sample.note, sample.diagnostics)
│   └── VoicePilot.Installer/       # WiX 7 Packaging definition (Package.wxs)
│
├── tests/
│   └── VoicePilot.Tests/           # 25 Automated unit and integration tests
│
├── build.ps1                       # Automated build & test execution script
└── publish.ps1                     # Automated self-contained publish & WiX MSI compilation script
```

---

## 🚀 Quick Start

### Prerequisites
- Windows 10 (Build 19041+) or Windows 11 (x64)
- [.NET 9 SDK](https://dotnet.microsoft.com/download/dotnet/9.0)
- WiX Toolset 7 (Automatically installed via `dotnet tool install --global wix` if needed)

### Build and Run

```powershell
# 1. Clone repository and navigate to folder
cd "VoicePilot AI"

# 2. Build solution and run automated test suite (25 tests)
.\build.ps1

# 3. Launch the native WPF desktop application
dotnet run --project src/VoicePilot.App
```

### Self-Contained Publishing & Windows Installer Creation

```powershell
# Runs self-contained win-x64 compilation and builds the WiX 7 MSI installer
.\publish.ps1
```

Generated deliverables:
- **Standalone Executable**: `publish\win-x64\VoicePilot.exe`
- **Windows MSI Installer**: `installer\VoicePilot-Setup-1.0.0.msi` (61.6 MB, self-contained)

---

## 🎙 Speech & AI Setup Instructions

### 1. Speech Recognition (STT)
VoicePilot includes two local STT providers:
1. **Windows Desktop SAPI (Default)**:
   - Works immediately out of the box with zero downloads on every Windows 10/11 system.
   - Includes real-time dictation and command grammars with audio amplitude event reporting.
2. **Local Whisper.net (GGML)**:
   - Size: ~75 MB (`ggml-tiny.bin`).
   - License: MIT License (OpenAI / whisper.cpp).
   - Storage Location: `%LOCALAPPDATA%\VoicePilot\Models\ggml-tiny.bin`.
   - Setup: Open **Settings** in VoicePilot and click **Download Whisper Model**, or download manually from [HuggingFace whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin) and place it into `%LOCALAPPDATA%\VoicePilot\Models\`.

### 2. Speech Synthesis (TTS)
- Uses native Windows SAPI voices (`Microsoft David`, `Microsoft Zira`, `Microsoft Mark`, or any installed Windows OneCore voice).
- Configurable speech rate (-10 to 10) and volume (0 to 100) from the Settings window.
- Instant cancellation support when the user pushes the microphone button to interrupt.

### 3. Optional Local LLM (Ollama)
- Built-in deterministic commands work 100% offline without an LLM.
- To enable natural language understanding via local LLM:
  1. Install [Ollama for Windows](https://ollama.com/download).
  2. Pull your preferred model:
     ```powershell
     ollama run llama3.2
     ```
  3. In VoicePilot **Settings**, check **Enable Ollama LLM intent parsing**.
  4. Test the connection using the **Test Ollama Connection** button.
  5. VoicePilot prompts Ollama to produce strict typed JSON mapped to allowlisted actions. If Ollama is offline or returns an invalid action, VoicePilot gracefully falls back to the local rule engine.

---

## 🛡 Security & Privacy Architecture

1. **Zero Shell Execution**: VoicePilot **never** passes arbitrary user or LLM strings to `cmd.exe` or `powershell.exe`. Requests are parsed into strictly typed `IAction` instances with validated arguments.
2. **Path Security Validator**: Prohibits access to Windows system directories (`C:\Windows`, `System32`, `Program Files`, root volume paths) and blocks directory traversal (`..`).
3. **Application Allowlist**: Launches only known productivity applications or user-approved executables. Blocks script hosts (`wscript`, `cscript`, `mshta`, `regedit`, `certutil`).
4. **Sensitive Action Confirmation Gate**: High-risk actions like `system.delete_file` present a confirmation card requiring explicit user clicking before deletion.
5. **Sensitive Data Masking**: Automatically masks API keys, secrets, passwords, and personal credentials in log streams.
6. **Local Conversation Storage**: Conversation history is persisted to `%LOCALAPPDATA%\VoicePilot\history.json`. Users can view the file or clear all history with a single click.

---

## 🧩 Plugin Architecture

Developers can create extension assemblies implementing `VoicePilot.Sdk.IPlugin`:

```csharp
using VoicePilot.Sdk;

public class MyCustomPlugin : IPlugin
{
    public string Id => "com.example.myplugin";
    public string Name => "Custom Tools Plugin";
    public string Version => "1.0.0";
    public string Description => "Sample custom plugin";
    public string Author => "Developer";

    public Task InitializeAsync(IPluginContext context, CancellationToken ct = default)
    {
        context.LogInfo("Initialized!");
        return Task.CompletedTask;
    }

    public IReadOnlyList<IActionDefinition> GetActions() => new[]
    {
        new ActionDefinition
        {
            Name = "tools.myaction",
            Description = "Executes custom logic",
            Parameters = new ActionParameterDefinition[] { ... }
        }
    };

    public Task<ActionResult> ExecuteActionAsync(string actionName, IReadOnlyDictionary<string, object?> parameters, CancellationToken ct = default)
    {
        return Task.FromResult(ActionResult.Ok("Executed successfully!"));
    }

    public Task ShutdownAsync(CancellationToken ct = default) => Task.CompletedTask;
}
```

Place compiled plugin `.dll` files in `%APPDATA%\VoicePilot\Plugins\`. The host validates directory safety and loads plugins into isolated `AssemblyLoadContext` domains.

---

## 🧪 Test Suite

Run all automated unit and integration tests:

```powershell
dotnet test tests/VoicePilot.Tests/VoicePilot.Tests.csproj --logger "console;verbosity=normal"
```

Tested scenarios (25 tests):
- Redaction of API keys and passwords via `SensitiveDataMasker`
- Enforcement of path traversal rejection and restricted Windows folders in `PathSecurityValidator`
- Verification of allowed application aliases and rejection of blocked binaries in `AppAllowlistValidator`
- Intent parsing for date/time, app launches, folder navigation, file search, system controls, and clipboard
- Confirmation gating enforcement in `ActionExecutor`
- Thread-safe conversation history storage, capping, and clearing
- Dynamic plugin action execution and diagnostics reporting
- End-to-end vertical slice integration pipeline (voice capture simulation -> pattern match -> action execution -> SAPI speech synthesis -> history persistence)
