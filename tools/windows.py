
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
