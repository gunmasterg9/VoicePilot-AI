"""
NEO AI - Central Tool Registry & Execution Dispatcher
Provides unified registration, schema validation, permission classification,
and safe execution for all PC automation capabilities.
"""

from typing import Any, Callable, Dict, List, Optional

from tools.base import ToolPermission, ToolResult, ToolSpec
from tools.apps import find_application, launch_application
from tools.web import open_website, search_web
from tools.computer import (
    move_mouse,
    click,
    double_click,
    right_click,
    scroll,
    type_text,
    press,
    hotkey,
    screenshot,
)
from tools.filesystem import (
    create_folder,
    list_directory,
    open_path,
    open_special_folder,
    find_latest_file,
    find_files,
    move_file,
    rename_file,
    delete_path,
)
from tools.windows import (
    list_windows,
    active_window,
    minimize_window,
    maximize_window,
    close_window,
)
from tools.system import (
    lock_pc,
    shutdown_pc,
    restart_pc,
    cancel_shutdown,
    get_ram_info,
    get_system_telemetry,
)
from tools.orion_direct import (
    close_target,
    search_youtube,
    open_url,
)
from core.safety import requires_confirmation, confirmation_message


KNOWN_WEBSITES = {
    "netflix": "https://www.netflix.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "spotify": "https://open.spotify.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "whatsapp": "https://web.whatsapp.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.in",
    "amazon india": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "reddit": "https://www.reddit.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "discord": "https://discord.com/app",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "canva": "https://www.canva.com",
    "zoom": "https://zoom.us",
    "outlook": "https://outlook.live.com",
    "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google maps": "https://maps.google.com",
}


def open_target(target: str, force_web: bool = False) -> str:
    """Intelligently resolves and launches an application, folder, or website."""
    target = str(target).strip()
    if not target:
        return "No target was specified."

    normalized = target.lower().strip()

    # Browser alias
    if normalized in {
        "browser",
        "my browser",
        "the browser",
        "web browser",
        "internet browser",
        "default browser",
    }:
        open_url("https://www.google.com")
        return "Opened default web browser."

    # Special user folders
    if normalized in {
        "downloads",
        "download",
        "downloads folder",
        "the downloads folder",
        "documents",
        "my documents",
        "desktop",
        "desktop folder",
        "pictures",
        "pictures folder",
        "videos",
        "music",
    }:
        folder_clean = normalized.replace(" folder", "").replace("the ", "").replace("my ", "").strip()
        return open_special_folder(folder_clean)

    # Compound request e.g., "notepad and help me write a letter"
    if "notepad" in normalized and ("letter" in normalized or "write" in normalized):
        app = find_application("notepad")
        if app:
            success, msg = launch_application(app)
            if success:
                return "Opened Notepad. Who would you like to address the letter to, and what is the topic?"
            return f"Failed to open Notepad: {msg}"
        return "Could not find Notepad application on this system."

    # Direct official website
    if not force_web:
        known_url = KNOWN_WEBSITES.get(normalized)
        if known_url:
            return open_url(known_url)

    # Local application search
    if not force_web:
        application = find_application(target)
        if application:
            success, message = launch_application(application)
            if success:
                return message

    # Generic website
    success, message = open_website(target)
    if success:
        return message

    # Search fallback
    return search_web(target)


# Registry of callable tools (100% backward-compatible dictionary)
TOOLS: Dict[str, Callable] = {
    # System and Telemetry
    "open_target": open_target,
    "open_website": open_url,
    "search_web": search_web,
    "search_youtube": search_youtube,
    "close_target": close_target,
    "get_ram_info": get_ram_info,
    "get_system_telemetry": get_system_telemetry,

    # Windows Management
    "list_windows": list_windows,
    "active_window": active_window,
    "minimize_window": minimize_window,
    "maximize_window": maximize_window,
    "close_window": close_window,

    # GUI and Input Automation
    "move_mouse": move_mouse,
    "click": click,
    "double_click": double_click,
    "right_click": right_click,
    "scroll": scroll,
    "type_text": type_text,
    "press": press,
    "hotkey": hotkey,
    "screenshot": screenshot,

    # Filesystem & Search
    "create_folder": create_folder,
    "list_directory": list_directory,
    "open_path": open_path,
    "open_special_folder": open_special_folder,
    "find_latest_file": find_latest_file,
    "find_files": find_files,
    "move_file": move_file,
    "rename_file": rename_file,
    "delete_path": delete_path,

    # System Power and Security
    "lock_pc": lock_pc,
    "shutdown_pc": shutdown_pc,
    "restart_pc": restart_pc,
    "cancel_shutdown": cancel_shutdown,
}


# Structured Tool Specifications with schemas and permission levels
TOOL_SPECS: Dict[str, ToolSpec] = {
    "open_target": ToolSpec(
        name="open_target",
        description="Opens a local application, special user folder, or website.",
        function=open_target,
        parameters={
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "search_web": ToolSpec(
        name="search_web",
        description="Searches Google using the default web browser.",
        function=search_web,
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "search_youtube": ToolSpec(
        name="search_youtube",
        description="Searches YouTube for videos.",
        function=search_youtube,
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "close_target": ToolSpec(
        name="close_target",
        description="Closes an application or window by title.",
        function=close_target,
        parameters={
            "type": "object",
            "properties": {"target": {"type": "string"}},
            "required": ["target"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "get_ram_info": ToolSpec(
        name="get_ram_info",
        description="Returns current available, used, and total RAM.",
        function=get_ram_info,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission.READ_ONLY,
    ),
    "get_system_telemetry": ToolSpec(
        name="get_system_telemetry",
        description="Gathers CPU, RAM, battery, and disk statistics.",
        function=get_system_telemetry,
        parameters={
            "type": "object",
            "properties": {"category": {"type": "string"}}
        },
        permission=ToolPermission.READ_ONLY,
    ),
    "screenshot": ToolSpec(
        name="screenshot",
        description="Captures a desktop screenshot to Pictures/NEO_Screenshot.png.",
        function=screenshot,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}}
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "find_latest_file": ToolSpec(
        name="find_latest_file",
        description="Finds the most recently modified file with a given extension (e.g. pdf).",
        function=find_latest_file,
        parameters={
            "type": "object",
            "properties": {
                "extension": {"type": "string"},
                "directory": {"type": "string"}
            }
        },
        permission=ToolPermission.READ_ONLY,
    ),
    "find_files": ToolSpec(
        name="find_files",
        description="Searches for files by name substring and optional extension.",
        function=find_files,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "extension": {"type": "string"},
                "directory": {"type": "string"}
            },
            "required": ["query"]
        },
        permission=ToolPermission.READ_ONLY,
    ),
    "list_directory": ToolSpec(
        name="list_directory",
        description="Lists files and subdirectories in a given folder.",
        function=list_directory,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}}
        },
        permission=ToolPermission.READ_ONLY,
    ),
    "open_special_folder": ToolSpec(
        name="open_special_folder",
        description="Opens standard folders: downloads, documents, desktop, pictures, videos.",
        function=open_special_folder,
        parameters={
            "type": "object",
            "properties": {"folder_name": {"type": "string"}},
            "required": ["folder_name"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "create_folder": ToolSpec(
        name="create_folder",
        description="Creates a new folder at the given path.",
        function=create_folder,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "open_path": ToolSpec(
        name="open_path",
        description="Opens a file or directory path in Windows.",
        function=open_path,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "move_file": ToolSpec(
        name="move_file",
        description="Moves a file to a new destination.",
        function=move_file,
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"}
            },
            "required": ["source", "destination"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "rename_file": ToolSpec(
        name="rename_file",
        description="Renames an existing file.",
        function=rename_file,
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "destination": {"type": "string"}
            },
            "required": ["source", "destination"]
        },
        permission=ToolPermission.REVERSIBLE,
    ),
    "delete_path": ToolSpec(
        name="delete_path",
        description="Permanently deletes a file or directory. Requires user confirmation.",
        function=delete_path,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        },
        permission=ToolPermission.DESTRUCTIVE,
    ),
    "lock_pc": ToolSpec(
        name="lock_pc",
        description="Locks the Windows workstation.",
        function=lock_pc,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission.REVERSIBLE,
    ),
    "shutdown_pc": ToolSpec(
        name="shutdown_pc",
        description="Shuts down the PC after an optional delay. Requires confirmation.",
        function=shutdown_pc,
        parameters={
            "type": "object",
            "properties": {"delay": {"type": "integer"}}
        },
        permission=ToolPermission.DESTRUCTIVE,
    ),
    "restart_pc": ToolSpec(
        name="restart_pc",
        description="Restarts the PC after an optional delay. Requires confirmation.",
        function=restart_pc,
        parameters={
            "type": "object",
            "properties": {"delay": {"type": "integer"}}
        },
        permission=ToolPermission.DESTRUCTIVE,
    ),
    "cancel_shutdown": ToolSpec(
        name="cancel_shutdown",
        description="Cancels any pending shutdown or restart.",
        function=cancel_shutdown,
        parameters={"type": "object", "properties": {}},
        permission=ToolPermission.REVERSIBLE,
    ),
}


def get_tool(name: str) -> Optional[Callable]:
    """Retrieves a registered tool callable by name."""
    return TOOLS.get(str(name).strip())


def get_tool_spec(name: str) -> Optional[ToolSpec]:
    """Retrieves tool metadata specification."""
    return TOOL_SPECS.get(str(name).strip())


def get_all_tools() -> Dict[str, Callable]:
    """Returns all registered tool callables."""
    return TOOLS


def get_all_tool_specs() -> Dict[str, ToolSpec]:
    """Returns all tool specifications."""
    return TOOL_SPECS


def execute_tool(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    confirm_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
) -> ToolResult:
    """
    Safely executes a registered tool:
    1. Validates existence in registry.
    2. Validates argument schema.
    3. Prompts for confirmation if tool is destructive.
    4. Executes with error handling and returns structured ToolResult.
    """
    arguments = arguments or {}
    spec = get_tool_spec(tool_name)
    func = get_tool(tool_name)

    if not func:
        return ToolResult(
            success=False,
            output="",
            error=f"Unrecognized tool: '{tool_name}'",
            permission=ToolPermission.REVERSIBLE
        )

    # Fail closed for every destructive action. A missing or broken
    # confirmation handler must never be interpreted as approval.
    destructive = requires_confirmation(tool_name) or (
        spec is not None and spec.permission == ToolPermission.DESTRUCTIVE
    )
    if destructive:
        if confirm_callback is None:
            return ToolResult(
                success=False,
                output="",
                error="Action blocked: explicit confirmation is unavailable.",
                permission=ToolPermission.DESTRUCTIVE,
            )
        try:
            approved = confirm_callback(tool_name, arguments) is True
        except Exception:
            approved = False
        if not approved:
            return ToolResult(
                success=False,
                output="",
                error="Action cancelled or confirmation failed.",
                permission=ToolPermission.DESTRUCTIVE,
            )

    # Use spec execution if available
    if spec:
        return spec.execute(**arguments)

    # Fallback to direct function call
    try:
        raw = func(**arguments)
        return ToolResult(
            success=True,
            output=str(raw),
            permission=ToolPermission.REVERSIBLE
        )
    except Exception as exc:
        return ToolResult(
            success=False,
            output="",
            error=f"Tool failed: {exc}",
            permission=ToolPermission.REVERSIBLE
        )