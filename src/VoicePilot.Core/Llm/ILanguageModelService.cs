using VoicePilot.Core.Automation;
using VoicePilot.Core.Intent;

namespace VoicePilot.Core.Llm;

public interface ILanguageModelService
{
    bool IsConfigured { get; }
    Task<bool> TestConnectionAsync(CancellationToken ct = default);
    Task<IReadOnlyList<string>> GetAvailableModelsAsync(CancellationToken ct = default);
    Task<IntentResult?> InterpretUtteranceAsync(string utterance, IReadOnlyCollection<IAction> availableActions, CancellationToken ct = default);
}
