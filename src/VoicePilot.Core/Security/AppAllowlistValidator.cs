namespace VoicePilot.Core.Security;

/// <summary>
/// Validates and resolves application launch requests against an approved allowlist.
/// Prevents execution of arbitrary command scripts, cmd.exe, powershell.exe, or unapproved binaries.
/// </summary>
public class AppAllowlistValidator
{
    private readonly Dictionary<string, string> _allowedApps = new(StringComparer.OrdinalIgnoreCase);
    private static readonly HashSet<string> BlockedBinaries = new(StringComparer.OrdinalIgnoreCase)
    {
        "cmd.exe", "powershell.exe", "pwsh.exe", "wscript.exe", "cscript.exe",
        "mshta.exe", "reg.exe", "regedit.exe", "format.com", "vssadmin.exe",
        "certutil.exe", "bitsadmin.exe", "rundll32.exe"
    };

    public AppAllowlistValidator(IDictionary<string, string>? customApps = null)
    {
        // Standard safe Windows productivity applications
        RegisterDefaultApp("notepad", "notepad.exe", "Notepad");
        RegisterDefaultApp("calculator", "calc.exe", "Calculator");
        RegisterDefaultApp("calc", "calc.exe", "Calculator");
        RegisterDefaultApp("paint", "mspaint.exe", "Paint");
        RegisterDefaultApp("explorer", "explorer.exe", "File Explorer");
        RegisterDefaultApp("file explorer", "explorer.exe", "File Explorer");
        RegisterDefaultApp("edge", "msedge.exe", "Microsoft Edge");
        RegisterDefaultApp("browser", "msedge.exe", "Web Browser");
        RegisterDefaultApp("chrome", "chrome.exe", "Google Chrome");
        RegisterDefaultApp("task manager", "taskmgr.exe", "Task Manager");
        RegisterDefaultApp("taskmgr", "taskmgr.exe", "Task Manager");
        RegisterDefaultApp("terminal", "wt.exe", "Windows Terminal");
        RegisterDefaultApp("settings", "ms-settings:", "Windows Settings");
        RegisterDefaultApp("snipping tool", "snippingtool.exe", "Snipping Tool");
        RegisterDefaultApp("wordpad", "write.exe", "WordPad");
        RegisterDefaultApp("clock", "ms-clock:", "Windows Clock");

        if (customApps != null)
        {
            foreach (var kvp in customApps)
            {
                RegisterCustomApp(kvp.Key, kvp.Value);
            }
        }
    }

    private void RegisterDefaultApp(string alias, string executable, string displayName)
    {
        _allowedApps[alias.ToLowerInvariant()] = executable;
    }

    public bool RegisterCustomApp(string alias, string executableOrUri)
    {
        if (string.IsNullOrWhiteSpace(alias) || string.IsNullOrWhiteSpace(executableOrUri))
            return false;

        var fileName = Path.GetFileName(executableOrUri);
        if (BlockedBinaries.Contains(fileName))
            return false;

        _allowedApps[alias.Trim().ToLowerInvariant()] = executableOrUri.Trim();
        return true;
    }

    public IReadOnlyDictionary<string, string> GetAllowedApps() => _allowedApps;

    /// <summary>
    /// Resolves an app alias (e.g. "calculator", "notepad") into an allowlisted target.
    /// Returns false if not allowed or if dangerous binary requested.
    /// </summary>
    public bool TryResolveApp(string appNameOrAlias, out string executableOrProtocol)
    {
        executableOrProtocol = string.Empty;
        if (string.IsNullOrWhiteSpace(appNameOrAlias))
            return false;

        var clean = appNameOrAlias.Trim().ToLowerInvariant();

        // Direct alias lookup
        if (_allowedApps.TryGetValue(clean, out var target))
        {
            var targetName = Path.GetFileName(target);
            if (BlockedBinaries.Contains(targetName))
                return false;

            executableOrProtocol = target;
            return true;
        }

        // Fuzzy alias lookup (e.g. "open the calculator" -> "calculator")
        foreach (var kvp in _allowedApps)
        {
            if (clean.Contains(kvp.Key, StringComparison.OrdinalIgnoreCase))
            {
                var targetName = Path.GetFileName(kvp.Value);
                if (BlockedBinaries.Contains(targetName))
                    return false;

                executableOrProtocol = kvp.Value;
                return true;
            }
        }

        return false;
    }
}
