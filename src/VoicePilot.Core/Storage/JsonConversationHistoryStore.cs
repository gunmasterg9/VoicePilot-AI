using System.Text.Json;
using VoicePilot.Core.Configuration;

namespace VoicePilot.Core.Storage;

public class JsonConversationHistoryStore : IConversationHistoryStore
{
    private readonly string _historyFilePath;
    private readonly SettingsManager _settingsManager;
    private readonly SemaphoreSlim _lock = new(1, 1);
    private readonly JsonSerializerOptions _jsonOptions;

    public JsonConversationHistoryStore(SettingsManager settingsManager, string? customPath = null)
    {
        _settingsManager = settingsManager;
        _jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNameCaseInsensitive = true
        };

        if (!string.IsNullOrEmpty(customPath))
        {
            _historyFilePath = customPath;
        }
        else
        {
            var baseDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VoicePilot");
            Directory.CreateDirectory(baseDir);
            _historyFilePath = Path.Combine(baseDir, "history.json");
        }
    }

    public async Task<IReadOnlyList<ConversationEntry>> GetHistoryAsync(int maxCount = 50, CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct);
        try
        {
            if (!File.Exists(_historyFilePath))
                return Array.Empty<ConversationEntry>();

            var json = await File.ReadAllTextAsync(_historyFilePath, ct);
            var list = JsonSerializer.Deserialize<List<ConversationEntry>>(json, _jsonOptions);
            if (list == null)
                return Array.Empty<ConversationEntry>();

            return list.OrderByDescending(x => x.Timestamp).Take(maxCount).ToList().AsReadOnly();
        }
        catch
        {
            return Array.Empty<ConversationEntry>();
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task AddEntryAsync(ConversationEntry entry, CancellationToken ct = default)
    {
        if (!_settingsManager.Current.SaveConversationHistory)
            return;

        await _lock.WaitAsync(ct);
        try
        {
            List<ConversationEntry> list = new();
            if (File.Exists(_historyFilePath))
            {
                try
                {
                    var existingJson = await File.ReadAllTextAsync(_historyFilePath, ct);
                    var existingList = JsonSerializer.Deserialize<List<ConversationEntry>>(existingJson, _jsonOptions);
                    if (existingList != null)
                        list = existingList;
                }
                catch
                {
                    // Fresh list if corrupted
                }
            }

            list.Add(entry);

            // Trim to max configured
            var max = _settingsManager.Current.MaxHistoryEntries;
            if (list.Count > max)
            {
                list = list.OrderByDescending(x => x.Timestamp).Take(max).OrderBy(x => x.Timestamp).ToList();
            }

            var json = JsonSerializer.Serialize(list, _jsonOptions);
            await File.WriteAllTextAsync(_historyFilePath, json, ct);
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task ClearHistoryAsync(CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct);
        try
        {
            if (File.Exists(_historyFilePath))
            {
                File.Delete(_historyFilePath);
            }
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task UpdateEntryConfirmationAsync(Guid entryId, bool confirmed, CancellationToken ct = default)
    {
        await _lock.WaitAsync(ct);
        try
        {
            if (!File.Exists(_historyFilePath))
                return;

            var json = await File.ReadAllTextAsync(_historyFilePath, ct);
            var list = JsonSerializer.Deserialize<List<ConversationEntry>>(json, _jsonOptions);
            if (list == null)
                return;

            var idx = list.FindIndex(x => x.Id == entryId);
            if (idx >= 0)
            {
                list[idx] = list[idx] with { Confirmed = confirmed };
                var updatedJson = JsonSerializer.Serialize(list, _jsonOptions);
                await File.WriteAllTextAsync(_historyFilePath, updatedJson, ct);
            }
        }
        finally
        {
            _lock.Release();
        }
    }
}
