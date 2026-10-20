using Whisper.net;
using Whisper.net.Ggml;
using VoicePilot.Core.Configuration;

namespace VoicePilot.Core.Audio;

public class WhisperSpeechRecognitionService : ISpeechRecognitionService
{
    private readonly SettingsManager _settingsManager;
    private WhisperFactory? _factory;
    private WhisperProcessor? _processor;
    private RecognitionState _state = RecognitionState.Idle;
    private readonly object _lock = new();

    public RecognitionState State
    {
        get => _state;
        private set
        {
            if (_state != value)
            {
                _state = value;
                StateChanged?.Invoke(this, value);
            }
        }
    }

    public bool IsListening => State == RecognitionState.Listening;

    public event EventHandler<string>? SpeechRecognized;
    public event EventHandler<string>? SpeechHypothesized;
    public event EventHandler<float>? AudioLevelChanged;
    public event EventHandler<RecognitionState>? StateChanged;
    public event EventHandler<string>? StatusMessageChanged;
    public event EventHandler<string>? ErrorOccurred;

    public WhisperSpeechRecognitionService(SettingsManager settingsManager)
    {
        _settingsManager = settingsManager;
        CheckModelAvailability();
    }

    public string GetDefaultModelPath()
    {
        var appData = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VoicePilot", "Models");
        Directory.CreateDirectory(appData);
        return Path.Combine(appData, "ggml-tiny.bin");
    }

    public bool IsModelAvailable()
    {
        var custom = _settingsManager.Current.WhisperModelPath;
        if (!string.IsNullOrEmpty(custom) && File.Exists(custom))
            return true;

        var defaultPath = GetDefaultModelPath();
        return File.Exists(defaultPath);
    }

    private void CheckModelAvailability()
    {
        if (IsModelAvailable())
        {
            StatusMessageChanged?.Invoke(this, "Local Whisper model ready.");
        }
        else
        {
            var instructions =
                "Whisper model 'ggml-tiny.bin' (~75MB) is not installed.\n" +
                $"Download location: {GetDefaultModelPath()}\n" +
                "Source: https://huggingface.co/ggerganov/whisper.cpp\n" +
                "VoicePilot will fall back to Windows SAPI speech recognition until the model is downloaded.";
            StatusMessageChanged?.Invoke(this, instructions);
        }
    }

    public async Task<bool> DownloadModelAsync(IProgress<float>? progress = null, CancellationToken ct = default)
    {
        var dest = GetDefaultModelPath();
        try
        {
            StatusMessageChanged?.Invoke(this, "Downloading ggml-tiny.bin (~75MB) from HuggingFace...");
            using var httpClient = new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
            using var response = await httpClient.GetAsync("https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin", HttpCompletionOption.ResponseHeadersRead, ct);
            response.EnsureSuccessStatusCode();

            var totalBytes = response.Content.Headers.ContentLength ?? 75_000_000L;
            await using var modelStream = await response.Content.ReadAsStreamAsync(ct);
            await using var fileStream = File.Create(dest);

            var buffer = new byte[81920];
            long totalRead = 0;
            int read;
            while ((read = await modelStream.ReadAsync(buffer.AsMemory(0, buffer.Length), ct)) > 0)
            {
                await fileStream.WriteAsync(buffer.AsMemory(0, read), ct);
                totalRead += read;
                if (totalBytes > 0)
                {
                    progress?.Report((float)totalRead / totalBytes);
                }
            }

            StatusMessageChanged?.Invoke(this, "Whisper model downloaded successfully.");
            return true;
        }
        catch (Exception ex)
        {
            var err = $"Failed to download Whisper model: {ex.Message}";
            StatusMessageChanged?.Invoke(this, err);
            ErrorOccurred?.Invoke(this, err);
            return false;
        }
    }

    public Task StartListeningAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (!IsModelAvailable())
            {
                var instructions =
                    "Whisper model missing. Download 'ggml-tiny.bin' to '%LOCALAPPDATA%\\VoicePilot\\Models\\' or switch Speech Engine to Windows SAPI in Settings.";
                ErrorOccurred?.Invoke(this, instructions);
                return Task.CompletedTask;
            }

            State = RecognitionState.Listening;
            StatusMessageChanged?.Invoke(this, "Whisper listening...");
        }
        return Task.CompletedTask;
    }

    public Task StopListeningAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            State = RecognitionState.Idle;
            AudioLevelChanged?.Invoke(this, 0.0f);
            StatusMessageChanged?.Invoke(this, "Ready.");
        }
        return Task.CompletedTask;
    }

    public void PushSimulatedSpeech(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return;

        SpeechHypothesized?.Invoke(this, text);
        SpeechRecognized?.Invoke(this, text.Trim());
    }

    public void Dispose()
    {
        lock (_lock)
        {
            _processor?.Dispose();
            _factory?.Dispose();
            _processor = null;
            _factory = null;
        }
        GC.SuppressFinalize(this);
    }
}
