namespace VoicePilot.Core.Storage;

/// <summary>
/// Represents a logged conversation turn between the user and VoicePilot AI.
/// </summary>
public record ConversationEntry
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public DateTimeOffset Timestamp { get; init; } = DateTimeOffset.Now;
    public string UserUtterance { get; init; } = string.Empty;
    public string AssistantResponse { get; init; } = string.Empty;
    public string? ActionName { get; init; }
    public bool Success { get; init; } = true;
    public string Engine { get; init; } = "Local";
    public bool RequiresConfirmation { get; init; }
    public bool? Confirmed { get; init; }
}

public interface IConversationHistoryStore
{
    Task<IReadOnlyList<ConversationEntry>> GetHistoryAsync(int maxCount = 50, CancellationToken ct = default);
    Task AddEntryAsync(ConversationEntry entry, CancellationToken ct = default);
    Task ClearHistoryAsync(CancellationToken ct = default);
    Task UpdateEntryConfirmationAsync(Guid entryId, bool confirmed, CancellationToken ct = default);
}
