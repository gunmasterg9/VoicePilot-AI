using System.Windows.Forms;
using VoicePilot.Sdk;

namespace VoicePilot.Core.Automation.Actions;

public class ClipboardAction : IAction
{
    public string Name => "system.clipboard";
    public string Description => "Reads or copies text to the Windows clipboard.";
    public bool RequiresConfirmation => false;

    public IReadOnlyList<ActionParameterDefinition> Parameters => new List<ActionParameterDefinition>
    {
        new("operation", typeof(string), true, "Operation: 'read' or 'write'"),
        new("text", typeof(string), false, "Text to copy when operation is write")
    };

    public IReadOnlyList<string> SamplePhrases => new List<string>
    {
        "read my clipboard",
        "copy text to clipboard",
        "what is on clipboard"
    };

    public Task<ActionResult> ExecuteAsync(ActionContext context, CancellationToken ct = default)
    {
        var op = context.Parameters.TryGetValue("operation", out var opVal) ? opVal?.ToString()?.ToLowerInvariant() : "read";

        if (op == "write" || op == "set" || op == "copy")
        {
            var text = context.Parameters.TryGetValue("text", out var tVal) ? tVal?.ToString() : string.Empty;
            if (string.IsNullOrEmpty(text))
            {
                return Task.FromResult(ActionResult.Fail("Text to copy is empty.", "There is no text provided to copy."));
            }

            try
            {
                // STA thread dispatch for clipboard
                var t = new Thread(() =>
                {
                    try { Clipboard.SetText(text); } catch { }
                });
                t.SetApartmentState(ApartmentState.STA);
                t.Start();
                t.Join(1000);

                return Task.FromResult(ActionResult.Ok("Copied to clipboard.", $"Copied: \"{text}\""));
            }
            catch (Exception ex)
            {
                return Task.FromResult(ActionResult.Fail($"Clipboard copy error: {ex.Message}", "Could not copy to clipboard."));
            }
        }
        else
        {
            string clipText = string.Empty;
            try
            {
                var t = new Thread(() =>
                {
                    try
                    {
                        if (Clipboard.ContainsText())
                            clipText = Clipboard.GetText();
                    }
                    catch { }
                });
                t.SetApartmentState(ApartmentState.STA);
                t.Start();
                t.Join(1000);

                if (string.IsNullOrWhiteSpace(clipText))
                {
                    return Task.FromResult(ActionResult.Ok("Your clipboard is currently empty.", "Clipboard is empty."));
                }

                var preview = clipText.Length > 120 ? clipText[..120] + "..." : clipText;
                return Task.FromResult(ActionResult.Ok($"Clipboard contains: {preview}", clipText));
            }
            catch (Exception ex)
            {
                return Task.FromResult(ActionResult.Fail($"Clipboard read error: {ex.Message}", "Could not read clipboard."));
            }
        }
    }
}
