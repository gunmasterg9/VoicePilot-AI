import webbrowser
from urllib.parse import quote_plus

import pygetwindow as gw


def open_url(url):
    """Open a URL directly in the default browser."""
    try:
        webbrowser.open(url, new=2)
        return f"Opened {url}"
    except Exception as exc:
        return f"Could not open {url}: {exc}"


def search_youtube(query):
    """Search YouTube directly."""
    query = str(query).strip()

    if not query:
        return "No YouTube search query was specified."

    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
    )

    try:
        webbrowser.open(url, new=2)
        return f"Searching YouTube for {query}"
    except Exception as exc:
        return f"Could not search YouTube: {exc}"


def _find_windows():
    """Return visible, titled windows."""
    windows = []

    try:
        for window in gw.getAllWindows():

            title = str(window.title).strip()

            if not title:
                continue

            if title not in windows:
                windows.append(title)

    except Exception:
        pass

    return windows


def close_target(target):
    """
    Close a specific window or handle commands such as:

        close chrome
        close notepad
        close netflix
        close all apps
        close all windows
        close running apps
        close every window
    """

    target = str(target).strip()

    if not target:
        return "No window was specified."

    normalized = " ".join(target.lower().split())

    # ---------------------------------------------------------
    # CLOSE EVERYTHING
    # ---------------------------------------------------------

    close_all_commands = {
        "all",
        "all apps",
        "all application",
        "all applications",
        "all windows",
        "every window",
        "every windows",
        "every app",
        "every application",
        "running apps",
        "running applications",
        "running windows",
        "close all",
        "close all apps",
        "close all applications",
        "close all windows",
        "close running apps",
        "close running applications",
        "close running windows",
        "close every app",
        "close every application",
        "close every window",
        "close everything",
    }

    if normalized in close_all_commands:

        closed = []
        failed = []

        try:
            windows = gw.getAllWindows()

            for window in windows:

                title = str(window.title).strip()

                if not title:
                    continue

                try:
                    window.close()
                    closed.append(title)
                except Exception:
                    failed.append(title)

        except Exception as exc:
            return f"Could not close running windows: {exc}"

        if closed:
            return f"Closed {len(closed)} running window(s)."

        return "No running windows could be closed."

    # ---------------------------------------------------------
    # REMOVE COMMAND PREFIXES IF THEY REACH THIS FUNCTION
    # ---------------------------------------------------------

    prefixes = (
        "close ",
        "exit ",
        "quit ",
        "close window ",
        "close the window ",
        "close app ",
        "close application ",
        "close the app ",
        "close the application ",
    )

    cleaned = normalized

    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    if not cleaned:
        return "No window was specified."

    # ---------------------------------------------------------
    # FIND SPECIFIC WINDOW
    # ---------------------------------------------------------

    try:

        for window in gw.getAllWindows():

            title = str(window.title).strip()

            if not title:
                continue

            if cleaned in title.lower():

                try:
                    window.close()
                    return f"Closed {title}"
                except Exception as exc:
                    return f"Could not close {title}: {exc}"

        # -----------------------------------------------------
        # SECOND PASS: WORD MATCH
        # -----------------------------------------------------

        target_words = cleaned.split()

        for window in gw.getAllWindows():

            title = str(window.title).strip()

            if not title:
                continue

            title_lower = title.lower()

            if all(word in title_lower for word in target_words):

                try:
                    window.close()
                    return f"Closed {title}"
                except Exception as exc:
                    return f"Could not close {title}: {exc}"

    except Exception as exc:
        return f"Window control error: {exc}"

    return f"Window not found: {target}"