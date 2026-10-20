using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation;

/// <summary>
/// Central registry of all built-in actions and dynamically loaded plugin actions.
/// </summary>
public class ActionRegistry
{
    private readonly Dictionary<string, IAction> _actions = new(StringComparer.OrdinalIgnoreCase);
    private readonly object _lock = new();

    public void RegisterAction(IAction action)
    {
        lock (_lock)
        {
            _actions[action.Name] = action;
        }
    }

    public void UnregisterAction(string actionName)
    {
        lock (_lock)
        {
            _actions.Remove(actionName);
        }
    }

    public bool TryGetAction(string actionName, out IAction action)
    {
        lock (_lock)
        {
            return _actions.TryGetValue(actionName, out action!);
        }
    }

    public IReadOnlyCollection<IAction> GetAllActions()
    {
        lock (_lock)
        {
            return _actions.Values.ToList().AsReadOnly();
        }
    }
}
