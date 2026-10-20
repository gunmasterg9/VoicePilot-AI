using VoicePilot.Core.Security;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation;

public record ExecutionRequest(
    string ActionName,
    IReadOnlyDictionary<string, object?> Parameters,
    bool IsConfirmed = false,
    string RawUtterance = ""
);

public record ExecutionResult(
    bool Success,
    string SpokenResponse,
    string DisplayResponse,
    bool RequiresConfirmation,
    ExecutionRequest? PendingRequest = null,
    string? Error = null
);

public class ActionExecutor
{
    private readonly ActionRegistry _registry;

    public ActionExecutor(ActionRegistry registry)
    {
        _registry = registry;
    }

    public async Task<ExecutionResult> ExecuteAsync(ExecutionRequest request, CancellationToken ct = default)
    {
        if (!_registry.TryGetAction(request.ActionName, out var action))
        {
            return new ExecutionResult(
                Success: false,
                SpokenResponse: $"I do not know how to perform the action '{request.ActionName}'.",
                DisplayResponse: $"Unknown action: '{request.ActionName}'.",
                RequiresConfirmation: false,
                Error: "Action not registered."
            );
        }

        // Check if the action requires confirmation and is not yet confirmed
        if (action.RequiresConfirmation && !request.IsConfirmed)
        {
            var prompt = $"Action '{action.Name}' requires confirmation to proceed.";
            return new ExecutionResult(
                Success: false,
                SpokenResponse: prompt,
                DisplayResponse: $"Confirmation Required:\n{action.Description}",
                RequiresConfirmation: true,
                PendingRequest: request,
                Error: null
            );
        }

        // Validate required parameters
        foreach (var pDef in action.Parameters.Where(p => p.IsRequired))
        {
            if (!request.Parameters.ContainsKey(pDef.Name) || request.Parameters[pDef.Name] == null)
            {
                return new ExecutionResult(
                    Success: false,
                    SpokenResponse: $"Missing required parameter '{pDef.Name}' for {action.Name}.",
                    DisplayResponse: $"Missing required parameter: {pDef.Name} ({pDef.Description})",
                    RequiresConfirmation: false,
                    Error: "Missing parameter"
                );
            }
        }

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(15)); // 15-second safety timeout

        try
        {
            var actionContext = new ActionContext(request.Parameters, request.IsConfirmed, request.RawUtterance);
            var result = await action.ExecuteAsync(actionContext, cts.Token);

            return new ExecutionResult(
                Success: result.Success,
                SpokenResponse: result.SpokenResponse,
                DisplayResponse: result.DisplayResponse,
                RequiresConfirmation: false,
                Error: result.ErrorMessage
            );
        }
        catch (OperationCanceledException)
        {
            return new ExecutionResult(
                Success: false,
                SpokenResponse: "The action timed out.",
                DisplayResponse: "Action execution timed out after 15 seconds.",
                RequiresConfirmation: false,
                Error: "Timeout"
            );
        }
        catch (Exception ex)
        {
            var maskedMsg = SensitiveDataMasker.Mask(ex.Message);
            return new ExecutionResult(
                Success: false,
                SpokenResponse: "An error occurred while executing the action.",
                DisplayResponse: $"Execution error: {maskedMsg}",
                RequiresConfirmation: false,
                Error: maskedMsg
            );
        }
    }
}
