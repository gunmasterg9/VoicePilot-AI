using Microsoft.Extensions.DependencyInjection;
using VoicePilot.Core.Audio;
using VoicePilot.Core.Automation;
using VoicePilot.Core.Automation.Actions;
using VoicePilot.Core.Configuration;
using VoicePilot.Core.Intent;
using VoicePilot.Core.Llm;
using VoicePilot.Core.Plugins;
using VoicePilot.Core.Security;
using VoicePilot.Core.Storage;
using VoicePilot.Core.Synthesis;

namespace VoicePilot.Core;

public static class ServiceConfigurator
{
    public static IServiceCollection AddVoicePilotCore(this IServiceCollection services)
    {
        // 1. Configuration & Security
        services.AddSingleton<SettingsManager>();
        services.AddSingleton(sp =>
        {
            var sm = sp.GetRequiredService<SettingsManager>();
            return new PathSecurityValidator(sm.Current.CustomAllowedDirectories);
        });
        services.AddSingleton(sp =>
        {
            var sm = sp.GetRequiredService<SettingsManager>();
            return new AppAllowlistValidator(sm.Current.CustomAllowedApplications);
        });

        // 2. Storage
        services.AddSingleton<IConversationHistoryStore, JsonConversationHistoryStore>();

        // 3. Audio & Speech
        services.AddSingleton<ISpeechSynthesisService, SapiSpeechSynthesisService>();
        services.AddSingleton<SapiSpeechRecognitionService>();
        services.AddSingleton<WhisperSpeechRecognitionService>();
        services.AddSingleton<ISpeechRecognitionService>(sp =>
        {
            var sm = sp.GetRequiredService<SettingsManager>();
            if (sm.Current.SpeechEngine.Equals("Whisper", StringComparison.OrdinalIgnoreCase))
            {
                var whisper = sp.GetRequiredService<WhisperSpeechRecognitionService>();
                if (whisper.IsModelAvailable())
                    return whisper;
            }
            return sp.GetRequiredService<SapiSpeechRecognitionService>();
        });

        // 4. Intent & LLM
        services.AddSingleton<HttpClient>();
        services.AddSingleton<IIntentParser, RuleBasedIntentParser>();
        services.AddSingleton<ILanguageModelService, OllamaLanguageModelService>();

        // 5. Actions & Registry
        services.AddSingleton<ActionRegistry>(sp =>
        {
            var reg = new ActionRegistry();
            var pathVal = sp.GetRequiredService<PathSecurityValidator>();
            var appVal = sp.GetRequiredService<AppAllowlistValidator>();

            // Register standard safe automation actions
            reg.RegisterAction(new DateTimeAction());
            reg.RegisterAction(new LaunchAppAction(appVal));
            reg.RegisterAction(new OpenPathAction(pathVal));
            reg.RegisterAction(new SearchFilesAction(pathVal));
            reg.RegisterAction(new SystemControlAction());
            reg.RegisterAction(new WebSearchAction());
            reg.RegisterAction(new ClipboardAction());
            reg.RegisterAction(new DeleteFileAction(pathVal));

            return reg;
        });

        services.AddSingleton<ActionExecutor>();

        // 6. Plugins
        services.AddSingleton<PluginLoader>(sp =>
        {
            var reg = sp.GetRequiredService<ActionRegistry>();
            return new PluginLoader(reg);
        });

        // 7. Engine Coordinator
        services.AddSingleton<AssistantEngine>();

        return services;
    }
}
