using System.Reflection;
using System.Runtime.Loader;
using VoicePilot.Core.Automation;
using VoicePilot.Core.Security;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Plugins;

public class PluginLoader : IDisposable
{
    private readonly ActionRegistry _actionRegistry;
    private readonly List<IPlugin> _loadedPlugins = new();
    private readonly List<AssemblyLoadContext> _contexts = new();
    private readonly string _pluginsDirectory;
    private readonly object _lock = new();

    public IReadOnlyList<IPlugin> LoadedPlugins => _loadedPlugins.AsReadOnly();

    public PluginLoader(ActionRegistry actionRegistry, string? customPluginDir = null)
    {
        _actionRegistry = actionRegistry;
        if (!string.IsNullOrEmpty(customPluginDir))
        {
            _pluginsDirectory = customPluginDir;
        }
        else
        {
            var appData = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "VoicePilot", "Plugins");
            _pluginsDirectory = appData;
        }

        Directory.CreateDirectory(_pluginsDirectory);
    }

    public string PluginsDirectory => _pluginsDirectory;

    /// <summary>
    /// Scans the trusted plugins directory, validates assemblies, loads plugins, and registers their actions.
    /// </summary>
    public async Task<int> DiscoverAndLoadPluginsAsync(CancellationToken ct = default)
    {
        lock (_lock)
        {
            if (!Directory.Exists(_pluginsDirectory))
                return 0;
        }

        var loadedCount = 0;
        var pluginFiles = Directory.GetFiles(_pluginsDirectory, "*.dll", SearchOption.AllDirectories);

        foreach (var dllPath in pluginFiles)
        {
            if (!IsPathInsideTrustedDirectory(dllPath))
                continue;

            try
            {
                var count = await LoadPluginAssemblyAsync(dllPath, ct);
                loadedCount += count;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to load plugin assembly at '{SensitiveDataMasker.Mask(dllPath)}': {SensitiveDataMasker.Mask(ex.Message)}");
            }
        }

        return loadedCount;
    }

    /// <summary>
    /// Loads a specific plugin assembly directly (useful for built-in/sample plugins).
    /// </summary>
    public async Task<int> LoadPluginAssemblyAsync(string assemblyPath, CancellationToken ct = default)
    {
        if (!File.Exists(assemblyPath))
            return 0;

        var alc = new AssemblyLoadContext(Path.GetFileNameWithoutExtension(assemblyPath), isCollectible: true);
        _contexts.Add(alc);

        Assembly assembly;
        try
        {
            assembly = alc.LoadFromAssemblyPath(Path.GetFullPath(assemblyPath));
        }
        catch
        {
            return 0;
        }

        var pluginTypes = assembly.GetTypes()
            .Where(t => typeof(IPlugin).IsAssignableFrom(t) && !t.IsInterface && !t.IsAbstract);

        var count = 0;
        foreach (var type in pluginTypes)
        {
            try
            {
                if (Activator.CreateInstance(type) is IPlugin plugin)
                {
                    var ctx = new PluginContext(plugin.Id);
                    await plugin.InitializeAsync(ctx, ct);

                    lock (_lock)
                    {
                        _loadedPlugins.Add(plugin);
                    }

                    foreach (var actionDef in plugin.GetActions())
                    {
                        _actionRegistry.RegisterAction(new PluginActionWrapper(plugin, actionDef));
                    }

                    count++;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error activating plugin '{type.FullName}': {SensitiveDataMasker.Mask(ex.Message)}");
            }
        }

        return count;
    }

    public void RegisterPluginInstance(IPlugin plugin)
    {
        lock (_lock)
        {
            _loadedPlugins.Add(plugin);
        }

        foreach (var actionDef in plugin.GetActions())
        {
            _actionRegistry.RegisterAction(new PluginActionWrapper(plugin, actionDef));
        }
    }

    private bool IsPathInsideTrustedDirectory(string path)
    {
        try
        {
            var full = Path.GetFullPath(path);
            var root = Path.GetFullPath(_pluginsDirectory);
            return full.StartsWith(root, StringComparison.OrdinalIgnoreCase);
        }
        catch
        {
            return false;
        }
    }

    public void Dispose()
    {
        lock (_lock)
        {
            foreach (var plugin in _loadedPlugins)
            {
                try
                {
                    plugin.ShutdownAsync().GetAwaiter().GetResult();
                }
                catch { }
            }
            _loadedPlugins.Clear();

            foreach (var alc in _contexts)
            {
                try { alc.Unload(); } catch { }
            }
            _contexts.Clear();
        }
        GC.SuppressFinalize(this);
    }
}
