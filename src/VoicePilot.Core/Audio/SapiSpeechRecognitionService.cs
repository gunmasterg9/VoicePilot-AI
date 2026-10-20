using System.Globalization;
using System.Speech.Recognition;
using VoicePilot.Core.Configuration;

namespace VoicePilot.Core.Audio;

public class SapiSpeechRecognitionService : ISpeechRecognitionService
{
    private SpeechRecognitionEngine? _engine;
    private readonly SettingsManager _settingsManager;
    private RecognitionState _state = RecognitionState.Idle;
    private bool _isDisposed;
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

    public SapiSpeechRecognitionService(SettingsManager settingsManager)
    {
        _settingsManager = settingsManager;
        InitializeEngine();
    }

    private void InitializeEngine()
    {
        try
        {
            // Try matching user system speech culture, fallback to en-US
            var culture = CultureInfo.CurrentCulture;
            try
            {
                _engine = new SpeechRecognitionEngine(culture);
            }
            catch
            {
                _engine = new SpeechRecognitionEngine(new CultureInfo("en-US"));
            }

            // Load free-form dictation grammar
            var dictation = new DictationGrammar();
            _engine.LoadGrammar(dictation);

            // Load common command choices for instant recognition accuracy
            var choices = new Choices(
                "what time is it", "what is the date", "what day is today",
                "open calculator", "launch notepad", "open paint",
                "open file explorer", "open edge", "open chrome",
                "open task manager", "open terminal",
                "mute volume", "unmute volume", "lock workstation", "lock screen",
                "search files", "open documents", "open downloads", "open desktop",
                "what can you do", "help", "clear history");
            var gb = new GrammarBuilder(choices);
            var cmdGrammar = new Grammar(gb) { Name = "VoicePilotBuiltinCommands" };
            _engine.LoadGrammar(cmdGrammar);

            _engine.SpeechRecognized += OnSpeechRecognized;
            _engine.SpeechHypothesized += OnSpeechHypothesized;
            _engine.AudioLevelUpdated += OnAudioLevelUpdated;
            _engine.RecognizeCompleted += OnRecognizeCompleted;

            StatusMessageChanged?.Invoke(this, "Speech recognition initialized with Windows Desktop SAPI.");
        }
        catch (Exception ex)
        {
            State = RecognitionState.Error;
            var err = $"Speech engine initialization warning: {ex.Message}. Text input remains available.";
            StatusMessageChanged?.Invoke(this, err);
            ErrorOccurred?.Invoke(this, err);
        }
    }

    public Task StartListeningAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (IsListening)
                return Task.CompletedTask;

            if (_engine == null)
            {
                InitializeEngine();
                if (_engine == null)
                {
                    ErrorOccurred?.Invoke(this, "Speech recognition engine is unavailable.");
                    return Task.CompletedTask;
                }
            }

            try
            {
                _engine.SetInputToDefaultAudioDevice();
                _engine.RecognizeAsync(RecognizeMode.Multiple);
                State = RecognitionState.Listening;
                StatusMessageChanged?.Invoke(this, "Listening for speech...");
            }
            catch (InvalidOperationException)
            {
                State = RecognitionState.Error;
                var msg = "No audio input device detected. Please connect a microphone or use keyboard input.";
                StatusMessageChanged?.Invoke(this, msg);
                ErrorOccurred?.Invoke(this, msg);
            }
            catch (Exception ex)
            {
                State = RecognitionState.Error;
                var msg = $"Microphone error: {ex.Message}";
                StatusMessageChanged?.Invoke(this, msg);
                ErrorOccurred?.Invoke(this, msg);
            }
        }
        return Task.CompletedTask;
    }

    public Task StopListeningAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (!IsListening || _engine == null)
            {
                State = RecognitionState.Idle;
                AudioLevelChanged?.Invoke(this, 0.0f);
                return Task.CompletedTask;
            }

            try
            {
                _engine.RecognizeAsyncStop();
            }
            catch
            {
                // Ignore cancel race conditions
            }

            State = RecognitionState.Idle;
            AudioLevelChanged?.Invoke(this, 0.0f);
            StatusMessageChanged?.Invoke(this, "Ready. Push-to-talk or click the microphone to speak.");
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

    private void OnSpeechHypothesized(object? sender, SpeechHypothesizedEventArgs e)
    {
        if (!string.IsNullOrWhiteSpace(e.Result.Text))
        {
            SpeechHypothesized?.Invoke(this, e.Result.Text);
        }
    }

    private void OnSpeechRecognized(object? sender, SpeechRecognizedEventArgs e)
    {
        if (e.Result != null && !string.IsNullOrWhiteSpace(e.Result.Text))
        {
            // Confidence check (e.g. at least 0.25 for dictation)
            if (e.Result.Confidence >= 0.20f)
            {
                SpeechRecognized?.Invoke(this, e.Result.Text);
            }
        }
    }

    private void OnAudioLevelUpdated(object? sender, AudioLevelUpdatedEventArgs e)
    {
        if (IsListening)
        {
            // e.AudioLevel is 0-100
            float normalized = Math.Clamp(e.AudioLevel / 100.0f, 0.0f, 1.0f);
            AudioLevelChanged?.Invoke(this, normalized);
        }
    }

    private void OnRecognizeCompleted(object? sender, RecognizeCompletedEventArgs e)
    {
        if (State == RecognitionState.Listening)
        {
            State = RecognitionState.Idle;
            AudioLevelChanged?.Invoke(this, 0.0f);
        }
    }

    public void Dispose()
    {
        lock (_lock)
        {
            if (_isDisposed)
                return;
            _isDisposed = true;

            try
            {
                _engine?.RecognizeAsyncCancel();
                _engine?.Dispose();
            }
            catch
            {
                // Suppress on dispose
            }
            _engine = null;
        }
        GC.SuppressFinalize(this);
    }
}
