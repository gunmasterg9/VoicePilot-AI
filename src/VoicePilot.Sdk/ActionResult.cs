namespace VoicePilot.Sdk;

/// <summary>
/// Encapsulates the execution result of an automated command or plugin action.
/// </summary>
public record ActionResult
{
    public bool Success { get; init; }
    public string SpokenResponse { get; init; } = string.Empty;
    public string DisplayResponse { get; init; } = string.Empty;
    public object? Data { get; init; }
    public string? ErrorMessage { get; init; }

    public static ActionResult Ok(string spokenResponse, string? displayResponse = null, object? data = null)
    {
        return new ActionResult
        {
            Success = true,
            SpokenResponse = spokenResponse,
            DisplayResponse = displayResponse ?? spokenResponse,
            Data = data,
            ErrorMessage = null
        };
    }

    public static ActionResult Fail(string errorMessage, string? spokenResponse = null)
    {
        return new ActionResult
        {
            Success = false,
            SpokenResponse = spokenResponse ?? errorMessage,
            DisplayResponse = errorMessage,
            Data = null,
            ErrorMessage = errorMessage
        };
    }
}
