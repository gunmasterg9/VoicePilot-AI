using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using System.Windows.Input;
using VoicePilot.Core;
using VoicePilot.Core.Audio;
using VoicePilot.Core.Configuration;
using VoicePilot.Core.Llm;
using VoicePilot.Core.Synthesis;

namespace VoicePilot.App.ViewModels;

public class SettingsViewModel : ViewModelBase
{
    private readonly SettingsManager _settingsManager;
    private readonly ISpeechSynthesisService _speechSynthesis;
    private readonly WhisperSpeechRecognitionService _whisperService;
    private readonly ILanguageModelService _llmService;

    private string _speechEngine;
    private string _selectedVoice;
    private int _ttsRate;
    private int _ttsVolume;
    private bool _ttsEnabled;
    private bool _ollamaEnabled;
    private string _ollamaEndpoint;
    private string _ollamaModel;
    private string _globalHotkey;
    private bool _minimizeToTray;
    private bool _saveHistory;
    private string _whisperStatus;
    private float _whisperDownloadProgress;
    private bool _isDownloadingWhisper;
    private string _ollamaStatus;

    public ObservableCollection<VoiceProfile> AvailableVoices { get; } = new();
    public ObservableCollection<string> AllowedDirectories { get; } = new();
    public ObservableCollection<string> AllowedApplications { get; } = new();

    public string SpeechEngine
    {
        get => _speechEngine;
        set => SetProperty(ref _speechEngine, value);
    }

    public string SelectedVoice
    {
        get => _selectedVoice;
        set => SetProperty(ref _selectedVoice, value);
    }

    public int TtsRate
    {
        get => _ttsRate;
        set => SetProperty(ref _ttsRate, value);
    }

    public int TtsVolume
    {
        get => _ttsVolume;
        set => SetProperty(ref _ttsVolume, value);
    }

    public bool TtsEnabled
    {
        get => _ttsEnabled;
        set => SetProperty(ref _ttsEnabled, value);
    }

    public bool OllamaEnabled
    {
        get => _ollamaEnabled;
        set => SetProperty(ref _ollamaEnabled, value);
    }

    public string OllamaEndpoint
    {
        get => _ollamaEndpoint;
        set => SetProperty(ref _ollamaEndpoint, value);
    }

    public string OllamaModel
    {
        get => _ollamaModel;
        set => SetProperty(ref _ollamaModel, value);
    }

    public string GlobalHotkey
    {
        get => _globalHotkey;
        set => SetProperty(ref _globalHotkey, value);
    }

    public bool MinimizeToTray
    {
        get => _minimizeToTray;
        set => SetProperty(ref _minimizeToTray, value);
    }

    public bool SaveHistory
    {
        get => _saveHistory;
        set => SetProperty(ref _saveHistory, value);
    }

    public string WhisperStatus
    {
        get => _whisperStatus;
        set => SetProperty(ref _whisperStatus, value);
    }

    public float WhisperDownloadProgress
    {
        get => _whisperDownloadProgress;
        set => SetProperty(ref _whisperDownloadProgress, value);
    }

    public bool IsDownloadingWhisper
    {
        get => _isDownloadingWhisper;
        set => SetProperty(ref _isDownloadingWhisper, value);
    }

    public string OllamaStatus
    {
        get => _ollamaStatus;
        set => SetProperty(ref _ollamaStatus, value);
    }

    public ICommand TestSpeechCommand { get; }
    public ICommand DownloadWhisperModelCommand { get; }
    public ICommand TestOllamaCommand { get; }
    public ICommand AddFolderCommand { get; }
    public ICommand RemoveFolderCommand { get; }
    public ICommand OpenAppDataFolderCommand { get; }
    public ICommand SaveSettingsCommand { get; }

    public event Action? RequestClose;

    public SettingsViewModel(
        SettingsManager settingsManager,
        ISpeechSynthesisService speechSynthesis,
        WhisperSpeechRecognitionService whisperService,
        ILanguageModelService llmService)
    {
        _settingsManager = settingsManager;
        _speechSynthesis = speechSynthesis;
        _whisperService = whisperService;
        _llmService = llmService;

        var s = _settingsManager.Current;
        _speechEngine = s.SpeechEngine;
        _selectedVoice = s.TtsVoice;
        _ttsRate = s.TtsRate;
        _ttsVolume = s.TtsVolume;
        _ttsEnabled = s.TtsEnabled;
        _ollamaEnabled = s.OllamaEnabled;
        _ollamaEndpoint = s.OllamaEndpoint;
        _ollamaModel = s.OllamaModel;
        _globalHotkey = s.GlobalHotkey;
        _minimizeToTray = s.MinimizeToTrayOnClose;
        _saveHistory = s.SaveConversationHistory;
        _whisperStatus = _whisperService.IsModelAvailable() ? "Local ggml-tiny.bin is installed." : "Model missing (~75MB required for Whisper).";
        _ollamaStatus = "Not tested yet.";

        foreach (var v in _speechSynthesis.GetInstalledVoices())
        {
            AvailableVoices.Add(v);
        }

        foreach (var dir in s.CustomAllowedDirectories)
        {
            AllowedDirectories.Add(dir);
        }

        foreach (var app in s.CustomAllowedApplications)
        {
            AllowedApplications.Add($"{app.Key} -> {app.Value}");
        }

        TestSpeechCommand = new AsyncRelayCommand(TestSpeechAsync);
        DownloadWhisperModelCommand = new AsyncRelayCommand(DownloadWhisperAsync);
        TestOllamaCommand = new AsyncRelayCommand(TestOllamaAsync);
        AddFolderCommand = new RelayCommand(AddFolder);
        RemoveFolderCommand = new RelayCommand(RemoveFolder);
        OpenAppDataFolderCommand = new RelayCommand(OpenAppDataFolder);
        SaveSettingsCommand = new RelayCommand(SaveSettings);
    }

    private async Task TestSpeechAsync()
    {
        _speechSynthesis.SetRate(TtsRate);
        _speechSynthesis.SetVolume(TtsVolume);
        if (!string.IsNullOrEmpty(SelectedVoice))
        {
            _speechSynthesis.SetVoice(SelectedVoice);
        }
        await _speechSynthesis.SpeakAsync("Hello! VoicePilot speech synthesis is working properly.");
    }

    private async Task DownloadWhisperAsync()
    {
        IsDownloadingWhisper = true;
        WhisperStatus = "Downloading ggml-tiny.bin (~75MB)...";

        var progress = new Progress<float>(val =>
        {
            WhisperDownloadProgress = val;
            WhisperStatus = $"Downloading: {(int)(val * 100)}%";
        });

        var success = await _whisperService.DownloadModelAsync(progress);
        IsDownloadingWhisper = false;

        WhisperStatus = success ? "Whisper model downloaded successfully!" : "Download failed. Check internet connection.";
    }

    private async Task TestOllamaAsync()
    {
        OllamaStatus = "Testing connection...";
        var reachable = await _llmService.TestConnectionAsync();
        if (reachable)
        {
            var models = await _llmService.GetAvailableModelsAsync();
            OllamaStatus = $"Connected! Found {models.Count} model(s): {string.Join(", ", models.Take(3))}";
        }
        else
        {
            OllamaStatus = "Unable to connect. Ensure Ollama is running (`ollama serve`).";
        }
    }

    private void AddFolder()
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "Select an additional safe folder for VoicePilot to access"
        };
        if (dialog.ShowDialog() == DialogResult.OK && !string.IsNullOrWhiteSpace(dialog.SelectedPath))
        {
            if (!AllowedDirectories.Contains(dialog.SelectedPath))
            {
                AllowedDirectories.Add(dialog.SelectedPath);
            }
        }
    }

    private void RemoveFolder(object? parameter)
    {
        if (parameter is string folder && AllowedDirectories.Contains(folder))
        {
            AllowedDirectories.Remove(folder);
        }
    }

    private void OpenAppDataFolder()
    {
        var appData = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VoicePilot");
        Directory.CreateDirectory(appData);
        Process.Start(new ProcessStartInfo { FileName = "explorer.exe", Arguments = appData, UseShellExecute = true });
    }

    public void SaveSettings()
    {
        var s = _settingsManager.Current;
        s.SpeechEngine = SpeechEngine;
        s.TtsVoice = SelectedVoice;
        s.TtsRate = TtsRate;
        s.TtsVolume = TtsVolume;
        s.TtsEnabled = TtsEnabled;
        s.OllamaEnabled = OllamaEnabled;
        s.OllamaEndpoint = OllamaEndpoint;
        s.OllamaModel = OllamaModel;
        s.GlobalHotkey = GlobalHotkey;
        s.MinimizeToTrayOnClose = MinimizeToTray;
        s.SaveConversationHistory = SaveHistory;

        s.CustomAllowedDirectories = AllowedDirectories.ToList();

        _settingsManager.SaveSettings(s);

        _speechSynthesis.SetRate(TtsRate);
        _speechSynthesis.SetVolume(TtsVolume);
        if (!string.IsNullOrEmpty(SelectedVoice))
        {
            _speechSynthesis.SetVoice(SelectedVoice);
        }

        RequestClose?.Invoke();
    }
}
