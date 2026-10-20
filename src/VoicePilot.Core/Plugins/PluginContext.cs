using VoicePilot.Core.Security;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Plugins;

public class PluginContext : IPluginContext
{
    public string StorageDirectory { get; }

    public PluginContext(string pluginId)
    {
        var appData = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "VoicePilot", "PluginData", pluginId);
        Directory.CreateDirectory(appData);
        StorageDirectory = appData;
    }

    public void LogInfo(string message)
    {
        System.Diagnostics.Debug.WriteLine($"[Plugin INFO] {SensitiveDataMasker.Mask(message)}");
    }

    public void LogWarning(string message)
    {
        System.Diagnostics.Debug.WriteLine($"[Plugin WARN] {SensitiveDataMasker.Mask(message)}");
    }

    public void LogError(string message, Exception? ex = null)
    {
        System.Diagnostics.Debug.WriteLine($"[Plugin ERROR] {SensitiveDataMasker.Mask(message)}: {SensitiveDataMasker.Mask(ex?.Message ?? "")}");
    }
}
