using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using VoicePilot.Core.Automation;
using VoicePilot.Core.Configuration;
using VoicePilot.Core.Intent;
using VoicePilot.Core.Security;

namespace VoicePilot.Core.Llm;

public class OllamaLanguageModelService : ILanguageModelService
{
    private readonly SettingsManager _settingsManager;
    private readonly HttpClient _httpClient;
    private readonly JsonSerializerOptions _jsonOptions;

    public bool IsConfigured => _settingsManager.Current.OllamaEnabled;

    public OllamaLanguageModelService(SettingsManager settingsManager, HttpClient? httpClient = null)
    {
        _settingsManager = settingsManager;
        _httpClient = httpClient ?? new HttpClient();
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
        };
    }

    public async Task<bool> TestConnectionAsync(CancellationToken ct = default)
    {
        try
        {
            var endpoint = _settingsManager.Current.OllamaEndpoint.TrimEnd('/');
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromSeconds(3));

            var res = await _httpClient.GetAsync($"{endpoint}/api/tags", cts.Token);
            return res.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<IReadOnlyList<string>> GetAvailableModelsAsync(CancellationToken ct = default)
    {
        var models = new List<string>();
        try
        {
            var endpoint = _settingsManager.Current.OllamaEndpoint.TrimEnd('/');
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(TimeSpan.FromSeconds(4));

            var response = await _httpClient.GetFromJsonAsync<OllamaTagsResponse>($"{endpoint}/api/tags", _jsonOptions, cts.Token);
            if (response?.Models != null)
            {
                models.AddRange(response.Models.Select(m => m.Name));
            }
        }
        catch
        {
            // Ignore offline errors
        }
        return models;
    }

    public async Task<IntentResult?> InterpretUtteranceAsync(string utterance, IReadOnlyCollection<IAction> availableActions, CancellationToken ct = default)
    {
        if (!IsConfigured || string.IsNullOrWhiteSpace(utterance))
            return null;

        var endpoint = _settingsManager.Current.OllamaEndpoint.TrimEnd('/');
        var modelName = _settingsManager.Current.OllamaModel;
        var timeoutSec = _settingsManager.Current.OllamaTimeoutSeconds;

        var actionsSummary = string.Join("\n", availableActions.Select(a =>
        {
            var paramDesc = string.Join(", ", a.Parameters.Select(p => $"{p.Name}: {p.ParameterType.Name} (required={p.IsRequired})"));
            return $"- Action: \"{a.Name}\" | Description: {a.Description} | Parameters: [{paramDesc}]";
        }));

        var systemPrompt =
            "You are VoicePilot AI, an offline Windows voice assistant.\n" +
            "Your job is to convert spoken natural language requests into typed structured actions.\n" +
            "You MUST ONLY use actions from the following list:\n" +
            actionsSummary + "\n\n" +
            "Rules:\n" +
            "1. Output ONLY a valid single JSON object. No explanations or markdown.\n" +
            "2. Format: {\"action\": \"system.launch\", \"parameters\": {\"appName\": \"notepad\"}, \"reply\": \"Opening Notepad.\"}\n" +
            "3. If no action applies, set \"action\": \"\" and provide a helpful voice reply in \"reply\".\n" +
            "4. NEVER invent action names or output raw shell commands.";

        var requestBody = new
        {
            model = modelName,
            stream = false,
            format = "json",
            messages = new[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user", content = utterance }
            }
        };

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(timeoutSec));

        try
        {
            var response = await _httpClient.PostAsJsonAsync($"{endpoint}/api/chat", requestBody, cts.Token);
            if (!response.IsSuccessStatusCode)
                return null;

            var resultObj = await response.Content.ReadFromJsonAsync<OllamaChatResponse>(_jsonOptions, cts.Token);
            var content = resultObj?.Message?.Content;
            if (string.IsNullOrWhiteSpace(content))
                return null;

            var cleanJson = ExtractJson(content);
            var parsed = JsonSerializer.Deserialize<LlmActionOutput>(cleanJson, _jsonOptions);
            if (parsed == null || string.IsNullOrWhiteSpace(parsed.Action))
                return null;

            // Validate that the returned action genuinely exists in available actions
            var matchedAction = availableActions.FirstOrDefault(a => a.Name.Equals(parsed.Action, StringComparison.OrdinalIgnoreCase));
            if (matchedAction == null)
            {
                return null; // Reject hallucinated action name
            }

            var parameters = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
            if (parsed.Parameters != null)
            {
                foreach (var kvp in parsed.Parameters)
                {
                    parameters[kvp.Key] = kvp.Value?.ToString();
                }
            }

            return IntentResult.Match(
                matchedAction.Name,
                parameters,
                suggestedResponse: parsed.Reply,
                engine: $"Ollama ({modelName})"
            );
        }
        catch
        {
            // Fall back cleanly on network/timeout errors
            return null;
        }
    }

    private static string ExtractJson(string text)
    {
        var start = text.IndexOf('{');
        var end = text.LastIndexOf('}');
        if (start >= 0 && end > start)
        {
            return text.Substring(start, end - start + 1);
        }
        return text;
    }

    private class OllamaTagsResponse
    {
        public List<OllamaModelItem>? Models { get; set; }
    }

    private class OllamaModelItem
    {
        public string Name { get; set; } = string.Empty;
    }

    private class OllamaChatResponse
    {
        public OllamaMessageItem? Message { get; set; }
    }

    private class OllamaMessageItem
    {
        public string? Content { get; set; }
    }

    private class LlmActionOutput
    {
        public string? Action { get; set; }
        public Dictionary<string, object?>? Parameters { get; set; }
        public string? Reply { get; set; }
    }
}
