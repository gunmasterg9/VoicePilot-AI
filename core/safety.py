"""
NEO AI - Safety, Permission, and Path Protection System
Protects Windows system directories, critical user roots, and requires
explicit human confirmation for all destructive actions.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Set

# Operations classified as destructive that REQUIRE user confirmation
DANGEROUS_TOOLS: Set[str] = {
    "shutdown_pc",
    "restart_pc",
    "delete_path",
}

# Protected system environments on Windows
CRITICAL_ENV_VARS = [
    "SystemRoot",       # C:\Windows
    "windir",           # C:\Windows
    "ProgramFiles",     # C:\Program Files
    "ProgramFiles(x86)",# C:\Program Files (x86)
    "ProgramData",      # C:\ProgramData
]


def is_path_safe_for_deletion(path_str: str) -> Tuple[bool, str]:
    """
    Validates that a path is safe for deletion.
    Blocks deletion of Windows, Program Files, system drives, user roots, and system files.
    """
    try:
        if not path_str or not str(path_str).strip():
            return False, "Target path is empty."

        p = Path(path_str).expanduser().resolve()
        p_str = str(p).lower().rstrip("\\/")

        # 1. Protect drive root (e.g. C:\, D:\)
        if len(p_str) <= 3 and ":" in p_str:
            return False, f"Refusing to delete drive root: {p}"

        # 2. Protect Windows accounts and user root (e.g. C:\Users, C:\Users\Username)
        user_home = str(Path.home()).lower().rstrip("\\/")
        user_parent = str(Path.home().parent).lower().rstrip("\\/")

        if p_str == user_parent:
            return False, f"Refusing to delete all-users root directory: {p}"
        if p_str == user_home:
            return False, f"Refusing to delete user profile root directory: {p}"

        # 3. Protect Windows system directories
        critical_paths = []
        for var in CRITICAL_ENV_VARS:
            val = os.environ.get(var)
            if val:
                critical_paths.append(str(Path(val).resolve()).lower().rstrip("\\/"))

        # Fallback defaults if env vars missing
        default_crit = [r"c:\windows", r"c:\windows\system32", r"c:\program files", r"c:\program files (x86)"]
        for dc in default_crit:
            if dc not in critical_paths:
                critical_paths.append(dc)

        for crit in critical_paths:
            if p_str == crit or p_str.startswith(crit + "\\"):
                return False, f"Refusing to delete protected system path: {p}"

        # 4. Protect critical system boot files
        critical_files = {"bootmgr", "pagefile.sys", "swapfile.sys", "hiberfil.sys", "ntldr"}
        if p.name.lower() in critical_files:
            return False, f"Refusing to delete core system file: {p.name}"

        return True, "Path is allowed for deletion."

    except Exception as exc:
        return False, f"Path validation error: {exc}"


def requires_confirmation(tool_name: str) -> bool:
    """Returns True if the tool performs an irreversible or destructive action."""
    return str(tool_name).strip().lower() in DANGEROUS_TOOLS


def is_tool_destructive(tool_name: str) -> bool:
    """Alias for requires_confirmation."""
    return requires_confirmation(tool_name)


def confirmation_message(tool_name: str, arguments: Optional[Dict] = None) -> str:
    """Generates a clear human-readable confirmation prompt."""
    arguments = arguments or {}
    tool = str(tool_name).strip().lower()

    if tool == "shutdown_pc":
        delay = arguments.get("delay", 5)
        return f"NEO is requesting permission to shut down your computer (delay {delay}s). Proceed?"

    if tool == "restart_pc":
        delay = arguments.get("delay", 5)
        return f"NEO is requesting permission to restart your computer (delay {delay}s). Proceed?"

    if tool == "delete_path":
        path = arguments.get("path", "the specified file or directory")
        return f"NEO is requesting permission to permanently delete: '{path}'. Proceed?"

    return f"NEO is requesting permission to execute potentially destructive tool '{tool_name}'. Proceed?"
