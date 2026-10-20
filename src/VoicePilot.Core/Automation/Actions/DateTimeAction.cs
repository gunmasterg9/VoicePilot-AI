using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class DateTimeAction : IAction
{
    public string Name => "system.datetime";
    public string Description => "Speaks and displays the current local time, date, or day of the week.";
    public bool RequiresConfirmation => false;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("mode", typeof(string), false, "Mode: 'time', 'date', 'day', or 'full'", "full")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "what time is it",
        "what is the date",
        "what day is today",
        "current time"
    };

    public Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        var now = DateTime.Now;
        var mode = context.Parameters.TryGetValue("mode", out var val) ? val?.ToString()?.ToLowerInvariant() : "full";

        string spoken;
        string display;

        switch (mode)
        {
            case "time":
                spoken = $"It is currently {now:h:mm tt}.";
                display = $"Current Time: {now:h:mm:ss tt}";
                break;
            case "date":
                spoken = $"Today is {now:dddd, MMMM d, yyyy}.";
                display = $"Current Date: {now:D}";
                break;
            case "day":
                spoken = $"Today is {now:dddd}.";
                display = $"Day of Week: {now:dddd}";
                break;
            default:
                spoken = $"It is {now:h:mm tt} on {now:dddd, MMMM d, yyyy}.";
                display = $"Time: {now:h:mm:ss tt} | Date: {now:D}";
                break;
        }

        return Task.FromResult(ActionResult.Ok(spoken, display, now));
    }
}
