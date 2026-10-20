using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation;

/// <summary>
/// Runtime context passed to an action execution request.
/// </summary>
public record ActionContext(
    IReadOnlyDictionary<string, object?> Parameters,
    bool IsUserConfirmed = false,
    string RawUtterance = ""
);

/// <summary>
/// Interface implemented by all typed automation actions.
/// </summary>
public interface IAction
{
    string Name { get; }
    string Description { get; }
    bool RequiresConfirmation { get; }
    IReadOnlyList<ActionParameterDefinition> Parameters { get; }
    IReadOnlyList<string> SamplePhrases { get; }

    Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default);
}
