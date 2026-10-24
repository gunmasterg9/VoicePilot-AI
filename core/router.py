"""
NEO AI - Deterministic Command Router & Plan Normalizer
Provides rule-based classification and execution planning for common natural
language instructions, ensuring instant responsiveness and 100% offline reliability.
"""

import re
from enum import Enum
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote_plus


class Intent(str, Enum):
    PC_COMMAND = "pc_command"
    CONVERSATIONAL = "conversational"
    SYSTEM_CONTROL = "system_control"
    DESTRUCTIVE_ACTION = "destructive_action"
    AMBIGUOUS = "ambiguous"
    EMPTY = "empty"


def is_ambiguous_fragment(text: str) -> bool:
    """
    Detects whether an utterance is an ambiguous fragment or noise (e.g. 'ndo', 'kaakwar')
    rather than a clear conversational question, greeting, or executable command.
    """
    clean = _clean(text).strip()
    if not clean:
        return True

    lower = clean.lower()
    words = lower.split()

    # If it matches any direct command or router rule, it's valid
    if route_direct_command(clean) is not None:
        return False

    # Allowed single-word conversational terms
    allowed_single_words = {
        "hi", "hello", "hey", "namaste", "thanks", "thank you", "bye", "goodbye",
        "yes", "no", "ok", "okay", "sure", "help",
        "नमस्ते", "नमस्कार", "धन्यवाद", "अलविदा", "हाँ", "नहीं", "मदद",
        "નમસ્તે", "આભાર", "હા", "ના", "મદદ"
    }
    if lower in allowed_single_words:
        return False

    # Short fragments (<= 3 characters that aren't allowed words)
    if len(clean) <= 3:
        return True

    # Known application & website names
    known_targets = {
        "notepad", "calculator", "paint", "explorer", "cmd", "powershell",
        "task manager", "chrome", "edge", "vs code", "code", "recycle bin",
        "youtube", "google", "github", "chatgpt", "spotify", "instagram",
        "facebook", "whatsapp", "linkedin", "amazon", "flipkart", "reddit",
        "twitter", "wikipedia", "canva", "zoom", "outlook"
    }

    # Single-word utterances
    if len(words) == 1:
        if lower in known_targets:
            return False
        question_words = {"who", "what", "where", "when", "why", "how", "which"}
        if lower in question_words or clean.endswith("?"):
            return False

        # Check latin character ratio / vowel absence
        latin_chars = [c for c in lower if 'a' <= c <= 'z']
        if latin_chars:
            vowels = sum(1 for c in latin_chars if c in "aeiouy")
            if vowels == 0 and len(latin_chars) >= 2:
                return True

        # Standalone unrecognized words without context or question mark are ambiguous
        return True

    # Two-word utterances
    if len(words) == 2:
        question_starters = {"what", "who", "where", "when", "why", "how", "can", "is", "are", "tell", "explain"}
        if words[0] in question_starters or clean.endswith("?"):
            return False
        greetings = {"good morning", "good evening", "good afternoon", "thank you", "how are"}
        if lower in greetings:
            return False
        # If any word has no vowels in Latin script
        for w in words:
            latin = [c for c in w if 'a' <= c <= 'z']
            if len(latin) >= 2 and sum(1 for c in latin if c in "aeiouy") == 0:
                return True

    return False


class CommandRouter:
    """
    Dedicated local command router between speech recognition and execution.
    Decides whether an utterance is a supported PC command, conversational question,
    system control (stop/cancel), or sensitive/destructive action.
    """
    def __init__(self):
        pass

    def classify_intent(self, utterance: str) -> Tuple[Intent, Dict[str, Any]]:
        text = _clean(utterance)
        if not text:
            return Intent.EMPTY, {}

        plan = route_direct_command(text)
        if plan:
            actions = plan.get("actions", [])
            if actions:
                tool = actions[0].get("tool", "")
                args = actions[0].get("arguments", {})
                if tool in {"stop_speaking", "cancel_speech"}:
                    return Intent.SYSTEM_CONTROL, {"command": "stop", "plan": plan}
                if tool in {"shutdown_pc", "restart_pc", "delete_path", "delete_file"}:
                    return Intent.DESTRUCTIVE_ACTION, {"tool": tool, "args": args, "plan": plan}
                return Intent.PC_COMMAND, {"tool": tool, "args": args, "plan": plan}
            if plan.get("type") in {"chat", "query"}:
                return Intent.PC_COMMAND, {"response": plan.get("response"), "plan": plan}
            return Intent.SYSTEM_CONTROL, {"plan": plan}

        # Check for ambiguous or garbled noise fragments before conversational routing
        if is_ambiguous_fragment(text):
            return Intent.AMBIGUOUS, {"query": text, "reason": "fragment"}

        return Intent.CONVERSATIONAL, {"query": text}

    def route(self, utterance: str) -> Optional[Dict[str, Any]]:
        return route_direct_command(utterance)


def normalize_plan(plan: Any) -> Dict[str, Any]:
    """Validate and normalize an LLM-generated execution plan."""
    if not isinstance(plan, dict):
        return {
            "type": "chat",
            "response": "I couldn't understand that request.",
            "actions": []
        }

    plan_type = plan.get("type", "chat")
    if plan_type not in {"chat", "action", "query"}:
        plan_type = "chat"

    response = str(plan.get("response", "")).strip()
    actions = plan.get("actions", [])
    if not isinstance(actions, list):
        actions = []

    cleaned_actions = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        tool = action.get("tool")
        if not tool or not isinstance(tool, str):
            continue

        arguments = action.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}

        cleaned_actions.append({
            "tool": str(tool).strip(),
            "arguments": arguments
        })

    return {
        "type": plan_type,
        "response": response,
        "actions": cleaned_actions
    }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip(" .,!?;:")


def route_direct_command(user_message: str) -> Optional[Dict[str, Any]]:
    """
    Deterministic router for common natural language commands.
    Provides offline resilience without requiring Ollama execution.
    """
    text = _clean(user_message)
    if not text:
        return None

    # Strip optional leading wake phrase if followed by a command
    unwaked = re.sub(
        r"^(?:(?:hey|hello|hi|okay)\s+)?(?:neo|orion)[\s,:-]+",
        "",
        text,
        flags=re.IGNORECASE
    ).strip()
    if unwaked:
        text = unwaked

    lower = text.lower()

    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # 0. Stop & Speech Cancellation
    # -------------------------------------------------------------
    if lower in {
        "stop",
        "cancel",
        "stop now",
        "cancel action",
        "halt",
        "abort",
        "stop speaking",
        "stop talking",
        "be quiet",
        "shut up",
        "stop audio",
        "stop voice",
        "silence",
        "cancel speech",
        "रुक जाओ",
        "बंद करो",
        "शांत रहो",
        "શાંત રહો",
        "રોકાઈ જાઓ",
    }:
        return {
            "type": "action",
            "response": "Speech synthesis stopped and operations halted.",
            "actions": [
                {
                    "tool": "stop_speaking",
                    "arguments": {}
                }
            ]
        }

    # -------------------------------------------------------------
    # 0.5. Volume Controls (Instant Local)
    # -------------------------------------------------------------
    if lower in {
        "increase volume",
        "volume up",
        "turn up volume",
        "turn up the volume",
        "raise volume",
        "raise the volume",
        "increase the volume",
        "louder",
        "make it louder",
        "आवाज़ बढ़ाओ",
        "वॉल्यूम बढ़ाओ",
        "आवाज बढ़ाओ",
        "અવાજ વધારો",
    }:
        return {
            "type": "action",
            "response": "Increasing volume.",
            "actions": [
                {
                    "tool": "volume_up",
                    "arguments": {"steps": 5}
                }
            ]
        }

    if lower in {
        "decrease volume",
        "volume down",
        "turn down volume",
        "turn down the volume",
        "lower volume",
        "lower the volume",
        "decrease the volume",
        "quieter",
        "make it quieter",
        "आवाज़ कम करो",
        "वॉल्यूम कम करो",
        "आवाज कम करो",
        "અવાજ ઘટાડો",
    }:
        return {
            "type": "action",
            "response": "Decreasing volume.",
            "actions": [
                {
                    "tool": "volume_down",
                    "arguments": {"steps": 5}
                }
            ]
        }

    if lower in {
        "mute volume",
        "mute the volume",
        "mute",
        "unmute",
        "unmute volume",
        "mute sound",
        "mute audio",
        "म्यूट करो",
        "आवाज़ म्यूट करो",
        "आवाज म्यूट करो",
        "અવાજ બંધ કરો",
    }:
        return {
            "type": "action",
            "response": "Toggling volume mute.",
            "actions": [
                {
                    "tool": "volume_mute",
                    "arguments": {}
                }
            ]
        }

    # -------------------------------------------------------------
    # 1. Conversation & Identity (English & Hindi)
    # -------------------------------------------------------------
    greetings = {
        "hi", "hello", "hey", "neo", "hey neo", "okay neo",
        "hey orion", "okay orion", "good morning", "good afternoon",
        "good evening", "namaste", "नमस्ते", "नमस्कार", "નમસ્તે", "કેમ છો"
    }
    if lower in greetings:
        return {
            "type": "chat",
            "response": "Hello! I'm NEO. How can I help you today?",
            "actions": []
        }

    if lower in {"how are you", "how are you doing", "what's up", "how's it going", "आप कैसे हैं", "कैसा चल रहा है"}:
        return {
            "type": "chat",
            "response": "I'm online, healthy, and ready for your commands.",
            "actions": []
        }

    if lower in {"who are you", "what is your name", "who made you", "तुम कौन हो", "आप कौन हैं", "तुम्हारा नाम क्या है", "તમે કોણ છો"}:
        return {
            "type": "chat",
            "response": "I am NEO, your local AI PC assistant.",
            "actions": []
        }

    # English & Hindi Time & Date
    time_patterns = [
        r"^what time is it$",
        r"^what'?s the time$",
        r"^what is the time$",
        r"^what is current time$",
        r"^what is the current time$",
        r"^tell me the time$",
        r"^current time$",
        r"^time now$",
        r"^what time is it now$",
        r"^what is the time now$"
    ]
    if any(re.match(p, lower) for p in time_patterns) or lower in {"समय क्या हुआ है", "टाइम क्या है", "समय बताओ", "टाइम बताओ", "સમય શું થયો છે", "ટાઈમ શું છે"}:
        from datetime import datetime
        now = datetime.now()
        return {
            "type": "chat",
            "response": now.strftime("The current time is %I:%M %p."),
            "actions": []
        }

    date_patterns = [
        r"^what is today'?s date$",
        r"^what'?s today'?s date$",
        r"^what is the date$",
        r"^what'?s the date$",
        r"^today'?s date$",
        r"^what day is it$",
        r"^what is the date today$",
        r"^what day is today$"
    ]
    if any(re.match(p, lower) for p in date_patterns) or lower in {"आज क्या तारीख है", "तारीख क्या है", "आज की तारीख क्या है", "आज कौन सा दिन है", "આજે કઈ તારીખ છે"}:
        from datetime import datetime
        now = datetime.now()
        return {
            "type": "chat",
            "response": now.strftime("Today is %A, %B %d, %Y."),
            "actions": []
        }

    # Hindi Time & Date
    if lower in {"समय क्या हुआ है", "टाइम क्या है", "समय बताओ", "टाइम बताओ"}:
        from datetime import datetime
        now = datetime.now()
        return {
            "type": "chat",
            "response": now.strftime("The current time is %I:%M %p."),
            "actions": []
        }

    if lower in {"आज क्या तारीख है", "तारीख क्या है", "आज की तारीख क्या है", "आज कौन सा दिन है"}:
        from datetime import datetime
        now = datetime.now()
        return {
            "type": "chat",
            "response": now.strftime("Today is %A, %B %d, %Y."),
            "actions": []
        }

    # Hindi & Gujarati App Launching
    if lower in {"कैलकुलेटर खोलो", "कैलकुलेटर चालू करो", "કેલ્ક્યુલેટર ખોલો", "કેલ્ક્યુલેટર ચાલુ કરો"}:
        return {
            "type": "action",
            "response": "Opening Calculator.",
            "actions": [{"tool": "open_target", "arguments": {"target": "calculator"}}]
        }

    if lower in {"नोटपैड खोलो", "नोटपैड चालू करो", "નોટપેડ ખોલો", "નોટપેડ ચાલુ કરો"}:
        return {
            "type": "action",
            "response": "Opening Notepad.",
            "actions": [{"tool": "open_target", "arguments": {"target": "notepad"}}]
        }

    if lower in {"पेंट खोलो", "पेंट चालू करो", "પેઇન્ટ ખોલો"}:
        return {
            "type": "action",
            "response": "Opening Paint.",
            "actions": [{"tool": "open_target", "arguments": {"target": "paint"}}]
        }

    if lower in {"स्क्रीनशॉट लो", "स्क्रीनशॉट खींचो", "સ્ક્રીનશોટ લો"}:
        return {
            "type": "action",
            "response": "Capturing desktop screenshot.",
            "actions": [{"tool": "screenshot", "arguments": {}}]
        }


    # -------------------------------------------------------------
    # 2. Hardware Telemetry & RAM Information (strictly anchored)
    # -------------------------------------------------------------
    ram_patterns = [
        r"^(?:(?:tell me|check|get|what is|show)\s+)?how much (?:ram|memory) is (?:available|free|used)$",
        r"^(?:tell me\s+)?how much ram is available$",
        r"^(?:how much\s+)?(?:available|free)\s+ram$",
        r"^ram\s+available$",
        r"^check\s+(?:ram|memory)$",
        r"^(?:ram|memory)\s+(?:usage|used)$",
        r"^how much memory is used$",
        r"^how much ram is used$",
    ]
    if any(re.match(p, lower) for p in ram_patterns):
        return {
            "type": "action",
            "response": "Inspecting system memory telemetry.",
            "actions": [
                {
                    "tool": "get_ram_info",
                    "arguments": {}
                }
            ]
        }

    system_patterns = [
        r"^(?:check\s+)?cpu(?:\s+(?:usage|load|status|%))?$",
        r"^(?:check\s+)?battery(?:\s+status|\s+level|\s+and\s+system\s+status)?$",
        r"^(?:check\s+)?(?:the\s+|my\s+)?system\s+(?:status|health|telemetry)$",
        r"^(?:check\s+)?hardware\s+status$",
        r"^(?:show\s+)?(?:the\s+|my\s+)?system\s+information$",
        r"^(?:show\s+)?(?:the\s+|my\s+)?system\s+info$",
        r"^show\s+system\s+telemetry$",
        r"^सिस्टम\s+(?:जानकारी|स्टेटस)(?:\s+दिखाओ)?$",
    ]
    if any(re.match(p, lower) for p in system_patterns):

        return {
            "type": "action",
            "response": "Gathering system telemetry.",
            "actions": [
                {
                    "tool": "get_system_telemetry",
                    "arguments": {"category": "all"}
                }
            ]
        }

    # -------------------------------------------------------------
    # 3. File Discovery & Inspection (PDFs, Downloads, etc.)
    # -------------------------------------------------------------
    match_pdf = re.search(
        r"(?:find|search|where\s+is|get|show)\s+(?:me\s+)?(?:my\s+)?(?:the\s+)?(?:latest|last|recent)\s+pdf",
        lower
    )
    if match_pdf or lower in {"find my latest pdf", "find latest pdf", "latest pdf"}:
        return {
            "type": "action",
            "response": "Searching your user folders for the most recent PDF.",
            "actions": [
                {
                    "tool": "find_latest_file",
                    "arguments": {"extension": "pdf"}
                }
            ]
        }

    match_latest_file = re.search(
        r"(?:find|search|show)\s+(?:me\s+)?(?:the\s+)?(?:latest|last|recent)\s+file(?:\s+with\s+extension\s+(\w+))?",
        lower
    )
    if match_latest_file:
        ext = match_latest_file.group(1) or "pdf"
        return {
            "type": "action",
            "response": f"Finding your most recent .{ext} file.",
            "actions": [
                {
                    "tool": "find_latest_file",
                    "arguments": {"extension": ext}
                }
            ]
        }

    # -------------------------------------------------------------
    # 4. Folder Navigation (Downloads, Documents, Desktop)
    # -------------------------------------------------------------
    match_folder = re.match(
        r"^(?:open|show|explore)\s+(?:the\s+|my\s+)?(downloads|documents|desktop|pictures|videos|music)\s*(?:folder|directory)?$",
        lower
    )
    if match_folder:
        folder_name = match_folder.group(1)
        return {
            "type": "action",
            "response": f"Opening your {folder_name.capitalize()} folder.",
            "actions": [
                {
                    "tool": "open_special_folder",
                    "arguments": {"folder_name": folder_name}
                }
            ]
        }

    # -------------------------------------------------------------
    # 4.5. Browser Tab Controls
    # -------------------------------------------------------------
    if lower in {
        "open new tab",
        "open a new tab",
        "new tab",
        "open tab",
        "create new tab",
        "create a new tab",
    }:
        return {
            "type": "action",
            "response": "Opening a new browser tab.",
            "actions": [
                {
                    "tool": "open_new_tab",
                    "arguments": {}
                }
            ]
        }

    # -------------------------------------------------------------
    # 5. Browser Launching
    # -------------------------------------------------------------
    if lower in {
        "open my browser",
        "open browser",
        "open the browser",
        "launch browser",
        "launch my browser",
        "open web browser",
        "launch web browser",
        "start browser",
    }:
        return {
            "type": "action",
            "response": "Opening web browser.",
            "actions": [
                {
                    "tool": "open_target",
                    "arguments": {"target": "browser"}
                }
            ]
        }

    # -------------------------------------------------------------
    # 6. Compound Commands (e.g. Notepad + letter drafting)
    # -------------------------------------------------------------
    if "notepad" in lower and ("letter" in lower or "write" in lower or "help me" in lower):
        return {
            "type": "action",
            "response": "Opening Notepad. Who would you like to address the letter to, and what is the topic?",
            "actions": [
                {
                    "tool": "open_target",
                    "arguments": {"target": "notepad and help me write a letter"}
                }
            ]
        }

    # -------------------------------------------------------------
    # 7. Screenshot
    # -------------------------------------------------------------
    if "screenshot" in lower or "screen shot" in lower or "capture screen" in lower:
        return {
            "type": "action",
            "response": "Capturing desktop screenshot.",
            "actions": [
                {
                    "tool": "screenshot",
                    "arguments": {}
                }
            ]
        }

    # -------------------------------------------------------------
    # 7.5. Local Computer Search
    # -------------------------------------------------------------
    local_search_patterns = [
        r"^(?:search|find)\s+(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)$",
        r"^(?:search|find)\s+files\s+(?:on\s+)?(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)$",
        r"^(?:search|find)\s+(?:for\s+)?files\s+on\s+(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)$",
        r"^(?:search|find)\s+(?:my\s+|the\s+)?(?:pc|computer)\s+for\s+files$",
        r"^(?:open\s+)?windows\s+search$",
    ]
    if any(re.match(p, lower) for p in local_search_patterns):
        return {
            "type": "action",
            "response": "Opening Windows Search.",
            "actions": [
                {
                    "tool": "open_windows_search",
                    "arguments": {"query": ""}
                }
            ]
        }

    # -------------------------------------------------------------
    # 8. Web Search (Google, YouTube)
    # -------------------------------------------------------------
    match_yt = re.match(
        r"^(?:search|look\s+up|find)\s+(?:for\s+)?(.+?)\s+on\s+youtube$",
        text,
        re.IGNORECASE
    )
    if match_yt:
        query = _clean(match_yt.group(1))
        return {
            "type": "action",
            "response": f"Searching YouTube for {query}.",
            "actions": [
                {
                    "tool": "search_youtube",
                    "arguments": {"query": query}
                }
            ]
        }

    match_explicit_web = re.match(
        r"^(?:search\s+(?:google|the\s+web|the\s+internet|web|online)\s+(?:for\s+)?|google\s+)(.+)$",
        text,
        re.IGNORECASE
    )
    if match_explicit_web:
        query = _clean(match_explicit_web.group(1))
        return {
            "type": "action",
            "response": f"Searching the web for {query}.",
            "actions": [
                {
                    "tool": "search_web",
                    "arguments": {"query": query}
                }
            ]
        }

    match_web_on = re.match(
        r"^(?:search|look\s+up|find)\s+(?:for\s+)?(.+?)\s+on\s+(?:google|the\s+web|web)$",
        text,
        re.IGNORECASE
    )
    if match_web_on:
        query = _clean(match_web_on.group(1))
        return {
            "type": "action",
            "response": f"Searching the web for {query}.",
            "actions": [
                {
                    "tool": "search_web",
                    "arguments": {"query": query}
                }
            ]
        }

    match_web = re.match(
        r"^(?:search|look\s+up)\s+(?:for\s+)?(.+)$",
        text,
        re.IGNORECASE
    )
    if match_web:
        query = _clean(match_web.group(1))
        if query and not query.startswith("folder") and not query.startswith("directory"):
            if not re.search(r"\b(?:my\s+|this\s+|the\s+)?(?:pc|computer|laptop)\b", query, re.IGNORECASE):
                return {
                    "type": "action",
                    "response": f"Searching the web for {query}.",
                    "actions": [
                        {
                            "tool": "search_web",
                            "arguments": {"query": query}
                        }
                    ]
                }

    # -------------------------------------------------------------
    # 9. Generic Open / Launch Application or Website
    # -------------------------------------------------------------
    match_open = re.match(
        r"^(?:open|launch|start|run)\s+(.+)$",
        text,
        re.IGNORECASE
    )
    if match_open:
        target = _clean(match_open.group(1))
        return {
            "type": "action",
            "response": f"Opening {target}.",
            "actions": [
                {
                    "tool": "open_target",
                    "arguments": {"target": target}
                }
            ]
        }

    # -------------------------------------------------------------
    # 10. Close Application or Window
    # -------------------------------------------------------------
    match_close = re.match(
        r"^(?:close|exit|quit|terminate)\s+(.+)$",
        text,
        re.IGNORECASE
    )
    if match_close:
        target = _clean(match_close.group(1))
        return {
            "type": "action",
            "response": f"Closing {target}.",
            "actions": [
                {
                    "tool": "close_target",
                    "arguments": {"target": target}
                }
            ]
        }

    # -------------------------------------------------------------
    # 11. Create Folder
    # -------------------------------------------------------------
    match_mk = re.match(
        r"^(?:create|make)\s+(?:a\s+)?folder(?:\s+(?:called|named))?\s+(.+)$",
        text,
        re.IGNORECASE
    )
    if match_mk:
        folder = _clean(match_mk.group(1))
        return {
            "type": "action",
            "response": f"Creating folder {folder}.",
            "actions": [
                {
                    "tool": "create_folder",
                    "arguments": {"path": folder}
                }
            ]
        }

    # -------------------------------------------------------------
    # 12. List Directory
    # -------------------------------------------------------------
    match_ls = re.match(
        r"^(?:list|show)\s+(?:the\s+)?(?:files|contents|directory)(?:\s+(?:in|of)\s+(.+))?$",
        text,
        re.IGNORECASE
    )
    if match_ls:
        target_dir = _clean(match_ls.group(1)) if match_ls.group(1) else "."
        return {
            "type": "action",
            "response": f"Listing directory contents.",
            "actions": [
                {
                    "tool": "list_directory",
                    "arguments": {"path": target_dir}
                }
            ]
        }

    # -------------------------------------------------------------
    # 13. System Lock & Power Controls
    # -------------------------------------------------------------
    if lower in {"lock pc", "lock computer", "lock my pc", "lock my computer", "lock workstation"}:
        return {
            "type": "action",
            "response": "Locking the computer.",
            "actions": [
                {
                    "tool": "lock_pc",
                    "arguments": {}
                }
            ]
        }

    if lower in {"shutdown pc", "shut down pc", "turn off pc", "shut down computer"}:
        return {
            "type": "action",
            "response": "Scheduling computer shutdown.",
            "actions": [
                {
                    "tool": "shutdown_pc",
                    "arguments": {"delay": 5}
                }
            ]
        }

    if lower in {"restart pc", "reboot pc", "restart computer", "reboot computer"}:
        return {
            "type": "action",
            "response": "Scheduling computer restart.",
            "actions": [
                {
                    "tool": "restart_pc",
                    "arguments": {"delay": 5}
                }
            ]
        }

    return None
