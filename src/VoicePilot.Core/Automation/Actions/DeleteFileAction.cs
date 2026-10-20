using VoicePilot.Core.Security;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class DeleteFileAction : IAction
{
    private readonly PathSecurityValidator _pathValidator;

    public DeleteFileAction(PathSecurityValidator pathValidator)
    {
        _pathValidator = pathValidator;
    }

    public string Name => "system.delete_file";
    public string Description => "Deletes a specified file in an authorized user directory. Requires explicit user confirmation.";
    public bool RequiresConfirmation => true;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("filePath", typeof(string), true, "The path or filename within authorized user directories to delete")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "delete file notes.txt in documents",
        "delete old_log.txt on desktop"
    };

    public Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        if (!context.Parameters.TryGetValue("filePath", out var pathObj) || pathObj == null)
        {
            return Task.FromResult(ActionResult.Fail("File path is required.", "Please specify the file path you wish to delete."));
        }

        var rawPath = pathObj.ToString()?.Trim() ?? string.Empty;
        if (!_pathValidator.IsPathAllowed(rawPath, out var normalizedPath))
        {
            return Task.FromResult(ActionResult.Fail(
                $"Access denied: '{rawPath}' is outside authorized user directories.",
                "Access denied. You can only delete files inside your authorized user directories."
            ));
        }

        if (!File.Exists(normalizedPath))
        {
            return Task.FromResult(ActionResult.Fail(
                $"File not found: '{normalizedPath}'.",
                $"File '{Path.GetFileName(normalizedPath)}' was not found."
            ));
        }

        // Gate: user confirmation requirement
        if (!context.IsUserConfirmed)
        {
            var fileName = Path.GetFileName(normalizedPath);
            return Task.FromResult(ActionResult.Fail(
                $"Confirmation required to delete: '{normalizedPath}'.",
                $"Deleting '{fileName}' requires your confirmation. Please confirm in the dialog to proceed."
            ));
        }

        try
        {
            File.Delete(normalizedPath);
            var fileName = Path.GetFileName(normalizedPath);
            return Task.FromResult(ActionResult.Ok(
                $"Deleted file '{fileName}'.",
                $"Successfully deleted: {normalizedPath}"
            ));
        }
        catch (Exception ex)
        {
            return Task.FromResult(ActionResult.Fail(
                $"Error deleting file: {ex.Message}",
                "An error occurred while attempting to delete the file."
            ));
        }
    }
}
