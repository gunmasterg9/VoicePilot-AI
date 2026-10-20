using System.Text.Json;
using VoicePilot.Core.Security;

namespace VoicePilot.Core.Configuration;

/// <summary>
/// Handles persistent storage and retrieval of application settings in %LOCALAPPDATA%\VoicePilot.
/// </summary>
public class SettingsManager
{
    private readonly string _settingsFilePath;
    private readonly JsonSerializerOptions _jsonOptions;
    private AppSettings _currentSettings;

    public AppSettings Current => _currentSettings;

    public SettingsManager(string? customPath = null)
    {
        _jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNameCaseInsensitive = true
        };

        if (!string.IsNullOrEmpty(customPath))
        {
            _settingsFilePath = customPath;
        }
        else
        {
            var baseDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VoicePilot");
            Directory.CreateDirectory(baseDir);
            _settingsFilePath = Path.Combine(baseDir, "config.json");
        }

        _currentSettings = LoadSettings();
    }

    public AppSettings LoadSettings()
    {
        try
        {
            if (File.Exists(_settingsFilePath))
            {
                var json = File.ReadAllText(_settingsFilePath);
                var loaded = JsonSerializer.Deserialize<AppSettings>(json, _jsonOptions);
                if (loaded != null)
                {
                    _currentSettings = ValidateSettings(loaded);
                    return _currentSettings;
                }
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to load settings: {SensitiveDataMasker.Mask(ex.Message)}");
        }

        _currentSettings = new AppSettings();
        SaveSettings(_currentSettings);
        return _currentSettings;
    }

    public void SaveSettings(AppSettings? settings = null)
    {
        try
        {
            if (settings != null)
            {
                _currentSettings = ValidateSettings(settings);
            }

            var dir = Path.GetDirectoryName(_settingsFilePath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var json = JsonSerializer.Serialize(_currentSettings, _jsonOptions);
            File.WriteAllText(_settingsFilePath, json);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Failed to save settings: {SensitiveDataMasker.Mask(ex.Message)}");
        }
    }

    private static AppSettings ValidateSettings(AppSettings s)
    {
        // Enforce valid ranges
        s.TtsRate = Math.Clamp(s.TtsRate, -10, 10);
        s.TtsVolume = Math.Clamp(s.TtsVolume, 0, 100);
        s.OllamaTimeoutSeconds = Math.Clamp(s.OllamaTimeoutSeconds, 2, 60);
        s.MaxHistoryEntries = Math.Clamp(s.MaxHistoryEntries, 10, 2000);

        if (string.IsNullOrWhiteSpace(s.SpeechEngine) ||
            (!s.SpeechEngine.Equals("Sapi", StringComparison.OrdinalIgnoreCase) &&
             !s.SpeechEngine.Equals("Whisper", StringComparison.OrdinalIgnoreCase)))
        {
            s.SpeechEngine = "Sapi";
        }

        if (string.IsNullOrWhiteSpace(s.OllamaEndpoint))
        {
            s.OllamaEndpoint = "http://localhost:11434";
        }

        if (string.IsNullOrWhiteSpace(s.OllamaModel))
        {
            s.OllamaModel = "llama3.2";
        }

        return s;
    }
}
