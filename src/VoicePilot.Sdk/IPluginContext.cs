namespace VoicePilot.Sdk;

/// <summary>
/// Execution environment services provided to a plugin by the host application.
/// </summary>
public interface IPluginContext
{
    /// <summary>
    /// Safe isolated directory where the plugin may persist its local data or configuration.
    /// </summary>
    string StorageDirectory { get; }

    /// <summary>
    /// Log an informational message with host logging policies applied.
    /// </summary>
    void LogInfo(string message);

    /// <summary>
    /// Log a warning message.
    /// </summary>
    void LogWarning(string message);

    /// <summary>
    /// Log an error with an optional exception.
    /// </summary>
    void LogError(string message, Exception? ex = null);
}
