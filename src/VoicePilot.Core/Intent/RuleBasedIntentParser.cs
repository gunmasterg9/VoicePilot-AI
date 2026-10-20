using System.Text.RegularExpressions;

namespace VoicePilot.Core.Intent;

/// <summary>
/// Fast, deterministic, 100% offline rule-based intent parser.
/// Requires no external LLM or network connection.
/// </summary>
public class RuleBasedIntentParser : IIntentParser
{
    private static readonly Regex CleanRegex = new(@"[^\w\s\.\*\-]", RegexOptions.Compiled);

    public Task<IntentResult> ParseIntentAsync(string utterance, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(utterance))
        {
            return Task.FromResult(IntentResult.Unrecognized(utterance));
        }

        var text = CleanRegex.Replace(utterance.ToLowerInvariant(), " ").Trim();
        text = Regex.Replace(text, @"\s+", " ");

        // 1. Date & Time
        if (text.Contains("what time") || text.Contains("current time") || text.Contains("tell me the time") || text.Contains("time is it"))
        {
            return Task.FromResult(IntentResult.Match("system.datetime", new() { ["mode"] = "time" }, confidence: 1.0));
        }
        if (text.Contains("what is the date") || text.Contains("what date") || text.Contains("today s date") || text.Contains("todays date"))
        {
            return Task.FromResult(IntentResult.Match("system.datetime", new() { ["mode"] = "date" }, confidence: 1.0));
        }
        if (text.Contains("what day is") || text.Contains("day of the week") || text.Contains("what day today"))
        {
            return Task.FromResult(IntentResult.Match("system.datetime", new() { ["mode"] = "day" }, confidence: 1.0));
        }
        if (text == "time" || text == "date" || text == "clock")
        {
            return Task.FromResult(IntentResult.Match("system.datetime", new() { ["mode"] = "full" }, confidence: 0.9));
        }

        // 2. Launch / Open Application
        var launchMatch = Regex.Match(text, @"^(?:open|launch|start|run)\s+(?:the\s+)?([a-z0-9\s]+?)(?:\s+app|\s+application)?$");
        if (launchMatch.Success)
        {
            var appCandidate = launchMatch.Groups[1].Value.Trim();
            // Check if it's actually a folder or system command
            if (IsFolderAlias(appCandidate))
            {
                return Task.FromResult(IntentResult.Match("system.open_path", new() { ["target"] = appCandidate }));
            }
            return Task.FromResult(IntentResult.Match("system.launch", new() { ["appName"] = appCandidate }));
        }

        // 3. Open Folder / Explorer
        if (text.StartsWith("open ") || text.StartsWith("show ") || text.StartsWith("explore "))
        {
            var folderCandidate = text.Substring(5).Trim();
            if (IsFolderAlias(folderCandidate) || folderCandidate.Contains("folder") || folderCandidate.Contains("directory"))
            {
                return Task.FromResult(IntentResult.Match("system.open_path", new() { ["target"] = folderCandidate }));
            }
        }

        // 4. File Search
        var searchMatch = Regex.Match(text, @"(?:search|find|look for)\s+(?:files?\s+(?:for\s+)?)?(.+?)(?:\s+in\s+([a-z]+))?$");
        if (searchMatch.Success)
        {
            var query = searchMatch.Groups[1].Value.Trim();
            var folder = searchMatch.Groups[2].Success ? searchMatch.Groups[2].Value.Trim() : "documents";

            // If it's "search web" or "google", defer to web search
            if (query.StartsWith("the web") || query.StartsWith("online") || query.StartsWith("google"))
            {
                var webQ = Regex.Replace(query, @"^(?:the\s+web\s+(?:for\s+)?|online\s+(?:for\s+)?|google\s+)", "").Trim();
                return Task.FromResult(IntentResult.Match("system.web_search", new() { ["query"] = webQ }));
            }

            return Task.FromResult(IntentResult.Match("system.search_files", new()
            {
                ["query"] = query,
                ["folder"] = folder
            }));
        }

        // 5. Web Search
        if (text.StartsWith("google ") || text.StartsWith("search the web for ") || text.StartsWith("search online for ") || text.StartsWith("web search "))
        {
            var query = Regex.Replace(text, @"^(?:google|search the web for|search online for|web search)\s+", "").Trim();
            return Task.FromResult(IntentResult.Match("system.web_search", new() { ["query"] = query }));
        }

        // 6. System Control: Lock, Mute, Battery
        if (text.Contains("lock my computer") || text.Contains("lock computer") || text.Contains("lock pc") || text.Contains("lock screen") || text.Contains("lock workstation"))
        {
            return Task.FromResult(IntentResult.Match("system.control", new() { ["command"] = "lock" }));
        }
        if (text.Contains("mute") || text.Contains("unmute") || text.Contains("toggle volume") || text.Contains("silence audio"))
        {
            return Task.FromResult(IntentResult.Match("system.control", new() { ["command"] = "mute" }));
        }
        if (text.Contains("battery") || text.Contains("power status") || text.Contains("battery level"))
        {
            return Task.FromResult(IntentResult.Match("system.control", new() { ["command"] = "battery" }));
        }

        // 7. Clipboard
        if (text.Contains("read clipboard") || text.Contains("what is on my clipboard") || text.Contains("clipboard content"))
        {
            return Task.FromResult(IntentResult.Match("system.clipboard", new() { ["operation"] = "read" }));
        }
        if (text.StartsWith("copy ") || text.StartsWith("copy to clipboard "))
        {
            var copyText = Regex.Replace(text, @"^(?:copy to clipboard|copy)\s+", "").Trim();
            return Task.FromResult(IntentResult.Match("system.clipboard", new() { ["operation"] = "write", ["text"] = copyText }));
        }

        // 8. Delete File (Requires confirmation)
        var deleteMatch = Regex.Match(text, @"(?:delete|remove)\s+file\s+(.+)");
        if (deleteMatch.Success)
        {
            var filePath = deleteMatch.Groups[1].Value.Trim();
            return Task.FromResult(IntentResult.Match("system.delete_file", new() { ["filePath"] = filePath }));
        }

        // 9. Sample Plugin actions (e.g. weather, note, diagnostics)
        if (text.Contains("weather"))
        {
            return Task.FromResult(IntentResult.Match("sample.weather", new() { ["location"] = "Local System" }, engine: "RuleBased"));
        }
        if (text.StartsWith("take note ") || text.StartsWith("add note ") || text.StartsWith("save note "))
        {
            var note = Regex.Replace(text, @"^(?:take|add|save)\s+note\s+", "").Trim();
            return Task.FromResult(IntentResult.Match("sample.note", new() { ["text"] = note }, engine: "RuleBased"));
        }
        if (text.Contains("system diagnostic") || text.Contains("system diagnostics") || text.Contains("diagnostics"))
        {
            return Task.FromResult(IntentResult.Match("sample.diagnostics", new(), engine: "RuleBased"));
        }

        return Task.FromResult(IntentResult.Unrecognized(utterance));
    }

    private static bool IsFolderAlias(string s)
    {
        var clean = s.ToLowerInvariant();
        return clean.Contains("document") || clean.Contains("download") || clean.Contains("desktop") ||
               clean.Contains("picture") || clean.Contains("photo") || clean.Contains("music") || clean.Contains("video");
    }
}
