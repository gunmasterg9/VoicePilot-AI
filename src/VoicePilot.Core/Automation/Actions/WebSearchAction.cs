using System.Diagnostics;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class WebSearchAction : IAction
{
    public string Name => "system.web_search";
    public string Description => "Safely searches the web using your default browser.";
    public bool RequiresConfirmation => false;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("query", typeof(string), true, "The search term or question")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "search the web for dotnet documentation",
        "google weather forecast",
        "search online for windows hotkeys"
    };

    public Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        if (!context.Parameters.TryGetValue("query", out var queryObj) || queryObj == null)
        {
            return Task.FromResult(ActionResult.Fail("Search query is required.", "Please specify what you would like to search for."));
        }

        var query = queryObj.ToString()?.Trim() ?? string.Empty;
        var encoded = Uri.EscapeDataString(query);
        var targetUrl = $"https://duckduckgo.com/?q={encoded}";

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = targetUrl,
                UseShellExecute = true
            };
            Process.Start(psi);

            return Task.FromResult(ActionResult.Ok(
                $"Searching the web for '{query}'.",
                $"Opened web search for: \"{query}\"\nURL: {targetUrl}"
            ));
        }
        catch (Exception ex)
        {
            return Task.FromResult(ActionResult.Fail($"Web search error: {ex.Message}", "Could not open browser for web search."));
        }
    }
}
