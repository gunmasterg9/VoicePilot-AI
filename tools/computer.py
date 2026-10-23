
from pathlib import Path
import pyautogui


def move_mouse(x, y):

    pyautogui.moveTo(
        int(x),
        int(y),
        duration=0.2
    )

    return (
        f"Moved mouse to {x}, {y}."
    )


def click(button="left"):

    pyautogui.click(
        button=str(button)
    )

    return (
        f"{str(button).capitalize()} click performed."
    )


def double_click():

    pyautogui.doubleClick()

    return "Double click performed."


def right_click():

    pyautogui.rightClick()

    return "Right click performed."


def scroll(amount):

    pyautogui.scroll(
        int(amount)
    )

    return "Scroll performed."


def type_text(
    text,
    interval=0.01
):

    pyautogui.write(
        str(text),
        interval=float(interval)
    )

    return "Text typed."


def press(key):

    pyautogui.press(
        str(key)
    )

    return f"Pressed {key}."


def hotkey(*keys):

    pyautogui.hotkey(
        *[
            str(key)
            for key in keys
        ]
    )

    return "Hotkey executed."


def screenshot(path=None):

    if path is None:

        path = (
            Path.home()
            / "Pictures"
            / "NEO_Screenshot.png"
        )

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    image = pyautogui.screenshot()

    image.save(path)

    return (
        f"Screenshot saved to {path}."
    )
