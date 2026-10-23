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


def normalize_safe_path(p_str: str) -> str:
    """
    Strips Windows extended device prefixes (\\\\?\\, \\\\.\\, \\??\\, UNC)
    and normalizes slashes to prevent adversarial path filtering bypasses.
    Preserves root trailing backslash for drive roots to prevent resolve() 
    from interpreting them as drive-relative CWD paths.
    """
    s = str(p_str).replace("/", "\\").strip()
    for unc_pfx in ("\\\\?\\unc\\", "\\\\.\\unc\\", "\\??\\unc\\"):
        if s.lower().startswith(unc_pfx):
            s = "\\\\" + s[len(unc_pfx):]
            break
    for pfx in ("\\\\?\\", "\\\\.\\", "\\??\\"):
        if s.startswith(pfx):
            s = s[len(pfx):]
            break
    # Drive root specification (e.g. C:, C:\, C:\\) must preserve trailing backslash
    if len(s) >= 2 and s[1] == ":" and (len(s) == 2 or all(c == "\\" for c in s[2:])):
        return s[:2].upper() + "\\"
    # Naked root slash
    if s and all(c == "\\" for c in s):
        return "\\"
    return s.rstrip("\\/")


def is_path_safe_for_deletion(path_str: str) -> Tuple[bool, str]:
    """
    Validates that a path is safe for deletion.
    Blocks deletion of Windows, Program Files, system drives, user roots, and system files.
    Resistant to path traversal, symbolic links, alternate device paths, and extended-length prefixes.
    """
    try:
        if not path_str or not str(path_str).strip():
            return False, "Target path is empty."

        clean_input = normalize_safe_path(path_str)
        p = Path(clean_input).expanduser().resolve()
        p_str = normalize_safe_path(str(p)).lower()

        # 0. Reject path traversal attempting to target protected directories or escape bounds
        raw_parts = [part.lower() for part in Path(clean_input).parts]
        if ".." in raw_parts:
            if any(name in raw_parts for name in ["windows", "system32", "syswow64", "program files", "users"]):
                return False, f"Refusing to delete path with unsafe directory traversal: {path_str}"

        # 1. Protect drive root (e.g. C:, C:\, D:\, \\server\share)
        drive, rest = os.path.splitdrive(p_str)
        if drive and rest.strip("\\/") == "":
            return False, f"Refusing to delete drive root: {p}"
        if len(p_str) <= 3 and ":" in p_str:
            return False, f"Refusing to delete drive root: {p}"
        if p == Path(p.anchor):
            return False, f"Refusing to delete drive root: {p}"

        # 2. Protect Windows accounts and user root (e.g. C:\Users, C:\Users\Username)
        user_home = normalize_safe_path(str(Path.home().resolve())).lower()
        user_parent = normalize_safe_path(str(Path.home().parent.resolve())).lower()

        if p_str == user_parent:
            return False, f"Refusing to delete all-users root directory: {p}"
        if p_str == user_home:
            return False, f"Refusing to delete user profile root directory: {p}"

        # Protect any directory named 'windows', 'system32', 'program files', etc.
        protected_directory_names = {"windows", "system32", "syswow64", "program files", "program files (x86)", "programdata", "users"}
        if p.name.lower() in protected_directory_names:
            return False, f"Refusing to delete protected system target name: {p}"

        # 3. Protect Windows system directories
        critical_paths = []
        for var in CRITICAL_ENV_VARS:
            val = os.environ.get(var)
            if val:
                critical_paths.append(normalize_safe_path(str(Path(val).resolve())).lower())

        # Fallback defaults if env vars missing
        default_crit = [r"c:\windows", r"c:\windows\system32", r"c:\program files", r"c:\program files (x86)"]
        for dc in default_crit:
            cleaned_dc = normalize_safe_path(dc).lower()
            if cleaned_dc not in critical_paths:
                critical_paths.append(cleaned_dc)

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


def mask_sensitive_data(text: str) -> str:
    """Masks API keys, tokens, credentials, and passwords in logs and outputs."""
    if not text:
        return ""
    import re
    # Mask OpenAI-like keys (sk-...)
    masked = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-***[MASKED]***", str(text))
    # Mask Bearer tokens
    masked = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]{8,}", "Bearer ***[MASKED]***", masked, flags=re.IGNORECASE)
    # Mask generic key/token/password assignments in json or query strings
    masked = re.sub(
        r'("(?:api_key|cloud_api_key|token|password|secret|auth_token)"\s*:\s*")[^"]+(")',
        r'\1***[MASKED]***\2',
        masked,
        flags=re.IGNORECASE
    )
    # Mask key/token assignments in python dict strings
    masked = re.sub(
        r"('(?:api_key|cloud_api_key|token|password|secret|auth_token)'\s*:\s*')[^']+(')",
        r"\1***[MASKED]***\2",
        masked,
        flags=re.IGNORECASE
    )
    # Mask parameter assignments in command lines or URLs
    masked = re.sub(
        r'((?:api_key|apikey|token|password|secret)=)[^\s&"\']+',
        r'\1***[MASKED]***',
        masked,
        flags=re.IGNORECASE
    )
    return masked
