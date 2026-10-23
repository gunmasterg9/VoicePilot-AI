import re
from urllib.parse import quote_plus


def normalize_plan(plan):
    """
    Validate and normalize an Ollama-generated plan.
    """

    if not isinstance(plan, dict):
        return {
            "type": "chat",
            "response": "I couldn't understand that request.",
            "actions": []
        }

    plan_type = plan.get("type", "chat")

    if plan_type not in {"chat", "action"}:
        plan_type = "chat"

    response = str(
        plan.get("response", "")
    )

    actions = plan.get("actions", [])

    if not isinstance(actions, list):
        actions = []

    cleaned_actions = []

    for action in actions:

        if not isinstance(action, dict):
            continue

        tool = action.get("tool")

        if not tool:
            continue

        arguments = action.get(
            "arguments",
            {}
        )

        if not isinstance(arguments, dict):
            arguments = {}

        cleaned_actions.append(
            {
                "tool": str(tool),
                "arguments": arguments
            }
        )

    return {
        "type": plan_type,
        "response": response,
        "actions": cleaned_actions
    }


def _clean(text):
    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip(" .,!?;:")


def route_direct_command(user_message):
    """
    Deterministic router for common commands.

    These commands do NOT need Ollama.
    """

    text = _clean(user_message)

    if not text:
        return None

    lower = text.lower()

    # -------------------------------------------------------------
    # Conversation
    # -------------------------------------------------------------

    greetings = {
        "hi",
        "hello",
        "hey",
        "neo",
        "hey neo",
        "okay neo",
        "hey orion",
        "okay orion",
        "good morning",
        "good afternoon",
        "good evening"
    }

    if lower in greetings:

        return {
            "type": "chat",
            "response": "Hello! I'm NEO. How can I help?",
            "actions": []
        }

    if lower in {
        "how are you",
        "how are you doing"
    }:

        return {
            "type": "chat",
            "response": "I'm online and ready.",
            "actions": []
        }

    # -------------------------------------------------------------
    # Screenshot
    # -------------------------------------------------------------

    if (
        "screenshot" in lower
        or "screen shot" in lower
    ):

        return {
            "type": "action",
            "response": "Capturing a screenshot.",
            "actions": [
                {
                    "tool": "screenshot",
                    "arguments": {}
                }
            ]
        }

    # -------------------------------------------------------------
    # YouTube search
    #
    # Examples:
    # search Michael Jackson on YouTube
    # search for Michael Jackson on YouTube
    # look up Spider-Man on YouTube
    # find music on YouTube
    # -------------------------------------------------------------

    match = re.match(
        r"^(?:search|look\s+up|find)"
        r"\s+(?:for\s+)?"
        r"(.+?)"
        r"\s+on\s+youtube$",
        text,
        re.IGNORECASE
    )

    if match:

        query = _clean(
            match.group(1)
        )

        return {
            "type": "action",
            "response": (
                f"Searching YouTube for {query}."
            ),
            "actions": [
                {
                    "tool": "search_youtube",
                    "arguments": {
                        "query": query
                    }
                }
            ]
        }

    # -------------------------------------------------------------
    # Generic web search
    # -------------------------------------------------------------

    match = re.match(
        r"^(?:search|look\s+up|find)"
        r"\s+(?:for\s+)?"
        r"(.+?)"
        r"(?:\s+on\s+(?:google|the\s+web|web))?$",
        text,
        re.IGNORECASE
    )

    if match:

        query = _clean(
            match.group(1)
        )

        return {
            "type": "action",
            "response": (
                f"Searching for {query}."
            ),
            "actions": [
                {
                    "tool": "search_web",
                    "arguments": {
                        "query": query
                    }
                }
            ]
        }

    # -------------------------------------------------------------
    # OPEN
    # -------------------------------------------------------------

    match = re.match(
        r"^(?:open|launch|start|run)"
        r"\s+(.+)$",
        text,
        re.IGNORECASE
    )

    if match:

        target = _clean(
            match.group(1)
        )

        return {
            "type": "action",
            "response": (
                f"Opening {target}."
            ),
            "actions": [
                {
                    "tool": "open_target",
                    "arguments": {
                        "target": target
                    }
                }
            ]
        }

    # -------------------------------------------------------------
    # CLOSE
    # -------------------------------------------------------------

    match = re.match(
        r"^(?:close|exit|quit)"
        r"\s+(.+)$",
        text,
        re.IGNORECASE
    )

    if match:

        target = _clean(
            match.group(1)
        )

        return {
            "type": "action",
            "response": (
                f"Closing {target}."
            ),
            "actions": [
                {
                    "tool": "close_target",
                    "arguments": {
                        "target": target
                    }
                }
            ]
        }

    # -------------------------------------------------------------
    # CREATE FOLDER
    # -------------------------------------------------------------

    match = re.match(
        r"^(?:create|make)"
        r"\s+(?:a\s+)?folder"
        r"(?:\s+(?:called|named))?"
        r"\s+(.+)$",
        text,
        re.IGNORECASE
    )

    if match:

        folder = _clean(
            match.group(1)
        )

        return {
            "type": "action",
            "response": (
                f"Creating folder {folder}."
            ),
            "actions": [
                {
                    "tool": "create_folder",
                    "arguments": {
                        "path": folder
                    }
                }
            ]
        }

    # -------------------------------------------------------------
    # TYPE
    # -------------------------------------------------------------

    match = re.match(
        r"^(?:type|write)"
        r"\s+(.+)$",
        text,
        re.IGNORECASE
    )

    if match:

        content = match.group(1)

        return {
            "type": "action",
            "response": "Typing the requested text.",
            "actions": [
                {
                    "tool": "type_text",
                    "arguments": {
                        "text": content
                    }
                }
            ]
        }

    # -------------------------------------------------------------
    # PRESS KEY
    # -------------------------------------------------------------

    match = re.match(
        r"^(?:press|hit)"
        r"\s+(.+)$",
        text,
        re.IGNORECASE
    )

    if match:

        key = _clean(
            match.group(1)
        )

        return {
            "type": "action",
            "response": (
                f"Pressing {key}."
            ),
            "actions": [
                {
                    "tool": "press",
                    "arguments": {
                        "key": key
                    }
                }
            ]
        }

    # -------------------------------------------------------------
    # LOCK COMPUTER
    # -------------------------------------------------------------

    if lower in {
        "lock pc",
        "lock computer",
        "lock my pc",
        "lock my computer"
    }:

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

    return None
