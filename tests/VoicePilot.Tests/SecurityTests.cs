using VoicePilot.Core.Security;
using Xunit;

namespace VoicePilot.Tests;

public class SecurityTests
{
    [Fact]
    public void SensitiveDataMasker_ShouldRedactApiKeyAndPassword()
    {
        var input = "Sending request with api_key: AIzaSyD982348df8234 and password=SuperSecretPassword123!";
        var masked = SensitiveDataMasker.Mask(input);

        Assert.DoesNotContain("AIzaSyD982348df8234", masked);
        Assert.DoesNotContain("SuperSecretPassword123!", masked);
        Assert.Contains("[REDACTED]", masked);
    }

    [Fact]
    public void PathSecurityValidator_ShouldAllowSafeUserFolders()
    {
        var validator = new PathSecurityValidator();
        var docs = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        var testPath = Path.Combine(docs, "test.txt");

        var allowed = validator.IsPathAllowed(testPath, out var normalized);

        Assert.True(allowed);
        Assert.Equal(Path.GetFullPath(testPath), normalized);
    }

    [Fact]
    public void PathSecurityValidator_ShouldRejectSystemWindowsDirectory()
    {
        var validator = new PathSecurityValidator();
        var winDir = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        var testPath = Path.Combine(winDir, "System32", "calc.exe");

        var allowed = validator.IsPathAllowed(testPath, out _);

        Assert.False(allowed);
    }

    [Fact]
    public void PathSecurityValidator_ShouldRejectDirectoryTraversal()
    {
        var validator = new PathSecurityValidator();
        var docs = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        var traversalPath = Path.Combine(docs, "..", "..", "Windows", "System32", "cmd.exe");

        var allowed = validator.IsPathAllowed(traversalPath, out _);

        Assert.False(allowed);
    }

    [Fact]
    public void AppAllowlistValidator_ShouldAllowApprovedApps()
    {
        var validator = new AppAllowlistValidator();

        Assert.True(validator.TryResolveApp("calculator", out var calcExe));
        Assert.Equal("calc.exe", calcExe);

        Assert.True(validator.TryResolveApp("notepad", out var noteExe));
        Assert.Equal("notepad.exe", noteExe);
    }

    [Fact]
    public void AppAllowlistValidator_ShouldRejectShellAndDangerousBinaries()
    {
        var validator = new AppAllowlistValidator();

        Assert.False(validator.TryResolveApp("cmd.exe", out _));
        Assert.False(validator.TryResolveApp("powershell.exe", out _));
        Assert.False(validator.TryResolveApp("format.com", out _));
        Assert.False(validator.TryResolveApp("regedit.exe", out _));
    }
}
