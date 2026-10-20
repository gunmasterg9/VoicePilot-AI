namespace VoicePilot.App.ViewModels;

public class ConversationBubbleViewModel : ViewModelBase
{
    private bool? _confirmed;

    public Guid Id { get; init; } = Guid.NewGuid();
    public DateTimeOffset Timestamp { get; init; } = DateTimeOffset.Now;
    public string UserUtterance { get; init; } = string.Empty;
    public string AssistantResponse { get; init; } = string.Empty;
    public string? ActionName { get; init; }
    public bool Success { get; init; } = true;
    public string Engine { get; init; } = "Local";
    public bool RequiresConfirmation { get; init; }

    public bool? Confirmed
    {
        get => _confirmed;
        set => SetProperty(ref _confirmed, value);
    }

    public string TimeFormatted => Timestamp.LocalDateTime.ToString("h:mm tt");
    public bool HasAction => !string.IsNullOrEmpty(ActionName);
}
