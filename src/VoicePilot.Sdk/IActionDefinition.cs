namespace VoicePilot.Sdk;

/// <summary>
/// Parameter metadata required or optional for executing an action.
/// </summary>
public record ActionParameterDefinition(
    string Name,
    Type ParameterType,
    bool IsRequired,
    string Description,
    object? DefaultValue = null
);

/// <summary>
/// Metadata describing a supported action exposed by a plugin or built-in system.
/// </summary>
public interface IActionDefinition
{
    /// <summary>
    /// Unique action verb/identifier (e.g. "sample.weather", "system.launch").
    /// </summary>
    string Name { get; }

    /// <summary>
    /// Friendly explanation of the action's behavior.
    /// </summary>
    string Description { get; }

    /// <summary>
    /// List of parameter specifications.
    /// </summary>
    IReadOnlyList<ActionParameterDefinition> Parameters { get; }

    /// <summary>
    /// If true, the action modifies the system, deletes files, or carries risk and requires user confirmation.
    /// </summary>
    bool RequiresConfirmation { get; }

    /// <summary>
    /// Sample phrases or command examples that activate this action.
    /// </summary>
    IReadOnlyList<string> SamplePhrases { get; }
}

/// <summary>
/// Standard implementation of IActionDefinition.
/// </summary>
public class ActionDefinition : IActionDefinition
{
    public string Name { get; init; } = string.Empty;
    public string Description { get; init; } = string.Empty;
    public IReadOnlyList<ActionParameterDefinition> Parameters { get; init; } = Array.Empty<ActionParameterDefinition>();
    public bool RequiresConfirmation { get; init; }
    public IReadOnlyList<string> SamplePhrases { get; init; } = Array.Empty<string>();
}
