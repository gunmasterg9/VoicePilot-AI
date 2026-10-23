"""
NEO AI - Deterministic Command Router & Plan Normalizer
Provides rule-based classification and execution planning for common natural
language instructions, ensuring instant responsiveness and 100% offline reliability.
"""

import re
from typing import Any, Dict, Optional
from urllib.parse import quote_plus


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

    lower = text.lower()

    # -------------------------------------------------------------
    # 0. Speech Cancellation
    # -------------------------------------------------------------
    if lower in {
        "stop speaking",
        "stop talking",
        "be quiet",
        "shut up",
        "stop audio",
        "stop voice",
        "silence",
        "cancel speech",
    }:
        return {
            "type": "action",
            "response": "Speech synthesis stopped.",
            "actions": [
                {
                    "tool": "stop_speaking",
                    "arguments": {}
                }
            ]
        }

    # -------------------------------------------------------------
    # 1. Conversation & Identity
    # -------------------------------------------------------------
    greetings = {
        "hi", "hello", "hey", "neo", "hey neo", "okay neo",
        "hey orion", "okay orion", "good morning", "good afternoon",
        "good evening", "namaste"
    }
    if lower in greetings:
        return {
            "type": "chat",
            "response": "Hello! I'm NEO. How can I help you today?",
            "actions": []
        }

    if lower in {"how are you", "how are you doing", "what's up", "how's it going"}:
        return {
            "type": "chat",
            "response": "I'm online, healthy, and ready for your commands.",
            "actions": []
        }

    # -------------------------------------------------------------
    # 2. Hardware Telemetry & RAM Information
    # -------------------------------------------------------------
    if any(k in lower for k in [
        "how much ram is available",
        "how much ram is free",
        "available ram",
        "ram available",
        "tell me how much ram is available",
        "how much memory is available",
        "free ram",
        "check memory",
        "check ram",
        "memory used",
        "ram usage",
        "how much memory"
    ]):
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

    if any(k in lower for k in [
        "check cpu", "cpu usage", "cpu load", "check battery",
        "system status", "system health", "hardware status"
    ]):
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
            "response": "Opening Notepad to assist you with drafting your letter.",
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

    match_web = re.match(
        r"^(?:search(?:\s+the\s+web|\s+the\s+internet|\s+google)?|look\s+up|google)\s+(?:for\s+)?(.+?)(?:\s+on\s+(?:google|the\s+web|web))?$",
        text,
        re.IGNORECASE
    )
    if match_web:
        query = _clean(match_web.group(1))
        if query and not query.startswith("folder") and not query.startswith("directory"):
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
