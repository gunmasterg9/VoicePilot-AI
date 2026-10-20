using System.Text.Json.Serialization;

namespace VoicePilot.Core.Configuration;

/// <summary>
/// Persistent application settings for VoicePilot AI.
/// </summary>
public class AppSettings
{
    // Speech Recognition
    public string SpeechEngine { get; set; } = "Sapi"; // "Sapi", "Whisper"
    public string WhisperModelPath { get; set; } = string.Empty;
    public string Language { get; set; } = "en-US";

    // Speech Synthesis
    public bool TtsEnabled { get; set; } = true;
    public string TtsVoice { get; set; } = string.Empty; // empty uses system default
    public int TtsRate { get; set; } = 0; // -10 to 10
    public int TtsVolume { get; set; } = 100; // 0 to 100

    // Local LLM / Ollama
    public bool OllamaEnabled { get; set; } = false;
    public string OllamaEndpoint { get; set; } = "http://localhost:11434";
    public string OllamaModel { get; set; } = "llama3.2";
    public int OllamaTimeoutSeconds { get; set; } = 10;

    // Hotkey & UI
    public string GlobalHotkey { get; set; } = "Ctrl+Win+Space";
    public bool MinimizeToTrayOnClose { get; set; } = true;
    public bool StartMinimized { get; set; } = false;
    public bool DarkMode { get; set; } = true;

    // Privacy & History
    public bool SaveConversationHistory { get; set; } = true;
    public int MaxHistoryEntries { get; set; } = 200;

    // Permissions & Safety
    public List<string> CustomAllowedDirectories { get; set; } = new();
    public Dictionary<string, string> CustomAllowedApplications { get; set; } = new();
}
