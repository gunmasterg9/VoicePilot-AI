using VoicePilot.Core.Audio;
using VoicePilot.Core.Automation;
using VoicePilot.Core.Configuration;
using VoicePilot.Core.Intent;
using VoicePilot.Core.Llm;
using VoicePilot.Core.Storage;
using VoicePilot.Core.Synthesis;
using VoicePilot.Sdk;

namespace VoicePilot.Core;

public class AssistantEngine : IDisposable
{
    private readonly SettingsManager _settingsManager;
    private readonly ISpeechRecognitionService _speechRecognition;
    private readonly ISpeechSynthesisService _speechSynthesis;
    private readonly IIntentParser _ruleIntentParser;
    private readonly ILanguageModelService _llmService;
    private readonly ActionRegistry _actionRegistry;
    private readonly ActionExecutor _actionExecutor;
    private readonly IConversationHistoryStore _historyStore;

    private readonly SemaphoreSlim _turnLock = new(1, 1);
    private CancellationTokenSource? _currentTurnCts;

    public event EventHandler<string>? LiveTranscriptionChanged;
    public event EventHandler<ConversationEntry>? TurnCompleted;
    public event EventHandler<ExecutionRequest>? ConfirmationRequested;
    public event EventHandler<string>? StatusChanged;
    public event EventHandler<float>? AudioLevelUpdated;
    public event EventHandler<string>? ErrorOccurred;

    public SettingsManager Settings => _settingsManager;
    public ISpeechRecognitionService Recognition => _speechRecognition;
    public ISpeechSynthesisService Synthesis => _speechSynthesis;
    public ActionRegistry Registry => _actionRegistry;
    public IConversationHistoryStore History => _historyStore;

    public AssistantEngine(
        SettingsManager settingsManager,
        ISpeechRecognitionService speechRecognition,
        ISpeechSynthesisService speechSynthesis,
        IIntentParser ruleIntentParser,
        ILanguageModelService llmService,
        ActionRegistry actionRegistry,
        ActionExecutor actionExecutor,
        IConversationHistoryStore historyStore)
    {
        _settingsManager = settingsManager;
        _speechRecognition = speechRecognition;
        _speechSynthesis = speechSynthesis;
        _ruleIntentParser = ruleIntentParser;
        _llmService = llmService;
        _actionRegistry = actionRegistry;
        _actionExecutor = actionExecutor;
        _historyStore = historyStore;

        _speechRecognition.SpeechHypothesized += (_, text) => LiveTranscriptionChanged?.Invoke(this, text);
        _speechRecognition.SpeechRecognized += async (_, text) => await ProcessUserUtteranceAsync(text);
        _speechRecognition.AudioLevelChanged += (_, lvl) => AudioLevelUpdated?.Invoke(this, lvl);
        _speechRecognition.StatusMessageChanged += (_, msg) => StatusChanged?.Invoke(this, msg);
        _speechRecognition.ErrorOccurred += (_, err) => ErrorOccurred?.Invoke(this, err);
    }

    public async Task StartListeningAsync(CancellationToken ct = default)
    {
        _speechSynthesis.StopSpeaking();
        await _speechRecognition.StartListeningAsync(ct);
    }

    public async Task StopListeningAsync(CancellationToken ct = default)
    {
        await _speechRecognition.StopListeningAsync(ct);
    }

    public void CancelCurrentOperation()
    {
        _currentTurnCts?.Cancel();
        _speechRecognition.StopListeningAsync();
        _speechSynthesis.StopSpeaking();
        StatusChanged?.Invoke(this, "Operation cancelled.");
    }

    /// <summary>
    /// Processes a spoken or typed utterance through the entire voice assistant pipeline.
    /// </summary>
    public async Task<ExecutionResult> ProcessUserUtteranceAsync(string utterance, bool isConfirmed = false, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(utterance))
            return new ExecutionResult(false, "", "", false, null, "Empty utterance.");

        await _turnLock.WaitAsync(ct);
        _currentTurnCts = new CancellationTokenSource();
        using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(ct, _currentTurnCts.Token);

        try
        {
            // Stop listening while processing
            await _speechRecognition.StopListeningAsync(linkedCts.Token);
            StatusChanged?.Invoke(this, "Interpreting request...");

            // 1. Intent interpretation
            IntentResult? intent = null;
            if (_settingsManager.Current.OllamaEnabled)
            {
                StatusChanged?.Invoke(this, "Consulting local Ollama model...");
                intent = await _llmService.InterpretUtteranceAsync(utterance, _actionRegistry.GetAllActions(), linkedCts.Token);
            }

            // Fallback to rule-based engine if Ollama is disabled, offline, or couldn't resolve
            if (intent == null || !intent.Recognized)
            {
                StatusChanged?.Invoke(this, "Matching local command patterns...");
                intent = await _ruleIntentParser.ParseIntentAsync(utterance, linkedCts.Token);
            }

            // 2. Unrecognized fallback
            if (!intent.Recognized || string.IsNullOrEmpty(intent.ActionName))
            {
                var unrecText = intent.SuggestedResponse ?? "I'm sorry, I didn't recognize that command. Try 'what time is it', 'open calculator', or say 'help'.";
                StatusChanged?.Invoke(this, "Command not recognized.");
                await _speechSynthesis.SpeakAsync(unrecText, linkedCts.Token);

                var entry = new ConversationEntry
                {
                    UserUtterance = utterance,
                    AssistantResponse = unrecText,
                    ActionName = null,
                    Success = false,
                    Engine = intent.ParserEngine
                };
                await _historyStore.AddEntryAsync(entry, linkedCts.Token);
                TurnCompleted?.Invoke(this, entry);

                return new ExecutionResult(false, unrecText, unrecText, false, null, "Unrecognized command.");
            }

            // 3. Execution dispatch
            StatusChanged?.Invoke(this, $"Executing action: {intent.ActionName}...");
            var execReq = new ExecutionRequest(intent.ActionName, intent.Parameters, isConfirmed, utterance);
            var execResult = await _actionExecutor.ExecuteAsync(execReq, linkedCts.Token);

            if (execResult.RequiresConfirmation)
            {
                StatusChanged?.Invoke(this, "Confirmation required.");
                await _speechSynthesis.SpeakAsync(execResult.SpokenResponse, linkedCts.Token);
                ConfirmationRequested?.Invoke(this, execResult.PendingRequest!);

                var confirmEntry = new ConversationEntry
                {
                    UserUtterance = utterance,
                    AssistantResponse = execResult.DisplayResponse,
                    ActionName = intent.ActionName,
                    Success = false,
                    Engine = intent.ParserEngine,
                    RequiresConfirmation = true,
                    Confirmed = null
                };
                await _historyStore.AddEntryAsync(confirmEntry, linkedCts.Token);
                TurnCompleted?.Invoke(this, confirmEntry);

                return execResult;
            }

            // 4. Output response
            StatusChanged?.Invoke(this, execResult.Success ? "Action executed successfully." : "Action failed.");
            if (!string.IsNullOrEmpty(execResult.SpokenResponse))
            {
                await _speechSynthesis.SpeakAsync(execResult.SpokenResponse, linkedCts.Token);
            }

            var logEntry = new ConversationEntry
            {
                UserUtterance = utterance,
                AssistantResponse = execResult.DisplayResponse,
                ActionName = intent.ActionName,
                Success = execResult.Success,
                Engine = intent.ParserEngine,
                RequiresConfirmation = isConfirmed,
                Confirmed = isConfirmed ? true : null
            };
            await _historyStore.AddEntryAsync(logEntry, linkedCts.Token);
            TurnCompleted?.Invoke(this, logEntry);

            return execResult;
        }
        catch (OperationCanceledException)
        {
            StatusChanged?.Invoke(this, "Cancelled.");
            return new ExecutionResult(false, "Cancelled.", "Cancelled.", false, null, "Cancelled");
        }
        catch (Exception ex)
        {
            var err = $"Error: {ex.Message}";
            StatusChanged?.Invoke(this, err);
            ErrorOccurred?.Invoke(this, err);
            return new ExecutionResult(false, "An unexpected error occurred.", err, false, null, ex.Message);
        }
        finally
        {
            _currentTurnCts?.Dispose();
            _currentTurnCts = null;
            _turnLock.Release();
        }
    }

    public async Task ConfirmAndExecuteAsync(ExecutionRequest request, CancellationToken ct = default)
    {
        var confirmedRequest = request with { IsConfirmed = true };
        await ProcessUserUtteranceAsync(confirmedRequest.RawUtterance, isConfirmed: true, ct: ct);
    }

    public void Dispose()
    {
        _currentTurnCts?.Cancel();
        _currentTurnCts?.Dispose();
        _speechRecognition.Dispose();
        _speechSynthesis.Dispose();
        _turnLock.Dispose();
        GC.SuppressFinalize(this);
    }
}
