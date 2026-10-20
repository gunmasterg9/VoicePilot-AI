namespace VoicePilot.Sdk;

/// <summary>
/// Contract implemented by VoicePilot extension plugins.
/// </summary>
public interface IPlugin
{
    /// <summary>
    /// Unique identifier for the plugin (e.g. "com.voicepilot.sample").
    /// </summary>
    string Id { get; }

    /// <summary>
    /// Human-readable display name of the plugin.
    /// </summary>
    string Name { get; }

    /// <summary>
    /// Semantic version of the plugin.
    /// </summary>
    string Version { get; }

    /// <summary>
    /// Brief explanation of plugin functionality.
    /// </summary>
    string Description { get; }

    /// <summary>
    /// Author or organization maintaining the plugin.
    /// </summary>
    string Author { get; }

    /// <summary>
    /// Called once during startup when the plugin is loaded into the host.
    /// </summary>
    Task InitializeAsync(IPluginContext context, CancellationToken ct = default);

    /// <summary>
    /// Returns action definitions provided by this plugin.
    /// </summary>
    IReadOnlyList<IActionDefinition> GetActions();

    /// <summary>
    /// Executes a registered action provided by this plugin.
    /// </summary>
    Task<ActionResult> ExecuteActionAsync(string actionName, IReadOnlyDictionary<string, object?> parameters, CancellationToken ct = default);

    /// <summary>
    /// Called when the host unloads the plugin or shuts down.
    /// </summary>
    Task ShutdownAsync(CancellationToken ct = default);
}
