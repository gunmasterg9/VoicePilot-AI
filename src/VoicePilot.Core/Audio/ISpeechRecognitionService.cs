namespace VoicePilot.Core.Audio;

public enum RecognitionState
{
    Idle,
    Listening,
    Processing,
    Error
}

public interface ISpeechRecognitionService : IDisposable
{
    RecognitionState State { get; }
    bool IsListening { get; }

    event EventHandler<string>? SpeechRecognized;
    event EventHandler<string>? SpeechHypothesized;
    event EventHandler<float>? AudioLevelChanged; // 0.0f to 1.0f
    event EventHandler<RecognitionState>? StateChanged;
    event EventHandler<string>? StatusMessageChanged;
    event EventHandler<string>? ErrorOccurred;

    Task StartListeningAsync(CancellationToken ct = default);
    Task StopListeningAsync(CancellationToken ct = default);
    void PushSimulatedSpeech(string text);
}
