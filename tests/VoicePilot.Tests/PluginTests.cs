using VoicePilot.Core.Automation;
using VoicePilot.Core.Plugins;
using VoicePilot.Plugins.Sample;
using Xunit;

namespace VoicePilot.Tests;

public class PluginTests
{
    [Fact]
    public async Task SampleUtilityPlugin_ShouldExecuteActionsSuccessfully()
    {
        var registry = new ActionRegistry();
        var loader = new PluginLoader(registry);
        var plugin = new SampleUtilityPlugin();

        loader.RegisterPluginInstance(plugin);

        Assert.True(registry.TryGetAction("sample.weather", out var weatherAction));
        Assert.NotNull(weatherAction);

        var context = new ActionContext(new Dictionary<string, object?> { ["location"] = "Seattle" });
        var result = await weatherAction.ExecuteAsync(context);

        Assert.True(result.Success);
        Assert.Contains("Seattle", result.SpokenResponse);
    }

    [Fact]
    public async Task SampleUtilityPlugin_DiagnosticsAction_ReturnsSystemMetrics()
    {
        var plugin = new SampleUtilityPlugin();
        var actions = plugin.GetActions();

        Assert.Contains(actions, a => a.Name == "sample.diagnostics");

        var result = await plugin.ExecuteActionAsync("sample.diagnostics", new Dictionary<string, object?>());

        Assert.True(result.Success);
        Assert.Contains("System diagnostics", result.SpokenResponse);
        Assert.Contains("CPU cores", result.SpokenResponse);
    }
}
