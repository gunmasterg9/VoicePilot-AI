from tools.apps import (
    find_application,
    launch_application
)

from tools.web import (
    open_website,
    search_web
)

from tools.computer import (
    move_mouse,
    click,
    double_click,
    right_click,
    scroll,
    type_text,
    press,
    hotkey,
    screenshot
)

from tools.filesystem import (
    create_folder,
    list_directory,
    open_path,
    move_file,
    rename_file,
    delete_path
)

from tools.windows import (
    list_windows,
    active_window,
    minimize_window,
    maximize_window,
    close_window
)

from tools.system import (
    lock_pc,
    shutdown_pc,
    restart_pc,
    cancel_shutdown
)

from tools.orion_direct import (
    close_target,
    search_youtube,
    open_url
)


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


def open_target(target, force_web=False):

    target = str(target).strip()

    if not target:
        return "No target was specified."

    normalized = target.lower().strip()

    # Direct official website
    if not force_web:

        known_url = KNOWN_WEBSITES.get(normalized)

        if known_url:
            return open_url(known_url)

    # Local application
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


TOOLS = {
    "open_target": open_target,
    "open_website": open_url,
    "search_web": search_web,
    "search_youtube": search_youtube,
    "close_target": close_target,

    "list_windows": list_windows,
    "active_window": active_window,
    "minimize_window": minimize_window,
    "maximize_window": maximize_window,
    "close_window": close_window,

    "move_mouse": move_mouse,
    "click": click,
    "double_click": double_click,
    "right_click": right_click,
    "scroll": scroll,
    "type_text": type_text,
    "press": press,
    "hotkey": hotkey,
    "screenshot": screenshot,

    "create_folder": create_folder,
    "list_directory": list_directory,
    "open_path": open_path,
    "move_file": move_file,
    "rename_file": rename_file,
    "delete_path": delete_path,

    "lock_pc": lock_pc,
    "shutdown_pc": shutdown_pc,
    "restart_pc": restart_pc,
    "cancel_shutdown": cancel_shutdown,
}


def get_tool(name):
    return TOOLS.get(name)


def get_all_tools():
    return TOOLS