using System.Windows.Forms;
using VoicePilot.Core.Interop;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class SystemControlAction : IAction
{
    public string Name => "system.control";
    public string Description => "Performs native Windows system controls like locking workstation, toggling mute, and checking battery.";
    public bool RequiresConfirmation => false;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("command", typeof(string), true, "Sub-command: 'lock', 'mute', 'battery'")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "lock my computer",
        "lock workstation",
        "mute audio",
        "check battery status"
    };

    public Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        if (!context.Parameters.TryGetValue("command", out var cmdObj) || cmdObj == null)
        {
            return Task.FromResult(ActionResult.Fail("System command is required.", "Please specify a system command."));
        }

        var command = cmdObj.ToString()?.ToLowerInvariant().Trim() ?? string.Empty;

        switch (command)
        {
            case "lock":
            case "lock_pc":
            case "lock_workstation":
                try
                {
                    NativeMethods.LockWorkStation();
                    return Task.FromResult(ActionResult.Ok("Locking your computer.", "Workstation locked."));
                }
                catch (Exception ex)
                {
                    return Task.FromResult(ActionResult.Fail($"Failed to lock workstation: {ex.Message}", "Could not lock the computer."));
                }

            case "mute":
            case "toggle_mute":
                try
                {
                    // Send volume mute command
                    NativeMethods.SendMessage(IntPtr.Zero, NativeMethods.WM_APPCOMMAND, IntPtr.Zero, (IntPtr)NativeMethods.APPCOMMAND_VOLUME_MUTE);
                    return Task.FromResult(ActionResult.Ok("Toggled audio mute.", "Audio mute toggled."));
                }
                catch (Exception ex)
                {
                    return Task.FromResult(ActionResult.Fail($"Audio mute error: {ex.Message}", "Could not toggle audio mute."));
                }

            case "battery":
            case "power":
                try
                {
                    var status = SystemInformation.PowerStatus;
                    var percent = (int)(status.BatteryLifePercent * 100);
                    var state = status.PowerLineStatus == PowerLineStatus.Online ? "plugged in and charging" : "running on battery";
                    var spoken = $"Your battery is at {percent} percent, and your computer is {state}.";
                    var display = $"Battery: {percent}% | Power: {status.PowerLineStatus} | Battery Charge: {status.BatteryChargeStatus}";
                    return Task.FromResult(ActionResult.Ok(spoken, display, status));
                }
                catch (Exception ex)
                {
                    return Task.FromResult(ActionResult.Fail($"Could not read battery: {ex.Message}", "Battery status is unavailable on this system."));
                }

            default:
                return Task.FromResult(ActionResult.Fail($"Unknown system control command: '{command}'", "I didn't recognize that system control."));
        }
    }
}
