using VoicePilot.Core;
using VoicePilot.Core.Audio;
using VoicePilot.Core.Automation;
using VoicePilot.Core.Automation.Actions;
using VoicePilot.Core.Configuration;
using VoicePilot.Core.Intent;
using VoicePilot.Core.Llm;
using VoicePilot.Core.Security;
using VoicePilot.Core.Storage;
using VoicePilot.Core.Synthesis;
using Xunit;

namespace VoicePilot.Tests;

public class VerticalSliceIntegrationTests
{
    [Fact]
    public async Task VerticalSlice_EndToEndPipeline_Transcribe_Execute_Speak()
    {
        var tempCfg = Path.Combine(Path.GetTempPath(), $"vp_cfg_{Guid.NewGuid()}.json");
        var tempHist = Path.Combine(Path.GetTempPath(), $"vp_hist_{Guid.NewGuid()}.json");

        try
        {
            var settings = new SettingsManager(tempCfg);
            var history = new JsonConversationHistoryStore(settings, tempHist);
            var pathVal = new PathSecurityValidator();
            var appVal = new AppAllowlistValidator();

            var registry = new ActionRegistry();
            registry.RegisterAction(new DateTimeAction());
            registry.RegisterAction(new LaunchAppAction(appVal));
            registry.RegisterAction(new OpenPathAction(pathVal));
            registry.RegisterAction(new SearchFilesAction(pathVal));
            registry.RegisterAction(new SystemControlAction());

            var executor = new ActionExecutor(registry);
            var ruleParser = new RuleBasedIntentParser();
            var llm = new OllamaLanguageModelService(settings);
            var synth = new SapiSpeechSynthesisService(settings);
            var recog = new SapiSpeechRecognitionService(settings);

            using var engine = new AssistantEngine(
                settings, recog, synth, ruleParser, llm, registry, executor, history);

            // Simulate spoken utterance capture: "what time is it"
            var spokenUtterance = "what time is it";
            var result = await engine.ProcessUserUtteranceAsync(spokenUtterance);

            // Assertions on the vertical slice
            Assert.True(result.Success);
            Assert.False(result.RequiresConfirmation);
            Assert.Contains("It is currently", result.SpokenResponse);

            // Verify conversation history stored
            var storedHistory = await history.GetHistoryAsync(10);
            Assert.Single(storedHistory);
            Assert.Equal("what time is it", storedHistory[0].UserUtterance);
            Assert.Equal("system.datetime", storedHistory[0].ActionName);
            Assert.True(storedHistory[0].Success);
        }
        finally
        {
            if (File.Exists(tempCfg)) File.Delete(tempCfg);
            if (File.Exists(tempHist)) File.Delete(tempHist);
        }
    }

    [Fact]
    public async Task VerticalSlice_AppLaunchCommand_ResolvesAllowlistedApp()
    {
        var tempCfg = Path.Combine(Path.GetTempPath(), $"vp_cfg_{Guid.NewGuid()}.json");
        var tempHist = Path.Combine(Path.GetTempPath(), $"vp_hist_{Guid.NewGuid()}.json");

        try
        {
            var settings = new SettingsManager(tempCfg);
            var history = new JsonConversationHistoryStore(settings, tempHist);
            var pathVal = new PathSecurityValidator();
            var appVal = new AppAllowlistValidator();

            var registry = new ActionRegistry();
            registry.RegisterAction(new LaunchAppAction(appVal));

            var executor = new ActionExecutor(registry);
            var ruleParser = new RuleBasedIntentParser();
            var llm = new OllamaLanguageModelService(settings);
            var synth = new SapiSpeechSynthesisService(settings);
            var recog = new SapiSpeechRecognitionService(settings);

            using var engine = new AssistantEngine(
                settings, recog, synth, ruleParser, llm, registry, executor, history);

            // Query: "open calculator"
            var result = await engine.ProcessUserUtteranceAsync("open calculator");

            Assert.True(result.Success);
            Assert.Contains("Calculator", result.SpokenResponse);
        }
        finally
        {
            if (File.Exists(tempCfg)) File.Delete(tempCfg);
            if (File.Exists(tempHist)) File.Delete(tempHist);
        }
    }
}
