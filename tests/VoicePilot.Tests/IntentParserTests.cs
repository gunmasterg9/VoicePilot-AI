using VoicePilot.Core.Intent;
using Xunit;

namespace VoicePilot.Tests;

public class IntentParserTests
{
    private readonly RuleBasedIntentParser _parser = new();

    [Theory]
    [InlineData("what time is it", "system.datetime", "time")]
    [InlineData("what is the date", "system.datetime", "date")]
    [InlineData("what day is today", "system.datetime", "day")]
    public async Task ParseIntentAsync_DateTimeQueries_ShouldMatchCorrectly(string utterance, string expectedAction, string expectedMode)
    {
        var result = await _parser.ParseIntentAsync(utterance);

        Assert.True(result.Recognized);
        Assert.Equal(expectedAction, result.ActionName);
        Assert.Equal(expectedMode, result.Parameters["mode"]);
    }

    [Theory]
    [InlineData("open calculator", "system.launch", "calculator")]
    [InlineData("launch notepad", "system.launch", "notepad")]
    [InlineData("start file explorer", "system.launch", "file explorer")]
    public async Task ParseIntentAsync_AppLaunchQueries_ShouldExtractApp(string utterance, string expectedAction, string expectedApp)
    {
        var result = await _parser.ParseIntentAsync(utterance);

        Assert.True(result.Recognized);
        Assert.Equal(expectedAction, result.ActionName);
        Assert.Equal(expectedApp, result.Parameters["appName"]);
    }

    [Theory]
    [InlineData("open documents folder", "system.open_path")]
    [InlineData("open downloads", "system.open_path")]
    [InlineData("show pictures", "system.open_path")]
    public async Task ParseIntentAsync_FolderQueries_ShouldMatchOpenPath(string utterance, string expectedAction)
    {
        var result = await _parser.ParseIntentAsync(utterance);

        Assert.True(result.Recognized);
        Assert.Equal(expectedAction, result.ActionName);
    }

    [Fact]
    public async Task ParseIntentAsync_SearchFiles_ShouldExtractQueryAndFolder()
    {
        var result = await _parser.ParseIntentAsync("search files for financial report in downloads");

        Assert.True(result.Recognized);
        Assert.Equal("system.search_files", result.ActionName);
        Assert.Equal("financial report", result.Parameters["query"]);
        Assert.Equal("downloads", result.Parameters["folder"]);
    }

    [Fact]
    public async Task ParseIntentAsync_LockWorkstation_ShouldMatchControl()
    {
        var result = await _parser.ParseIntentAsync("lock my computer");

        Assert.True(result.Recognized);
        Assert.Equal("system.control", result.ActionName);
        Assert.Equal("lock", result.Parameters["command"]);
    }

    [Fact]
    public async Task ParseIntentAsync_DeleteFile_ShouldExtractFilePath()
    {
        var result = await _parser.ParseIntentAsync("delete file notes.txt");

        Assert.True(result.Recognized);
        Assert.Equal("system.delete_file", result.ActionName);
        Assert.Equal("notes.txt", result.Parameters["filePath"]);
    }
}
