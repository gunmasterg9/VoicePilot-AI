
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
