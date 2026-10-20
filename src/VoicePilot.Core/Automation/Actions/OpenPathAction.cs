using System.Diagnostics;
using VoicePilot.Core.Security;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class OpenPathAction : IAction
{
    private readonly PathSecurityValidator _pathValidator;

    public OpenPathAction(PathSecurityValidator pathValidator)
    {
        _pathValidator = pathValidator;
    }

    public string Name => "system.open_path";
    public string Description => "Opens an approved directory or document in File Explorer.";
    public bool RequiresConfirmation => false;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("target", typeof(string), true, "Folder alias ('documents', 'downloads', 'desktop') or approved path")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "open documents folder",
        "open downloads",
        "open my desktop",
        "show pictures"
    };

    public Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        if (!context.Parameters.TryGetValue("target", out var targetObj) || targetObj == null)
        {
            return Task.FromResult(ActionResult.Fail("Target folder or file path is required.", "Please specify a folder to open."));
        }

        var target = targetObj.ToString()?.Trim() ?? string.Empty;
        var resolvedPath = ResolveTargetAlias(target);

        if (!_pathValidator.IsPathAllowed(resolvedPath, out var normalizedPath))
        {
            return Task.FromResult(ActionResult.Fail(
                $"Access denied: '{resolvedPath}' is outside authorized user directories.",
                "Access denied. That folder is outside your authorized user directories."
            ));
        }

        if (!Directory.Exists(normalizedPath) && !File.Exists(normalizedPath))
        {
            return Task.FromResult(ActionResult.Fail(
                $"Path not found: '{normalizedPath}'.",
                $"I could not find the folder or file at {Path.GetFileName(normalizedPath)}."
            ));
        }

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "explorer.exe",
                Arguments = normalizedPath,
                UseShellExecute = true
            };
            Process.Start(psi);

            var friendly = Path.GetFileName(normalizedPath);
            if (string.IsNullOrEmpty(friendly))
                friendly = normalizedPath;

            return Task.FromResult(ActionResult.Ok(
                $"Opened {friendly} in File Explorer.",
                $"Opened '{normalizedPath}'."
            ));
        }
        catch (Exception ex)
        {
            return Task.FromResult(ActionResult.Fail(
                $"Error opening path: {ex.Message}",
                "Sorry, an error occurred opening File Explorer."
            ));
        }
    }

    private static string ResolveTargetAlias(string target)
    {
        var clean = target.ToLowerInvariant().Trim();
        if (clean.Contains("document"))
            return Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        if (clean.Contains("download"))
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
        if (clean.Contains("desktop"))
            return Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
        if (clean.Contains("picture") || clean.Contains("photo"))
            return Environment.GetFolderPath(Environment.SpecialFolder.MyPictures);
        if (clean.Contains("music"))
            return Environment.GetFolderPath(Environment.SpecialFolder.MyMusic);
        if (clean.Contains("video"))
            return Environment.GetFolderPath(Environment.SpecialFolder.MyVideos);

        return target;
    }
}
