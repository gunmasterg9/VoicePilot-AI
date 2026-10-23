
from tools.computer import screenshot


def capture_screen(path=None):

    return screenshot(path)


def find_on_screen(description):

    return (
        "Vision system is not configured yet "
        f"for: {description}"
    )
