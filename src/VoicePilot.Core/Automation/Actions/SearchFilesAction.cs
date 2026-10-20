using VoicePilot.Core.Security;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class SearchFilesAction : IAction
{
    private readonly PathSecurityValidator _pathValidator;

    public SearchFilesAction(PathSecurityValidator pathValidator)
    {
        _pathValidator = pathValidator;
    }

    public string Name => "system.search_files";
    public string Description => "Searches for files matching a query or pattern within approved directories.";
    public bool RequiresConfirmation => false;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("query", typeof(string), true, "File name keyword or pattern (e.g. 'report', '*.pdf')"),
        new("folder", typeof(string), false, "Search folder ('documents', 'downloads', 'desktop')", "documents")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "search files for project",
        "find notes in documents",
        "search downloads for installer",
        "find pdf files"
    };

    public async Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        if (!context.Parameters.TryGetValue("query", out var queryObj) || queryObj == null)
        {
            return ActionResult.Fail("Search query is required.", "Please tell me what file you are looking for.");
        }

        var query = queryObj.ToString()?.Trim() ?? string.Empty;
        var folderParam = context.Parameters.TryGetValue("folder", out var fVal) ? fVal?.ToString() : "documents";

        var searchDir = ResolveSearchDirectory(folderParam);
        if (!_pathValidator.IsPathAllowed(searchDir, out var normalizedDir))
        {
            return ActionResult.Fail("Search directory is restricted.", "That directory is restricted.");
        }

        if (!Directory.Exists(normalizedDir))
        {
            return ActionResult.Fail($"Directory '{normalizedDir}' does not exist.", "The specified directory does not exist.");
        }

        try
        {
            var pattern = query.Contains('*') || query.Contains('?') ? query : $"*{query}*";
            var results = await Task.Run(() =>
            {
                var matches = new List<string>();
                var dirInfo = new DirectoryInfo(normalizedDir);
                try
                {
                    // Search top directory and one level of subdirectories for speed
                    var files = dirInfo.EnumerateFiles(pattern, new EnumerationOptions
                    {
                        IgnoreInaccessible = true,
                        RecurseSubdirectories = true,
                        MaxRecursionDepth = 2
                    }).Take(6).ToList();

                    matches.AddRange(files.Select(f => f.FullName));
                }
                catch
                {
                    // Catch IO permission errors
                }
                return matches;
            }, ct);

            if (results.Count == 0)
            {
                return ActionResult.Ok(
                    $"I could not find any files matching '{query}' in {Path.GetFileName(normalizedDir)}.",
                    $"No files matching '{query}' found in '{normalizedDir}'.",
                    results
                );
            }

            var spoken = $"Found {results.Count} matching file{(results.Count == 1 ? "" : "s")} for '{query}'.";
            var display = $"Found {results.Count} result(s):\n" + string.Join("\n", results.Select(r => $"• {Path.GetFileName(r)} ({r})"));

            return ActionResult.Ok(spoken, display, results);
        }
        catch (Exception ex)
        {
            return ActionResult.Fail($"Search error: {ex.Message}", "An error occurred while searching for files.");
        }
    }

    private static string ResolveSearchDirectory(string? folder)
    {
        var clean = folder?.ToLowerInvariant().Trim() ?? "documents";
        if (clean.Contains("download"))
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
        if (clean.Contains("desktop"))
            return Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
        if (clean.Contains("picture"))
            return Environment.GetFolderPath(Environment.SpecialFolder.MyPictures);

        return Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
    }
}
