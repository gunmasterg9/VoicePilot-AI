namespace VoicePilot.Core.Security;

/// <summary>
/// Enforces path safety to ensure VoicePilot actions only access approved user directories.
/// Rejects path traversal attempts, Windows system directories, and unauthorized drives.
/// </summary>
public class PathSecurityValidator
{
    private readonly HashSet<string> _allowedDirectories = new(StringComparer.OrdinalIgnoreCase);

    public PathSecurityValidator(IEnumerable<string>? customAllowedDirs = null)
    {
        // Add standard safe user directories
        AddSafeDirectory(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments));
        AddSafeDirectory(Environment.GetFolderPath(Environment.SpecialFolder.Desktop));
        AddSafeDirectory(Environment.GetFolderPath(Environment.SpecialFolder.MyPictures));
        AddSafeDirectory(Environment.GetFolderPath(Environment.SpecialFolder.MyMusic));
        AddSafeDirectory(Environment.GetFolderPath(Environment.SpecialFolder.MyVideos));
        
        var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (!string.IsNullOrEmpty(userProfile))
        {
            var downloads = Path.Combine(userProfile, "Downloads");
            if (Directory.Exists(downloads))
                AddSafeDirectory(downloads);
        }

        if (customAllowedDirs != null)
        {
            foreach (var dir in customAllowedDirs)
            {
                AddSafeDirectory(dir);
            }
        }
    }

    public void AddSafeDirectory(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
            return;

        try
        {
            var fullPath = Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            if (IsSystemRestrictedDirectory(fullPath))
                return; // Prohibit adding C:\Windows, C:\Windows\System32, etc.

            _allowedDirectories.Add(fullPath);
        }
        catch
        {
            // Ignore malformed path
        }
    }

    public IReadOnlyCollection<string> GetAllowedDirectories() => _allowedDirectories.ToList().AsReadOnly();

    /// <summary>
    /// Validates whether a file or directory path is safe to access/open/modify.
    /// </summary>
    public bool IsPathAllowed(string targetPath, out string normalizedPath)
    {
        normalizedPath = string.Empty;
        if (string.IsNullOrWhiteSpace(targetPath))
            return false;

        try
        {
            // Strip harmful quote marks or whitespace
            targetPath = targetPath.Trim('\"', '\'', ' ');

            // Check for obvious traversal tokens
            if (targetPath.Contains(".."))
            {
                var full = Path.GetFullPath(targetPath);
                targetPath = full;
            }

            var canonicalPath = Path.GetFullPath(targetPath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

            // Recheck system restricted directories
            if (IsSystemRestrictedDirectory(canonicalPath))
                return false;

            // Must fall under one of the allowed directories
            foreach (var allowed in _allowedDirectories)
            {
                if (canonicalPath.Equals(allowed, StringComparison.OrdinalIgnoreCase) ||
                    canonicalPath.StartsWith(allowed + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                {
                    normalizedPath = canonicalPath;
                    return true;
                }
            }

            return false;
        }
        catch
        {
            return false;
        }
    }

    private static bool IsSystemRestrictedDirectory(string path)
    {
        var winDir = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        var sysDir = Environment.GetFolderPath(Environment.SpecialFolder.System);
        var progFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        var progFilesX86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);

        if (!string.IsNullOrEmpty(winDir) && path.StartsWith(winDir, StringComparison.OrdinalIgnoreCase))
            return true;
        if (!string.IsNullOrEmpty(sysDir) && path.StartsWith(sysDir, StringComparison.OrdinalIgnoreCase))
            return true;

        // Prohibit direct root volume tampering (e.g. "C:\", "D:\")
        var root = Path.GetPathRoot(path);
        if (string.Equals(root?.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar), path, StringComparison.OrdinalIgnoreCase))
            return true;

        return false;
    }
}
