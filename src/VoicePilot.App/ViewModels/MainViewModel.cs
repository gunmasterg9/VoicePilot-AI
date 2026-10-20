using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Input;
using WpfApp = System.Windows.Application;
using VoicePilot.Core;
using VoicePilot.Core.Audio;
using VoicePilot.Core.Automation;
using VoicePilot.Core.Storage;

namespace VoicePilot.App.ViewModels;

public class MainViewModel : ViewModelBase
{
    private readonly AssistantEngine _engine;
    private readonly Func<SettingsViewModel> _settingsVmFactory;
    private readonly Action<SettingsViewModel> _openSettingsWindow;

    private RecognitionState _recognitionState = RecognitionState.Idle;
    private string _liveTranscription = string.Empty;
    private float _audioLevel = 0.0f;
    private string _statusText = "Ready. Click the microphone or push-to-talk.";
    private string _textInput = string.Empty;
    private bool _hasPendingConfirmation;
    private string _confirmationPrompt = string.Empty;
    private ExecutionRequest? _pendingRequest;

    public ObservableCollection<ConversationBubbleViewModel> Conversation { get; } = new();

    public RecognitionState State
    {
        get => _recognitionState;
        set
        {
            if (SetProperty(ref _recognitionState, value))
            {
                OnPropertyChanged(nameof(IsListening));
                OnPropertyChanged(nameof(StateBadgeText));
            }
        }
    }

    public bool IsListening => State == RecognitionState.Listening;

    public string StateBadgeText => State switch
    {
        RecognitionState.Listening => "Listening...",
        RecognitionState.Processing => "Processing...",
        RecognitionState.Error => "Attention Needed",
        _ => "Idle"
    };

    public string LiveTranscription
    {
        get => _liveTranscription;
        set => SetProperty(ref _liveTranscription, value);
    }

    public float AudioLevel
    {
        get => _audioLevel;
        set => SetProperty(ref _audioLevel, value);
    }

    public string StatusText
    {
        get => _statusText;
        set => SetProperty(ref _statusText, value);
    }

    public string TextInput
    {
        get => _textInput;
        set => SetProperty(ref _textInput, value);
    }

    public bool HasPendingConfirmation
    {
        get => _hasPendingConfirmation;
        set => SetProperty(ref _hasPendingConfirmation, value);
    }

    public string ConfirmationPrompt
    {
        get => _confirmationPrompt;
        set => SetProperty(ref _confirmationPrompt, value);
    }

    public string PrivacyStatusText => "🔒 Local Only | Never Uploaded to Cloud";

    public ICommand ToggleListeningCommand { get; }
    public ICommand SendTextCommand { get; }
    public ICommand ConfirmActionCommand { get; }
    public ICommand CancelActionCommand { get; }
    public ICommand ClearHistoryCommand { get; }
    public ICommand OpenSettingsCommand { get; }

    public MainViewModel(
        AssistantEngine engine,
        Func<SettingsViewModel> settingsVmFactory,
        Action<SettingsViewModel> openSettingsWindow)
    {
        _engine = engine;
        _settingsVmFactory = settingsVmFactory;
        _openSettingsWindow = openSettingsWindow;

        ToggleListeningCommand = new AsyncRelayCommand(ToggleListeningAsync);
        SendTextCommand = new AsyncRelayCommand(SendTextInputAsync);
        ConfirmActionCommand = new AsyncRelayCommand(ConfirmPendingActionAsync);
        CancelActionCommand = new RelayCommand(CancelPendingAction);
        ClearHistoryCommand = new AsyncRelayCommand(ClearHistoryAsync);
        OpenSettingsCommand = new RelayCommand(OpenSettings);

        WireEngineEvents();
        LoadExistingHistoryAsync().ConfigureAwait(false);
    }

    private void WireEngineEvents()
    {
        _engine.Recognition.StateChanged += (_, s) =>
        {
            WpfApp.Current?.Dispatcher.Invoke(() => State = s);
        };

        _engine.AudioLevelUpdated += (_, lvl) =>
        {
            WpfApp.Current?.Dispatcher.Invoke(() => AudioLevel = lvl);
        };

        _engine.LiveTranscriptionChanged += (_, text) =>
        {
            WpfApp.Current?.Dispatcher.Invoke(() => LiveTranscription = text);
        };

        _engine.StatusChanged += (_, status) =>
        {
            WpfApp.Current?.Dispatcher.Invoke(() => StatusText = status);
        };

        _engine.TurnCompleted += (_, entry) =>
        {
            WpfApp.Current?.Dispatcher.Invoke(() =>
            {
                LiveTranscription = string.Empty;
                Conversation.Add(new ConversationBubbleViewModel
                {
                    Id = entry.Id,
                    Timestamp = entry.Timestamp,
                    UserUtterance = entry.UserUtterance,
                    AssistantResponse = entry.AssistantResponse,
                    ActionName = entry.ActionName,
                    Success = entry.Success,
                    Engine = entry.Engine,
                    RequiresConfirmation = entry.RequiresConfirmation,
                    Confirmed = entry.Confirmed
                });
            });
        };

        _engine.ConfirmationRequested += (_, req) =>
        {
            WpfApp.Current?.Dispatcher.Invoke(() =>
            {
                _pendingRequest = req;
                ConfirmationPrompt = $"Action '{req.ActionName}' requires your explicit permission.\nDo you want to proceed?";
                HasPendingConfirmation = true;
            });
        };

        _engine.ErrorOccurred += (_, err) =>
        {
            WpfApp.Current?.Dispatcher.Invoke(() =>
            {
                StatusText = $"Notice: {err}";
            });
        };
    }

    private async Task LoadExistingHistoryAsync()
    {
        try
        {
            var history = await _engine.History.GetHistoryAsync(30);
            WpfApp.Current?.Dispatcher.Invoke(() =>
            {
                Conversation.Clear();
                foreach (var entry in history.Reverse())
                {
                    Conversation.Add(new ConversationBubbleViewModel
                    {
                        Id = entry.Id,
                        Timestamp = entry.Timestamp,
                        UserUtterance = entry.UserUtterance,
                        AssistantResponse = entry.AssistantResponse,
                        ActionName = entry.ActionName,
                        Success = entry.Success,
                        Engine = entry.Engine,
                        RequiresConfirmation = entry.RequiresConfirmation,
                        Confirmed = entry.Confirmed
                    });
                }
            });
        }
        catch { }
    }

    private async Task ToggleListeningAsync()
    {
        if (IsListening)
        {
            await _engine.StopListeningAsync();
        }
        else
        {
            LiveTranscription = "Listening for your voice...";
            await _engine.StartListeningAsync();
        }
    }

    private async Task SendTextInputAsync()
    {
        if (string.IsNullOrWhiteSpace(TextInput))
            return;

        var text = TextInput.Trim();
        TextInput = string.Empty;
        LiveTranscription = $"\"{text}\"";

        await _engine.ProcessUserUtteranceAsync(text);
    }

    private async Task ConfirmPendingActionAsync()
    {
        if (_pendingRequest != null)
        {
            var req = _pendingRequest;
            _pendingRequest = null;
            HasPendingConfirmation = false;
            await _engine.ConfirmAndExecuteAsync(req);
        }
    }

    private void CancelPendingAction()
    {
        _pendingRequest = null;
        HasPendingConfirmation = false;
        StatusText = "Sensitive action cancelled by user.";
    }

    private async Task ClearHistoryAsync()
    {
        await _engine.History.ClearHistoryAsync();
        Conversation.Clear();
        StatusText = "Conversation history cleared.";
    }

    private void OpenSettings()
    {
        var vm = _settingsVmFactory();
        _openSettingsWindow(vm);
    }
}
