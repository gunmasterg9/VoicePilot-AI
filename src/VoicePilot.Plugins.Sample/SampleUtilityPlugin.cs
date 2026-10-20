using VoicePilot.Sdk;

namespace VoicePilot.Plugins.Sample;

public class SampleUtilityPlugin : IPlugin
{
    private IPluginContext? _context;

    public string Id => "com.voicepilot.plugins.sample";
    public string Name => "VoicePilot Sample Utilities Plugin";
    public string Version => "1.0.0";
    public string Description => "Provides weather simulation, local quick notes, and Windows system diagnostic actions.";
    public string Author => "VoicePilot AI Team";

    public Task InitializeAsync(IPluginContext context, CancellationToken ct = default)
    {
        _context = context;
        _context.LogInfo("SampleUtilityPlugin initialized successfully.");
        return Task.CompletedTask;
    }

    public IReadOnlyList<IActionDefinition> GetActions()
    {
        return new List<IActionDefinition>
        {
            new ActionDefinition
            {
                Name = "sample.weather",
                Description = "Provides current weather conditions and forecast.",
                Parameters = new List<ActionParameterDefinition>
                {
                    new("location", typeof(string), false, "Target city or location", "Current Location")
                },
                RequiresConfirmation = false,
                SamplePhrases = new[] { "what is the weather", "check weather report", "current temperature" }
            },
            new ActionDefinition
            {
                Name = "sample.note",
                Description = "Appends a quick voice note to a local file in the plugin's isolated storage.",
                Parameters = new List<ActionParameterDefinition>
                {
                    new("text", typeof(string), true, "Content of the note to record")
                },
                RequiresConfirmation = false,
                SamplePhrases = new[] { "take note buy groceries", "add note review pull request" }
            },
            new ActionDefinition
            {
                Name = "sample.diagnostics",
                Description = "Gathers system performance metrics including memory, processor count, and uptime.",
                Parameters = Array.Empty<ActionParameterDefinition>(),
                RequiresConfirmation = false,
                SamplePhrases = new[] { "system diagnostics", "run diagnostic check" }
            }
        };
    }

    public async Task<ActionResult> ExecuteActionAsync(string actionName, IReadOnlyDictionary<string, object?> parameters, CancellationToken ct = default)
    {
        switch (actionName.ToLowerInvariant())
        {
            case "sample.weather":
                var loc = parameters.TryGetValue("location", out var l) ? l?.ToString() : "Current Location";
                var spoken = $"The weather in {loc} is 72 degrees Fahrenheit and mostly sunny with light winds.";
                var display = $"🌤 Weather for {loc}:\nTemperature: 72°F (22°C)\nConditions: Mostly Sunny\nHumidity: 45%\nWind: 6 mph NW";
                return ActionResult.Ok(spoken, display);

            case "sample.note":
                if (!parameters.TryGetValue("text", out var tObj) || tObj == null)
                {
                    return ActionResult.Fail("Note text is required.", "Please specify what note to save.");
                }
                var noteText = tObj.ToString()?.Trim() ?? string.Empty;
                if (_context != null)
                {
                    var notesPath = Path.Combine(_context.StorageDirectory, "quick_notes.txt");
                    var line = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {noteText}{Environment.NewLine}";
                    await File.AppendAllTextAsync(notesPath, line, ct);
                    return ActionResult.Ok($"Saved your note: \"{noteText}\".", $"Appended note to {notesPath}:\n\"{noteText}\"");
                }
                return ActionResult.Ok($"Noted: \"{noteText}\".", noteText);

            case "sample.diagnostics":
                var mem = GC.GetGCMemoryInfo();
                var uptime = TimeSpan.FromMilliseconds(Environment.TickCount64);
                var diagSpoken = $"System diagnostics: {Environment.ProcessorCount} CPU cores detected, system uptime is {uptime.Days} days and {uptime.Hours} hours.";
                var diagDisplay = $"📊 System Diagnostics Report:\n" +
                                  $"• OS: {Environment.OSVersion}\n" +
                                  $"• Architecture: {(Environment.Is64BitOperatingSystem ? "64-bit" : "32-bit")}\n" +
                                  $"• Logical Processors: {Environment.ProcessorCount}\n" +
                                  $"• System Uptime: {uptime.Days}d {uptime.Hours}h {uptime.Minutes}m\n" +
                                  $"• Managed Memory: {GC.GetTotalMemory(false) / (1024 * 1024):N1} MB\n" +
                                  $"• .NET Runtime: {Environment.Version}";
                return ActionResult.Ok(diagSpoken, diagDisplay);

            default:
                return ActionResult.Fail($"Action '{actionName}' is not supported by {Name}.", "Unsupported plugin action.");
        }
    }

    public Task ShutdownAsync(CancellationToken ct = default)
    {
        _context?.LogInfo("SampleUtilityPlugin shutdown.");
        return Task.CompletedTask;
    }
}
