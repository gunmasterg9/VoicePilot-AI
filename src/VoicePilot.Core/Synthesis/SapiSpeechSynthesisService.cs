using System.Speech.Synthesis;
using VoicePilot.Core.Configuration;

namespace VoicePilot.Core.Synthesis;

public class SapiSpeechSynthesisService : ISpeechSynthesisService
{
    private readonly SpeechSynthesizer _synthesizer;
    private readonly SettingsManager _settingsManager;
    private bool _isSpeaking;
    private TaskCompletionSource<bool>? _currentSpeechTcs;
    private readonly object _lock = new();

    public bool IsSpeaking
    {
        get => _isSpeaking;
        private set
        {
            if (_isSpeaking != value)
            {
                _isSpeaking = value;
                SpeakingStateChanged?.Invoke(this, value);
            }
        }
    }

    public event EventHandler<bool>? SpeakingStateChanged;

    public SapiSpeechSynthesisService(SettingsManager settingsManager)
    {
        _settingsManager = settingsManager;
        _synthesizer = new SpeechSynthesizer();

        // Configure default audio output
        try
        {
            _synthesizer.SetOutputToDefaultAudioDevice();
        }
        catch
        {
            // Fallback to null output if no audio output device is present
        }

        _synthesizer.SpeakStarted += (_, _) => IsSpeaking = true;
        _synthesizer.SpeakCompleted += (_, _) =>
        {
            IsSpeaking = false;
            lock (_lock)
            {
                _currentSpeechTcs?.TrySetResult(true);
            }
        };

        ApplySettings();
    }

    public void ApplySettings()
    {
        var settings = _settingsManager.Current;
        SetRate(settings.TtsRate);
        SetVolume(settings.TtsVolume);
        if (!string.IsNullOrEmpty(settings.TtsVoice))
        {
            SetVoice(settings.TtsVoice);
        }
    }

    public IReadOnlyList<VoiceProfile> GetInstalledVoices()
    {
        var list = new List<VoiceProfile>();
        try
        {
            foreach (var installedVoice in _synthesizer.GetInstalledVoices())
            {
                var info = installedVoice.VoiceInfo;
                list.Add(new VoiceProfile(
                    info.Name,
                    info.Description,
                    info.Culture.Name,
                    info.Gender.ToString()
                ));
            }
        }
        catch
        {
            // SAPI enumeration fallback
        }
        return list;
    }

    public async Task SpeakAsync(string text, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(text) || !_settingsManager.Current.TtsEnabled)
            return;

        StopSpeaking();

        TaskCompletionSource<bool> tcs;
        lock (_lock)
        {
            tcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            _currentSpeechTcs = tcs;
        }

        using var reg = ct.Register(() =>
        {
            StopSpeaking();
            tcs.TrySetCanceled(ct);
        });

        try
        {
            _synthesizer.SpeakAsync(text);
            await tcs.Task;
        }
        catch (OperationCanceledException)
        {
            // Canceled gracefully
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"SAPI SpeakAsync error: {ex.Message}");
        }
    }

    public void StopSpeaking()
    {
        lock (_lock)
        {
            try
            {
                _synthesizer.SpeakAsyncCancelAll();
            }
            catch
            {
                // Ignore cancel race conditions
            }
            IsSpeaking = false;
            _currentSpeechTcs?.TrySetCanceled();
            _currentSpeechTcs = null;
        }
    }

    public void SetVoice(string? voiceName)
    {
        if (string.IsNullOrWhiteSpace(voiceName))
            return;

        try
        {
            _synthesizer.SelectVoice(voiceName);
        }
        catch
        {
            // Keep current voice if requested voice not installed
        }
    }

    public void SetRate(int rate)
    {
        _synthesizer.Rate = Math.Clamp(rate, -10, 10);
    }

    public void SetVolume(int volume)
    {
        _synthesizer.Volume = Math.Clamp(volume, 0, 100);
    }

    public void Dispose()
    {
        StopSpeaking();
        _synthesizer.Dispose();
        GC.SuppressFinalize(this);
    }
}
