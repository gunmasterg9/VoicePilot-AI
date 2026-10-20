using System.Diagnostics;
using VoicePilot.Core.Security;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class LaunchAppAction : IAction
{
    private readonly AppAllowlistValidator _validator;

    public LaunchAppAction(AppAllowlistValidator validator)
    {
        _validator = validator;
    }

    public string Name => "system.launch";
    public string Description => "Launches an approved desktop application safely.";
    public bool RequiresConfirmation => false;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("appName", typeof(string), true, "The name or alias of the application to launch (e.g. 'notepad', 'calculator')")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "open calculator",
        "launch notepad",
        "start file explorer",
        "open task manager"
    };

    public Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        if (!context.Parameters.TryGetValue("appName", out var appObj) || appObj == null)
        {
            return Task.FromResult(ActionResult.Fail("Application name is required.", "Please specify an application to launch."));
        }

        var appName = appObj.ToString()?.Trim() ?? string.Empty;
        if (!_validator.TryResolveApp(appName, out var executableOrProtocol))
        {
            return Task.FromResult(ActionResult.Fail(
                $"Access denied: '{appName}' is not in the approved application allowlist.",
                $"I cannot open '{appName}' because it is not in the approved applications list. You can add it in Settings."
            ));
        }

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = executableOrProtocol,
                UseShellExecute = true
            };
            Process.Start(psi);

            var friendlyName = char.ToUpperInvariant(appName[0]) + (appName.Length > 1 ? appName[1..] : "");
            return Task.FromResult(ActionResult.Ok(
                $"Opened {friendlyName}.",
                $"Successfully launched {friendlyName} ({executableOrProtocol})."
            ));
        }
        catch (Exception ex)
        {
            return Task.FromResult(ActionResult.Fail(
                $"Failed to launch application '{appName}': {ex.Message}",
                $"Sorry, I encountered an error trying to open {appName}."
            ));
        }
    }
}
