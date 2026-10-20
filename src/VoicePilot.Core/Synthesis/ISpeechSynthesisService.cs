namespace VoicePilot.Core.Synthesis;

public record VoiceProfile(string Name, string Description, string Culture, string Gender);

public interface ISpeechSynthesisService : IDisposable
{
    bool IsSpeaking { get; }
    event EventHandler<bool>? SpeakingStateChanged;

    IReadOnlyList<VoiceProfile> GetInstalledVoices();
    Task SpeakAsync(string text, CancellationToken ct = default);
    void StopSpeaking();
    void SetVoice(string? voiceName);
    void SetRate(int rate);
    void SetVolume(int volume);
}
