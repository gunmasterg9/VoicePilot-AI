
import os
from pathlib import Path

DANGEROUS_TOOLS = {
    "shutdown_pc",
    "restart_pc",
    "delete_path"
}


def is_path_safe_for_deletion(path_str):
    try:
        p = Path(path_str).expanduser().resolve()
        p_str = str(p).lower().rstrip("\\/")

        # Protect Windows and Program Files directories
        user_root = str(Path.home().parent).lower().rstrip("\\/")
        critical = [
            os.environ.get("SystemRoot", r"C:\Windows").lower().rstrip("\\/"),
            os.environ.get("ProgramFiles", r"C:\Program Files").lower().rstrip("\\/"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)").lower().rstrip("\\/"),
        ]

        if p_str == user_root:
            return False, f"Refusing to delete user accounts root directory: {p}"

        for crit in critical:
            if p_str == crit or p_str.startswith(crit + "\\"):
                return False, f"Refusing to delete protected system path: {p}"

        # Protect root of any drive (e.g. C:\)
        if len(p_str) <= 3 and ":" in p_str:
            return False, f"Refusing to delete drive root: {p}"

        return True, "Path is allowed"
    except Exception as exc:
        return False, f"Path validation error: {exc}"


def requires_confirmation(tool_name):
    return tool_name in DANGEROUS_TOOLS


def confirmation_message(tool_name, arguments=None):

    arguments = arguments or {}

    if tool_name == "shutdown_pc":
        return "This will shut down the computer. Continue?"

    if tool_name == "restart_pc":
        return "This will restart the computer. Continue?"

    if tool_name == "delete_path":

        path = arguments.get(
            "path",
            "the selected item"
        )

        return (
            f"This will permanently delete "
            f"{path}. Continue?"
        )

    return "This action requires confirmation. Continue?"

