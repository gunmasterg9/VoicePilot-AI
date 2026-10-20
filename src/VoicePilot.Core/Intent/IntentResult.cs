namespace VoicePilot.Core.Intent;

public record IntentResult
{
    public bool Recognized { get; init; }
    public string ActionName { get; init; } = string.Empty;
    public Dictionary<string, object?> Parameters { get; init; } = new();
    public string? SuggestedResponse { get; init; }
    public string ParserEngine { get; init; } = "Unknown";
    public double Confidence { get; init; } = 1.0;

    public static IntentResult Match(string actionName, Dictionary<string, object?> parameters, string? suggestedResponse = null, string engine = "RuleBased", double confidence = 1.0)
    {
        return new IntentResult
        {
            Recognized = true,
            ActionName = actionName,
            Parameters = parameters,
            SuggestedResponse = suggestedResponse,
            ParserEngine = engine,
            Confidence = confidence
        };
    }

    public static IntentResult Unrecognized(string rawUtterance, string engine = "RuleBased")
    {
        return new IntentResult
        {
            Recognized = false,
            ActionName = string.Empty,
            Parameters = new Dictionary<string, object?> { ["raw"] = rawUtterance },
            SuggestedResponse = "I'm sorry, I didn't understand that command. Say 'help' to see what I can do.",
            ParserEngine = engine,
            Confidence = 0.0
        };
    }
}

public interface IIntentParser
{
    Task<IntentResult> ParseIntentAsync(string utterance, CancellationToken ct = default);
}
