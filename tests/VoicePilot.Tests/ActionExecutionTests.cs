using VoicePilot.Core.Automation;
using VoicePilot.Core.Automation.Actions;
using VoicePilot.Core.Configuration;
using VoicePilot.Core.Security;
using VoicePilot.Core.Storage;
using Xunit;

namespace VoicePilot.Tests;

public class ActionExecutionTests
{
    [Fact]
    public async Task DateTimeAction_ShouldReturnFormattedDateTime()
    {
        var action = new DateTimeAction();
        var context = new ActionContext(new Dictionary<string, object?> { ["mode"] = "time" });

        var result = await action.ExecuteAsync(context);

        Assert.True(result.Success);
        Assert.Contains("It is currently", result.SpokenResponse);
    }

    [Fact]
    public async Task ActionExecutor_RequiresConfirmation_WhenActionSensitive()
    {
        var registry = new ActionRegistry();
        var pathVal = new PathSecurityValidator();
        var deleteAction = new DeleteFileAction(pathVal);
        registry.RegisterAction(deleteAction);

        var executor = new ActionExecutor(registry);
        var docs = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        var testFile = Path.Combine(docs, "temp_voicepilot_test.txt");

        var request = new ExecutionRequest(
            ActionName: "system.delete_file",
            Parameters: new Dictionary<string, object?> { ["filePath"] = testFile },
            IsConfirmed: false
        );

        var result = await executor.ExecuteAsync(request);

        Assert.False(result.Success);
        Assert.True(result.RequiresConfirmation);
        Assert.NotNull(result.PendingRequest);
    }

    [Fact]
    public async Task JsonConversationHistoryStore_ShouldStoreAndClearEntries()
    {
        var tempConfigPath = Path.Combine(Path.GetTempPath(), $"vp_cfg_{Guid.NewGuid()}.json");
        var tempHistoryPath = Path.Combine(Path.GetTempPath(), $"vp_hist_{Guid.NewGuid()}.json");

        try
        {
            var sm = new SettingsManager(tempConfigPath);
            var store = new JsonConversationHistoryStore(sm, tempHistoryPath);

            var entry1 = new ConversationEntry
            {
                UserUtterance = "what time is it",
                AssistantResponse = "It is 10:00 AM.",
                ActionName = "system.datetime",
                Success = true
            };

            await store.AddEntryAsync(entry1);
            var history = await store.GetHistoryAsync(10);

            Assert.Single(history);
            Assert.Equal("what time is it", history[0].UserUtterance);

            await store.ClearHistoryAsync();
            var cleared = await store.GetHistoryAsync(10);
            Assert.Empty(cleared);
        }
        finally
        {
            if (File.Exists(tempConfigPath)) File.Delete(tempConfigPath);
            if (File.Exists(tempHistoryPath)) File.Delete(tempHistoryPath);
        }
    }
}
