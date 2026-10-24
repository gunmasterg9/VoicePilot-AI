
import urllib.parse
import webbrowser


KNOWN_SERVICES = {
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "leetcode": "https://leetcode.com",
    "spotify": "https://open.spotify.com",
    "discord": "https://discord.com/app",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "chatgpt": "https://chatgpt.com",
    "gemini": "https://gemini.google.com",
    "stackoverflow": "https://stackoverflow.com"
}


def normalize_target(target):

    return (
        str(target)
        .lower()
        .strip()
        .replace(" app", "")
        .replace(" website", "")
        .strip()
    )


def resolve_known_service(target):

    return KNOWN_SERVICES.get(
        normalize_target(target)
    )


def search_web(query):

    encoded = urllib.parse.quote_plus(
        str(query)
    )

    url = (
        "https://www.google.com/search?q="
        + encoded
    )

    webbrowser.open(url)

    return (
        f"Searching the web for {query}."
    )


def open_website(target):

    known = resolve_known_service(
        target
    )

    if known:

        webbrowser.open(known)

        return (
            True,
            f"Opened {target} in the browser."
        )

    target = str(target).strip()

    if target.startswith(
        ("http://", "https://")
    ):

        webbrowser.open(target)

        return (
            True,
            f"Opened {target}."
        )

    if "." in target and " " not in target:

        url = "https://" + target

        webbrowser.open(url)

        return (
            True,
            f"Opened {target}."
        )

    return False, None


def open_new_tab(url: str = "") -> str:
    """
    Opens a new tab in the existing browser window if available,
    otherwise safely falls back to opening the default browser.
    """
    browser_signatures = [
        "Google Chrome", "Chrome",
        "Microsoft Edge", "Edge",
        "Mozilla Firefox", "Firefox",
        "Brave", "Opera", "Vivaldi"
    ]
    browser_window = None
    try:
        import pygetwindow as gw
        for win in gw.getAllWindows():
            title = win.title.strip()
            if not title:
                continue
            if any(sig.lower() in title.lower() for sig in browser_signatures):
                browser_window = win
                break
    except Exception:
        browser_window = None

    if browser_window:
        try:
            browser_window.activate()
            import pyautogui
            pyautogui.hotkey("ctrl", "t")
            if url:
                pyautogui.typewrite(url + "\n", interval=0.02)
            return "Opened a new tab in your browser."
        except Exception:
            pass

    # Safe, documented fallback: open default browser
    fallback_url = url if url else "https://www.google.com"
    try:
        webbrowser.open_new_tab(fallback_url)
        return "Opened default web browser."
    except Exception as exc:
        return f"Could not open browser: {exc}"
