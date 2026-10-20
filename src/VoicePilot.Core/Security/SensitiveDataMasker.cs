using System.Text.RegularExpressions;

namespace VoicePilot.Core.Security;

/// <summary>
/// Redacts sensitive information (tokens, keys, passwords, full user credentials) from logs.
/// </summary>
public static class SensitiveDataMasker
{
    private static readonly Regex KeyPattern = new(
        @"(api[-_]?key|secret|password|token|bearer|auth)[\s:=]+([a-zA-Z0-9_\-\.]{8,})",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex EmailPattern = new(
        @"([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})",
        RegexOptions.Compiled);

    public static string Mask(string input)
    {
        if (string.IsNullOrWhiteSpace(input))
            return string.Empty;

        var result = KeyPattern.Replace(input, "$1: [REDACTED]");
        result = EmailPattern.Replace(result, "[$1@***.***]");
        return result;
    }
}
