using VoicePilot.Core.Automation;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Plugins;

/// <summary>
/// Adapts an action exposed by an IPlugin into the host's IAction pipeline.
/// </summary>
public class PluginActionWrapper : IAction
{
    private readonly IPlugin _plugin;
    private readonly IActionDefinition _definition;

    public PluginActionWrapper(IPlugin plugin, IActionDefinition definition)
    {
        _plugin = plugin;
        _definition = definition;
    }

    public string Name => _definition.Name;
    public string Description => $"{_definition.Description} (Plugin: {_plugin.Name})";
    public bool RequiresConfirmation => _definition.RequiresConfirmation;
    public IReadOnlyList<ActionParameterDefinition> Parameters => _definition.Parameters;
    public IReadOnlyList<string> SamplePhrases => _definition.SamplePhrases;

    public async Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        return await _plugin.ExecuteActionAsync(_definition.Name, context.Parameters, ct);
    }
}
