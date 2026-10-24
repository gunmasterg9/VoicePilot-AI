
import pygetwindow as gw


def list_windows():

    windows = []

    for window in gw.getAllWindows():

        title = window.title.strip()

        if title:
            windows.append(title)

    if not windows:
        return "No windows found."

    return "\n".join(windows)


def active_window():

    window = gw.getActiveWindow()

    if not window:
        return "No active window."

    return (
        window.title
        or "Untitled window"
    )


def _find_window(title):

    title = str(title).lower()

    for window in gw.getAllWindows():

        if title in window.title.lower():

            return window

    return None


def minimize_window(title):

    window = _find_window(title)

    if not window:

        return (
            f"Window not found: {title}"
        )

    window.minimize()

    return (
        f"Minimized {window.title}"
    )


def maximize_window(title):

    window = _find_window(title)

    if not window:

        return (
            f"Window not found: {title}"
        )

    window.maximize()

    return (
        f"Maximized {window.title}"
    )


def close_window(title):

    window = _find_window(title)

    if not window:

        return (
            f"Window not found: {title}"
        )

    window.close()

    return (
        f"Closed {window.title}"
    )


def open_windows_search(query: str = "") -> str:
    """Opens Windows Search or File Explorer search."""
    import subprocess
    import urllib.parse
    try:
        if query:
            target = f"search-ms:query={urllib.parse.quote_plus(query)}"
        else:
            target = "search-ms:"
        subprocess.Popen(["explorer.exe", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if query:
            return f"Opening Windows Search for {query}."
        return "Opening Windows Search."
    except Exception as exc:
        return f"Could not open Windows Search: {exc}"
